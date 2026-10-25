"""Agent-facing local state/evidence protocol; reasoning belongs to the caller."""
import hashlib
import json
import math
import uuid

from fastapi import HTTPException, Request
from pydantic import ValidationError
from agent_models import MODELS, Source, Submission

PREFIX = '/api/agent/v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def register(w):
    """Inject existing app storage/locks; avoid a second state store."""
    app = w.app

    def context(pid):
        path = w.folder(pid)
        with w.LOCK:
            project = w.read(path/'project.json')
            sources = []
            for item in project.get('agent_sources', []):
                source_file = path/item['relative_path']
                intact = source_file.is_file() and w.file_sha256(source_file) == item['sha256']
                sources.append({**item, 'integrity':intact,
                                'content':source_file.read_text('utf-8') if intact else None})
            artifacts = [w.read(p) for p in sorted((path/'agent/artifacts').glob('*.json'))]
            heads = project.get('agent_heads', {})
            by_id = {a['id']:a for a in artifacts}
            def stale(artifact, seen=None):
                seen = set() if seen is None else seen
                if artifact['id'] in seen:
                    return True
                seen = seen | {artifact['id']}
                return any(aid not in by_id or heads.get(by_id[aid]['stage']) != aid
                           or stale(by_id[aid], seen) for aid in artifact['input_artifact_ids'])
            for artifact in artifacts:
                artifact['dependency_stale'] = stale(artifact)
            media = []
            for item in project['media']:
                record = {**item, 'declaration_only':True}
                marker = path/'media'/item['id']/'current-asr.json'
                if marker.exists():
                    run = w.read(marker)['run_id']
                    review_path = path/'media'/item['id']/'asr'/run/'review.json'
                    if review_path.exists():
                        r = w.read(review_path)
                        record['asr'] = {'run_id':run, 'revision':r.get('revision', 0),
                                         'backend':r.get('backend','faster-whisper'),'device':r.get('device'),
                                         'execution':r.get('execution',{}),'fallback_errors':r.get('fallback_errors',[]),
                                         'words':len(r['words']), 'sha256':w.file_sha256(review_path),
                                         'review_url':f'/api/projects/{pid}/media/{item["id"]}/review',
                                         'original_transcript_path':str(review_path.with_name('transcript.original.json'))}
                media.append(record)
            visual_plans = []
            for entry in project.get('visual_plans',[]):
                saved=w.read(path/entry['relative_path'])
                current=next((m for m in media if m['id']==entry['media_id']),{})
                asr=current.get('asr',{})
                visual_plans.append({**saved,'media_id':entry['media_id'],
                    'stale':saved['asr_run']!=asr.get('run_id') or saved['review_revision']!=asr.get('revision') or saved['source_sha256']!=current.get('sha256')})
            exports = [{'id':p.parent.name, 'provenance':w.read(p)}
                       for p in sorted((path/'exports').glob('*/provenance.json'))]
            jobs = w.list_jobs(pid)
            skill_files = sorted(w.SKILL.rglob('*'))
            skill_hashes = {p.relative_to(w.SKILL).as_posix():w.file_sha256(p)
                            for p in skill_files if p.is_file() and '__pycache__' not in p.parts}
            state = {'protocol_version':1, 'project':project, 'sources':sources,
                     'artifacts':artifacts, 'heads':heads, 'media':media,
                     'tasks':[w.read(p) for p in sorted((path/'agent/tasks').glob('*.json'))],
                     'exports':exports, 'jobs':jobs, 'visual_plans':visual_plans,
                     'timeline_plans':[w.read(path/e['relative_path']) for e in project.get('timeline_plans',[])],
                     'knowledge_library':{'root':str(w.LIBRARY) if w.LIBRARY else None,
                                          'ledger':str(w.LIBRARY/'阅读记录/全库逐篇阅读清单.json') if w.LIBRARY else None,
                                          'progress':w.read(w.LIBRARY/'阅读记录/当前阅读进度.json') if w.LIBRARY and (w.LIBRARY/'阅读记录/当前阅读进度.json').exists() else None},
                     'skill':{'entry':str(w.SKILL/'SKILL.md'), 'files':skill_hashes,
                              'bundle_sha256':digest(skill_hashes)},
                     'validation_scope':'structure, exact source anchors, IDs, revisions, arithmetic; not independent truth or content quality',
                     'external_publication':False}
            state['context_id'] = digest(state)
            context_file = path/'agent/contexts'/f'{state["context_id"]}.json'
            state['context_snapshot_path'] = str(context_file)
            if not context_file.exists():
                w.write(context_file,state)
            return state

    def errors_for(body, state):
        errors, warnings, computed = [], [], {}
        def error(code, location, message):
            errors.append({'code':code, 'location':location, 'message':message})
        try:
            submission = Submission.model_validate(body)
            payload = MODELS[submission.stage].model_validate(submission.payload).model_dump()
        except ValidationError as exc:
            for e in exc.errors(include_url=False, include_context=False, include_input=False):
                error('schema', '.'.join(map(str,e['loc'])), e['msg'])
            return errors, warnings, computed, None
        s = submission.model_dump()
        s['payload'] = payload
        if s['revision'] != state['project']['revision']:
            error('revision_conflict', 'revision', f"Expected context.project.revision={state['project']['revision']}, received {s['revision']}; this is not a phase version. Refresh context and reconsider before resubmitting.")
        if s['context_id'] != state['context_id']:
            error('context_conflict', 'context_id', 'Sources, skill, artifacts, media review or jobs changed.')
        sources = {a['id']:a for a in state['sources']}
        artifacts = {a['id']:a for a in state['artifacts']}
        selected_inputs = []
        for aid in s['input_artifact_ids']:
            a = artifacts.get(aid)
            if not a:
                error('unknown_artifact', 'input_artifact_ids', aid)
            else:
                selected_inputs.append(a)
                if state['heads'].get(a['stage']) != aid or a['dependency_stale']:
                    error('stale_dependency', 'input_artifact_ids', aid)
        required = {'topics':'diagnose', 'script':'topics', 'publish':'script', 'review':'publish'}
        upstream = required.get(s['stage'])
        if upstream and not any(a['stage'] == upstream for a in selected_inputs):
            if not s['standalone_reason'] or not s['standalone_reason'].strip():
                error('missing_handoff', 'input_artifact_ids', f'Need {upstream}, or explain standalone scope.')
            else:
                warnings.append('Standalone phase; this does not establish an end-to-end pass.')
        old = state['heads'].get(s['stage'])
        if old and s['supersedes'] != old:
            error('missing_supersedes', 'supersedes', 'A new version must name the current phase head.')
        if s['supersedes']:
            prior = artifacts.get(s['supersedes'])
            if not prior or prior['stage'] != s['stage']:
                error('invalid_supersedes', 'supersedes', 'Must refer to a previous artifact in this phase.')
            if not s['revision_reason'] or not s['revision_reason'].strip():
                error('missing_revision_reason', 'revision_reason', 'Describe the actual change.')

        simulated = state['project']['simulation'] or any(a['scope'] == 'simulation' for a in selected_inputs)
        def check_links(links, location):
            nonlocal simulated
            for link in links:
                source = sources.get(link['source_id'])
                if not source:
                    error('unknown_source', location, link['source_id'])
                elif not source['integrity']:
                    error('source_integrity', location, source['id'])
                elif link['quote'] not in source['content']:
                    error('anchor_not_found', location, f'Quote not present in {source["id"]}.')
                elif source['nature'] == 'simulation':
                    simulated = True
        claims = payload.get('claims', [])
        claim_ids = [c['id'] for c in claims]
        if len(set(claim_ids)) != len(claim_ids):
            error('duplicate_claim', 'payload.claims', 'Claim IDs must be unique in this artifact.')
        for i,c in enumerate(claims):
            check_links(c['evidence'], f'payload.claims.{i}.evidence')
            if c['kind'] == 'observation' and not c['evidence']:
                error('unsupported_observation', f'payload.claims.{i}', 'Observation requires an exact source anchor.')
            if c['kind'] == 'fictional':
                simulated = True
        def claim_refs(rows):
            ids = [r['id'] for r in rows]
            if len(set(ids)) != len(ids):
                error('duplicate_row', 'payload', 'Row IDs must be unique.')
            for row in rows:
                for cid in row['claim_ids']:
                    if cid not in claim_ids:
                        error('unknown_claim', 'payload', cid)
        stage = s['stage']
        if stage == 'topics':
            claim_refs(payload['candidates'])
            if payload['selected_id'] not in [t['id'] for t in payload['candidates']]:
                error('unknown_topic', 'payload.selected_id', 'Select an existing candidate.')
        if stage in ('script', 'publish', 'review'):
            field = {'script':'topic_artifact_id', 'publish':'script_artifact_id', 'review':'publish_artifact_id'}[stage]
            expected_stage = {'script':'topics','publish':'script','review':'publish'}[stage]
            aid = payload[field]
            if aid is not None and not any(a['id'] == aid and a['stage'] == expected_stage for a in selected_inputs):
                error('unbound_handoff', 'payload.'+field, 'Reference must be an input artifact of the correct phase.')
            if aid is None and any(a['stage'] == expected_stage for a in selected_inputs):
                error('missing_artifact_binding', 'payload.'+field, 'Bind the upstream artifact explicitly.')
        if stage == 'script':
            aid = payload['topic_artifact_id']
            if aid in artifacts and payload['topic_id'] != artifacts[aid]['payload']['selected_id']:
                error('topic_mismatch', 'payload.topic_id', 'Script must bind the selected topic.')
            claim_refs(payload['segments'])
            end = 0
            for i,seg in enumerate(payload['segments']):
                if seg['end'] <= seg['start'] or seg['start'] < end:
                    error('invalid_timeline', f'payload.segments.{i}', 'End must follow start; segments cannot overlap.')
                end = seg['end']
            computed['script_duration_seconds'] = end
            computed['spoken_non_whitespace_characters'] = sum(len(''.join(seg['spoken'].split())) for seg in payload['segments'])
            computed['character_count_scope'] = 'includes punctuation; use calculate/script_check for the skill speaking-budget count'
            warnings.append('Script timing is a planned timeline, not a measured human reading.')
        if stage == 'publish':
            mids = {m['id']:m for m in state['media']}
            exports = {e['id']:e for e in state['exports']}
            for asset in payload['assets']:
                mid, eid = asset['media_id'], asset['export_id']
                if mid not in mids:
                    error('unknown_media', 'payload.assets', mid)
                elif mids[mid].get('media_nature') in ('generated', 'mixed', 'restored') and not payload['disclosure'].strip():
                    error('missing_disclosure', 'payload.disclosure', 'State generated/restored/mixed asset nature.')
                if eid is not None and (eid not in exports or exports[eid]['provenance']['source_media_id'] != mid):
                    error('unbound_export', 'payload.assets', str(eid))
            for check in payload['checklist']:
                check_links(check['evidence'], 'payload.checklist')
                if check['state'] == 'checked' and not check['evidence']:
                    error('unsupported_check', 'payload.checklist', 'Checked requires a source anchor.')
        if stage == 'review':
            computed['metrics'] = []
            for i,m in enumerate(payload['metrics']):
                loc = f'payload.metrics.{i}'
                check_links(m['evidence'], loc)
                n,d,v = m['numerator'],m['denominator'],m['value']
                if (n is None) != (d is None):
                    error('partial_fraction', loc, 'Provide both numerator and denominator, or neither.')
                if d == 0:
                    error('zero_denominator', loc, 'Zero observations do not define a ratio.')
                derived = None
                if n is not None and d is not None and d > 0:
                    if m['unit'] not in ('ratio','percent'):
                        error('fraction_unit', loc, 'Fraction needs ratio or percent units.')
                    derived = n/d * (100 if m['unit']=='percent' else 1)
                    if v is not None and not math.isclose(v, derived, rel_tol=1e-6, abs_tol=1e-8):
                        error('metric_mismatch', loc, 'Supplied value disagrees with numerator/denominator.')
                if (v is not None or derived is not None) and (not m['evidence'] or not m['collected_at']):
                    error('missing_metric_evidence', loc, 'Observed metrics need source anchors and collection time.')
                computed['metrics'].append({'name':m['name'], 'derived_value':derived,
                                            'missing':v is None and derived is None})
            if payload['observation_type']=='simulated':
                simulated = True
            if payload['observation_type']=='published' and simulated:
                error('simulation_as_publication', 'payload.observation_type', 'Simulated inputs cannot establish actual publication.')
            if payload['observation_type']=='planned':
                warnings.append('Review is a collection/experiment plan; no publication result is established.')
        if simulated and s['declared_status'] not in ('needs_review','simulation_pass'):
            error('simulation_status', 'declared_status', 'Simulation cannot become a real recording/publication result.')
        if s['unresolved'] and s['declared_status'] != 'needs_review':
            error('unresolved_status', 'declared_status', 'Unresolved items require needs_review.')
        if s['declared_status'] in ('ready_to_publish','published_observed'):
            warnings.append('Readiness/publication is a caller declaration; this validator has not independently verified it.')
        computed['scope'] = 'simulation' if simulated else 'unverified'
        warnings.append('Exact quote matching does not prove that a source supports a claim, is true, or is licensed.')
        return errors, warnings, computed, s

    @app.get(PREFIX+'/capabilities')
    def capabilities():
        return {'protocol_version':1, 'primary_client':'ai_agent',
                'reasoning_executor':'calling agent using the skill; server stores, validates and runs local media tools',
                'schemas':{s:PREFIX+'/schemas/'+s for s in [*MODELS, 'task', 'submission', 'source','media-import','media-transcribe','media-review','media-export','visual-plan','editing-template','editing-recipe','talking-profile','timeline-plan','timeline-export','music-onsets']},
                'media_editing':{'spoken_cuts':'explicit contiguous ASR word groups with reason and source/run binding',
                                 'restore':'speech_cuts=[] restores spoken groups; omitted preserves decisions',
                                 'review_attempts':'project media/<mid>/review-attempts records accepted/rejected writes'},
                'native_timeline':{'transitions':['fade','wipeleft','wiperight','slideleft','slideright','circleopen'],
                    'transition_timing':'overlap reduces total frames; reviewed music edges use transition midpoints',
                    'masks':'static rectangle/ellipse source crops with inward feather, opacity and multiplied original PNG alpha',
                    'motion_effects':['document_extract','motion_layer','spotlight','motion_text','track_matte','keyframe_layer'],
                    'limits':'32 shots with transitions, 16 masks; no automatic tracking/matting'},
                'actions':{
                    'editing_logics':{'method':'GET','path':'/api/visual/logics'},
                    'talking_profiles':{'method':'GET','path':'/api/visual/talking-profiles'},
                    'compile_talking_profile':{'method':'POST','path':'/api/projects/{pid}/talking-profile/compile','schema':PREFIX+'/schemas/talking-profile'},
                    'timeline_plans':{'method':'GET','path':'/api/projects/{pid}/timeline-plans'},
                    'save_timeline':{'method':'POST','path':'/api/projects/{pid}/timeline-plans','schema':PREFIX+'/schemas/timeline-plan'},
                    'align_timeline':{'method':'POST','path':'/api/projects/{pid}/timeline/align','schema':PREFIX+'/schemas/timeline-plan'},
                    'export_timeline':{'method':'POST','path':'/api/projects/{pid}/timeline/export','schema':PREFIX+'/schemas/timeline-export'},
                    'music_onsets':{'method':'POST','path':'/api/projects/{pid}/music-onsets','schema':PREFIX+'/schemas/music-onsets'},
                    'editing_templates':{'method':'GET','path':'/api/visual/templates'},
                    'validate_editing_recipe':{'method':'POST','path':'/api/visual/recipes/validate','schema':PREFIX+'/schemas/editing-recipe'},
                    'compile_editing_template':{'method':'POST','path':'/api/projects/{pid}/media/{mid}/visual-template/compile','schema':PREFIX+'/schemas/editing-template'},
                    'visual_status':{'method':'GET','path':'/api/visual/status'},
                    'visual_plans':{'method':'GET','path':'/api/projects/{pid}/media/{mid}/visual-plans'},
                    'visual_plan_save':{'method':'POST','path':'/api/projects/{pid}/media/{mid}/visual-plans','schema':PREFIX+'/schemas/visual-plan'},
                    'task':{'method':'POST','path':PREFIX+'/tasks','schema':PREFIX+'/schemas/task'},
                    'create_project':{'method':'POST','path':'/api/projects'},
                    'context':{'method':'GET','path':PREFIX+'/projects/{pid}/context'},
                    'add_source':{'method':'POST','path':PREFIX+'/projects/{pid}/sources'},
                    'submit':{'method':'POST','path':PREFIX+'/projects/{pid}/artifacts'},
                    'attempts':{'method':'GET','path':PREFIX+'/projects/{pid}/attempts'},
                    'import_media':{'method':'POST','path':'/api/projects/{pid}/media','schema':PREFIX+'/schemas/media-import'},
                    'transcribe':{'method':'POST','path':'/api/projects/{pid}/media/{mid}/transcribe',
                                  'schema':PREFIX+'/schemas/media-transcribe','request_body':False},
                    'review_read':{'method':'GET','path':'/api/projects/{pid}/media/{mid}/review'},
                    'review_write':{'method':'PUT','path':'/api/projects/{pid}/media/{mid}/review'},
                    'export':{'method':'POST','path':'/api/projects/{pid}/media/{mid}/export'},
                    'jobs':{'method':'GET','path':'/api/projects/{pid}/jobs'},
                    'job':{'method':'GET','path':'/api/projects/{pid}/jobs/{jid}'},
                    'calculate':{'method':'POST','path':'/api/projects/{pid}/calculate/{metrics|script_check}'}},
                'legacy_openapi':'/openapi.json', 'external_publication':False,
                'acceptance':'structural checks only; see current delivery evidence for independent acceptance scope'}

    @app.get(PREFIX+'/schemas/{name}')
    def schema(name:str):
        if name=='talking-profile':
            from talking_profiles import TalkingCompile
            return TalkingCompile.model_json_schema()
        if name in ('timeline-plan','timeline-export','music-onsets'):
            from timeline_models import TimelinePlan,TimelineExport,OnsetRequest
            return {'timeline-plan':TimelinePlan,'timeline-export':TimelineExport,'music-onsets':OnsetRequest}[name].model_json_schema()
        if name == 'editing-recipe':
            from editing_templates import RecipeDefinition
            return RecipeDefinition.model_json_schema()
        if name == 'editing-template':
            from editing_templates import CompileTemplate
            return CompileTemplate.model_json_schema()
        if name == 'visual-plan':
            from visual_models import VisualPlan
            return VisualPlan.model_json_schema()
        if name == 'task':
            from task_api import TaskRequest
            return TaskRequest.model_json_schema()
        if name == 'media-import':
            return w.MediaImport.model_json_schema()
        if name == 'media-transcribe':
            return {'title':'Local transcription: no request body', 'type':'null',
                    'description':'POST without a request body. Uses persisted local GPU strategy: NVIDIA CUDA, Windows AMD/Intel whisper.cpp Vulkan, Apple Silicon MLX, Intel Mac optional whisper.cpp Metal. CPU fallback is recorded or rejected by require_gpu. Read the terminal job.result for actual backend/device/execution/fallback errors.'}
        if name == 'media-review':
            return w.ReviewEdit.model_json_schema()
        if name == 'media-export':
            return w.ExportReview.model_json_schema()
        model = {**MODELS, 'submission':Submission, 'source':Source}.get(name)
        if model is None:
            raise HTTPException(404,'Unknown schema')
        return model.model_json_schema()

    from task_api import register_tasks
    register_tasks(w, context)

    @app.get(PREFIX+'/projects/{pid}/context')
    def get_context(pid:str):
        return context(pid)

    @app.post(PREFIX+'/projects/{pid}/sources')
    async def add_source(pid:str, request:Request):
        path = w.folder(pid)
        try:
            body = Source.model_validate(await request.json()).model_dump()
        except ValidationError as exc:
            return w.JSONResponse({'error':'schema','details':exc.errors(include_url=False, include_context=False, include_input=False)},status_code=422)
        with w.LOCK:
            project = w.read(path/'project.json')
            if body['revision'] != project['revision']:
                raise HTTPException(409, 'Project revision changed')
            sid = 'E'+uuid.uuid4().hex
            file = path/'agent/sources'/f'{sid}.txt'
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(body['content'].encode('utf-8'))
            source = {key:body[key] for key in ('label','nature','origin')}
            source.update(id=sid, relative_path=file.relative_to(path).as_posix(),
                          sha256=w.file_sha256(file), created_at=w.now(), declaration_only=True)
            project.setdefault('agent_sources', []).append(source)
            w.snapshot(path, project)
            w.event(path, 'agent_source_registered', source)
            return {'source':source, 'revision':project['revision']}

    @app.get(PREFIX+'/projects/{pid}/attempts')
    def attempts(pid:str):
        return [w.read(p) for p in sorted((w.folder(pid)/'agent/attempts').glob('*.json'))]

    @app.post(PREFIX+'/projects/{pid}/artifacts')
    async def submit(pid:str, request:Request):
        path = w.folder(pid)
        raw = await request.body()
        if len(raw)>1000000:
            raise HTTPException(413,'Submission exceeds one million bytes')
        try:
            body = json.loads(raw, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
        except (ValueError, UnicodeError):
            raise HTTPException(422,'Valid finite JSON required')
        with w.LOCK:
            request_hash = digest(body)
            if isinstance(body,dict) and isinstance(body.get('request_id'), str):
                for p in (path/'agent/attempts').glob('*.json'):
                    prior = w.read(p)
                    if isinstance(prior['request'],dict) and prior['request'].get('request_id') == body['request_id'] and prior['response'].get('accepted'):
                        if prior['request_hash'] == request_hash:
                            return {**prior['response'], 'idempotent_replay':True}
                        response = {'accepted':False, 'errors':[{'code':'request_id_reuse', 'location':'request_id', 'message':'Use a new request_id for changed input.'}]}
                        code = 409
                        break
                else:
                    response = None
            else:
                response = None
            if response is None:
                state = context(pid)
                errors,warnings,computed,s = errors_for(body,state)
                code = 409 if any(e['code'] in ('revision_conflict','context_conflict') for e in errors) else 422
                response = {'accepted':not errors, 'errors':errors, 'warnings':warnings,
                            'computed':computed, 'validation_scope':'structural_only',
                            'content_review':'required_by_calling_agent', 'external_publication':False}
                if not errors:
                    aid = 'A'+uuid.uuid4().hex
                    artifact = {**s, 'id':aid, 'created_at':w.now(), 'scope':computed['scope'],
                                'context_snapshot_path':state['context_snapshot_path'],
                                'validation':response.copy()}
                    w.write(path/'agent/artifacts'/f'{aid}.json',artifact)
                    project = w.read(path/'project.json')
                    project.setdefault('agent_heads', {})[s['stage']] = aid
                    # No user/agent declaration promotes the project's verified state.
                    w.snapshot(path,project)
                    response.update(artifact=artifact, revision=project['revision'])
                    code = 200
            attempt_id = uuid.uuid4().hex
            response['attempt_id'] = attempt_id
            w.write(path/'agent/attempts'/f'{attempt_id}.json',
                    {'at':w.now(), 'request_hash':request_hash, 'request':body, 'response':response})
            w.event(path,'agent_artifact_attempt', {'attempt_id':attempt_id, 'accepted':response['accepted']})
            return w.JSONResponse(response, status_code=code)
