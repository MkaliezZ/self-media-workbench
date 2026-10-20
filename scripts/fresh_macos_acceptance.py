#!/usr/bin/env python3
"""Independent native-macOS fresh-install acceptance. Host uses stdlib only.

This is a deterministic acceptance driver, not a live LLM Agent. It orchestrates
real public product protocols. Run on a genuinely fresh public clone and venv.
Model download requires --download-models; inference is then forced offline.
"""
import argparse
import difflib
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path
from urllib.request import urlopen

MODELS = [
    ("ct2", "Systran/faster-whisper-tiny", "d90ca5fe260221311c53c58e660288d3deb8d356"),
    ("mlx", "mlx-community/whisper-tiny-mlx", "6caf9c55601caafbe6508a8b0d216bdf4783c4e8"),
]
DESIGN_PUBLIC_COMMIT = "85ffa38bcf321694c7a84d94f24a72a9e7c626d7"
FIRST = "This is a synthetic desk reset demonstration. Before starting a writing task, put a blue notebook beside the keyboard. Move the empty cup away from the computer. Never place a drink above the keyboard."
SECOND = "Now set a short timer and write one clear question on the first page. Close unrelated windows, then begin the first paragraph. This demonstration uses generated speech and a generated background. It does not report an actual customer result."
BRIEF = ("SYNTHETIC ACCEPTANCE MATERIAL. Newly authored for this independent run.\n"
         "Audience: someone preparing a desk for a short writing task.\n"
         "Goal: a practical desk reset explanation, not a claim about measured productivity.\n"
         "Keep the safety qualification about drinks. The inserted two-second blank pause may be removed.\n"
         "No real account, customer, performance, publication, or recorded footage is represented.\n\n" + FIRST + "\n\n" + SECOND + "\n")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Audit:
    def __init__(self, args):
        self.args = args
        self.root = Path(args.root).resolve()
        self.out = Path(args.out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.logs = self.out / "calls"
        self.logs.mkdir(exist_ok=True)
        self.env = os.environ.copy()
        self.n = 0
        self.results = []
        self.base = None
        self.state = self.out / "state"
        self.agent = self.out / "agent-home"
        self.hf = self.out / "hf-home"
        self.py = self.root / ".venv/bin/python"
        self.started_at = time.time()

    def save(self, name, obj):
        dest = self.out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return dest

    def check(self, name, condition, detail=None, fatal=True):
        self.results.append({"check": name, "passed": bool(condition), "detail": detail})
        self.save("checks.json", self.results)
        if not condition and fatal:
            raise AssertionError(name + ": " + str(detail))

    def run(self, name, command, env=None, timeout=180, ok=(0,), cwd=None):
        self.n += 1
        prefix = self.logs / (f"{self.n:03d}-" + re.sub(r"[^A-Za-z0-9_.-]", "_", name))
        meta = {"name": name, "command": [str(v) for v in command], "cwd": str(cwd or self.root), "started_at": time.time()}
        try:
            p = subprocess.run(meta["command"], cwd=cwd or self.root, env=env or self.env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            meta.update(returncode=p.returncode, elapsed_seconds=time.time()-meta["started_at"])
            stdout, stderr = p.stdout, p.stderr
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or b"", exc.stderr or b""
            meta.update(returncode=None, timeout=True, elapsed_seconds=time.time()-meta["started_at"])
        prefix.with_suffix(".stdout.txt").write_bytes(stdout)
        prefix.with_suffix(".stderr.txt").write_bytes(stderr)
        prefix.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        if meta["returncode"] not in ok:
            raise RuntimeError(name + " failed: " + json.dumps(meta) + "\n" + stderr.decode("utf-8", "replace")[-2000:])
        return stdout.decode("utf-8", "replace")

    def cli(self, name, *args):
        raw = self.run(name, [self.py, "-B", self.root / "workbench.py", *args])
        value = json.loads(raw)
        self.save("responses/"+name+".json", value)
        if isinstance(value, dict) and value.get("service_url"):
            self.base = value["service_url"]
        return value

    def call(self, name, method, route, body=None):
        args = ["call", method, route]
        if body is not None:
            args += ["--json", str(self.save("requests/"+name+".json", body))]
        return self.cli(name, *args)

    def wait(self, name, pid, job, timeout=1200):
        history = []
        deadline = time.monotonic()+timeout
        while True:
            data = self.call(name+f"-{len(history):03d}", "GET", f"/api/projects/{pid}/jobs/{job['id']}")
            history.append(data)
            self.save("jobs/"+name+".json", history)
            if data["status"] in ("done", "failed", "interrupted", "cancelled"):
                self.check(name+" terminal done", data["status"] == "done", data)
                return data
            if time.monotonic() > deadline:
                raise TimeoutError(name+" did not reach terminal status")
            time.sleep(3)

    def setup(self):
        self.check("native macOS", sys.platform == "darwin", sys.platform)
        native = platform.machine()
        self.check("expected native architecture", native == self.args.expect, native)
        self.run("uname", ["uname", "-a"])
        self.run("hardware", ["system_profiler", "SPHardwareDataType", "SPDisplaysDataType"], timeout=120)
        self.check("root is Git checkout", (self.root/".git").exists())
        remote = self.run("git-origin", ["git", "remote", "get-url", "origin"]).strip()
        self.check("public origin", remote.rstrip("/").removesuffix(".git") == "https://github.com/MkaliezZ/self-media-workbench", remote)
        self.commit = self.run("git-commit", ["git", "rev-parse", "HEAD"]).strip()
        self.initial_status = self.run("git-initial-status", ["git", "status", "--porcelain"])
        self.check("clean new clone", not self.initial_status.strip(), self.initial_status)
        for rel in ["README.md", "AGENTS.md", "docs/configuration.md", "docs/apple-gpu.md", "skills/media-workbench/SKILL.md", "skills/media-workbench/scripts/run.py", "skills/self-media-workflow/SKILL.md", "skills/self-media-workflow/references/script.md", "skills/self-media-workflow/references/media.md"]:
            dest = self.out / "public-protocol" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.root/rel, dest)
        self.check("new venv exists", self.py.is_file())
        banned = [k for k in self.env if k.startswith("SELF_MEDIA_") and k != "SELF_MEDIA_STATE_DIR"]
        self.check("no config environment bypass", not banned, banned)
        for key, path in [("SELF_MEDIA_STATE_DIR", self.state), ("CODEX_HOME", self.agent), ("HF_HOME", self.hf)]:
            self.check(key+" isolated", key not in self.env or Path(self.env[key]).resolve() == path, self.env.get(key))
            self.env[key] = str(path)
        self.check("new state/config", not (self.state/"config.json").exists() and not any((self.state/"projects").glob("*")) and not any((self.state/"services").glob("*.json")))
        self.fresh_state_confirmed = True
        self.check("new Agent home", not (self.agent/"skills").exists())
        self.check("new HF cache", not any(p for p in self.hf.rglob("*") if p.is_file()))
        for path in (self.state, self.agent, self.hf):
            path.mkdir(parents=True, exist_ok=True)
        self.env.update(PYTHONNOUSERSITE="1", HF_HUB_DISABLE_XET="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        inventory_code = "import sys,platform,json,importlib.util; print(json.dumps(dict(executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,machine=platform.machine(),deps={x:importlib.util.find_spec(x) is not None for x in ['fastapi','numpy','faster_whisper','mlx_whisper','huggingface_hub']})))"
        inv = json.loads(self.run("venv-inventory", [self.py, "-c", inventory_code]))
        self.save("venv-inventory.json", inv)
        self.check("actual isolated venv", Path(inv["prefix"]).resolve() == (self.root/".venv").resolve() and inv["prefix"] != inv["base_prefix"], inv)
        self.check("host outside product venv", Path(sys.prefix).resolve() != Path(inv["prefix"]).resolve(), {"host":sys.prefix,"venv":inv["prefix"]})
        self.run("pip-check", [self.py, "-m", "pip", "check"])
        self.cli("doctor-before-configure", "doctor")
        self.check("download explicitly authorized", self.args.download_models)
        paths = {}
        for kind, repo, revision in MODELS:
            if kind == "mlx" and native != "arm64":
                continue
            destination = self.hf / "models" / kind
            downloader = '''import hashlib,json,sys
from pathlib import Path
from huggingface_hub import HfApi,snapshot_download
repo,revision,destination,cache,manifest_path=sys.argv[1:]
info=HfApi().model_info(repo,revision=revision,files_metadata=True)
remote={s.rfilename:s for s in info.siblings}
p=Path(snapshot_download(repo_id=repo,revision=revision,local_dir=destination,cache_dir=cache))
files=[]
for f in sorted(p.rglob('*')):
 if not f.is_file() or '.cache' in f.parts: continue
 rel=f.relative_to(p).as_posix()
 with f.open('rb') as stream: actual_sha256=hashlib.file_digest(stream,'sha256').hexdigest()
 sibling=remote.get(rel)
 lfs=getattr(sibling,'lfs',None)
 expected_sha256=(lfs.get('sha256') if isinstance(lfs,dict) else getattr(lfs,'sha256',None)) if lfs else None
 expected_blob=getattr(sibling,'blob_id',None)
 blob=hashlib.sha1()
 blob.update(b'blob '+str(f.stat().st_size).encode()+b'\\0')
 with f.open('rb') as stream:
  for block in iter(lambda:stream.read(1048576),b''): blob.update(block)
 actual_blob=blob.hexdigest()
 verified=(actual_sha256==expected_sha256) if expected_sha256 else bool(expected_blob and actual_blob==expected_blob)
 files.append(dict(path=rel,bytes=f.stat().st_size,sha256=actual_sha256,expected_lfs_sha256=expected_sha256,expected_git_blob_id=expected_blob,actual_git_blob_id=None if expected_sha256 else actual_blob,verification='LFS SHA256' if expected_sha256 else 'Git blob SHA1',verified=verified))
result=dict(repo=repo,requested_revision=revision,resolved_revision=info.sha,source='https://huggingface.co/'+repo+'/tree/'+revision,local_path=str(p),files=files,all_hashes_verified=bool(files) and all(f['verified'] for f in files) and info.sha==revision)
Path(manifest_path).parent.mkdir(parents=True,exist_ok=True)
Path(manifest_path).write_text(json.dumps(result,indent=2)+'\\n',encoding='utf-8')
print(json.dumps(result))
raise SystemExit(0 if result['all_hashes_verified'] else 3)
'''
            online = dict(self.env, HF_HUB_OFFLINE="0", TRANSFORMERS_OFFLINE="0")
            manifest = json.loads(self.run("authorized-download-"+kind, [self.py, "-c", downloader, repo, revision, destination, self.hf/"hub", self.out/"models"/(kind+"-manifest.json")], env=online, timeout=1800))
            self.save("models/"+kind+"-manifest.json", manifest)
            self.check(kind+" pinned upstream hashes verified", manifest["all_hashes_verified"], manifest)
            paths[kind] = destination
        configure = ["configure", "--model", str(paths["ct2"]), "--data-dir", str(self.state/"projects"), "--language", "en", "--asr-backend", "auto", "--device", "auto"]
        if "mlx" in paths:
            configure += ["--mlx-model", str(paths["mlx"])]
        cfg = self.cli("configure-real-models", *configure)
        disk = json.loads(Path(cfg["config_file"]).read_text())
        self.save("config-on-disk.json", disk)
        self.check("configure persisted model", disk["model"] == str(paths["ct2"]) and disk["language"] == "en" and disk["device"] == "auto", disk)
        if native == "arm64":
            self.check("configure persisted MLX model", disk.get("mlx_model") == str(paths["mlx"]))
        doctor = self.cli("doctor-after-configure", "doctor")
        self.check("doctor actual paths", doctor["model_present"] and Path(doctor["state_dir"]) == self.state and Path(doctor["data_dir"]) == self.state/"projects", doctor)
        self.check("doctor dependencies", all(doctor["dependencies"].values()) and all(doctor["executables"].values()), doctor)
        installed = self.cli("install-skill", "install-skill")
        self.wrapper = Path(installed["installed"])/"scripts/run.py"
        self.check("installed entry isolated", self.wrapper.is_relative_to(self.agent) and self.wrapper.is_file(), str(self.wrapper))
        foreign = self.out/"foreign-python"
        self.run("create-foreign-python", [sys.executable, "-m", "venv", "--without-pip", str(foreign)])
        self.foreign_py = foreign/"bin/python"
        foreign_inv = json.loads(self.run("foreign-inventory", [self.foreign_py,"-c",inventory_code]))
        self.check("foreign Python lacks product deps", not any(foreign_inv["deps"].values()), foreign_inv)
        self.save("isolation.json", {"root":str(self.root),"commit":self.commit,"host_executable":sys.executable,"host_prefix":sys.prefix,"product_python":str(self.py),"foreign_python":str(self.foreign_py),"state":str(self.state),"agent_home":str(self.agent),"hf_home":str(self.hf),"environment":{k:v for k,v in self.env.items() if k in ["SELF_MEDIA_STATE_DIR","CODEX_HOME","HF_HOME","HF_HUB_OFFLINE","TRANSFORMERS_OFFLINE","PYTHONNOUSERSITE"]},"driver_kind":"independently orchestrated deterministic acceptance, not live LLM Agent"})

    def text_workflow(self):
        material = self.out/"materials"
        material.mkdir(exist_ok=True)
        brief = material/"new-synthetic-brief.txt"
        brief.write_text(BRIEF, encoding="utf-8")
        session = "independent-fresh-"+self.commit[:12]
        self.session = session
        self.auto_start_attempted = True
        raw = self.run("foreign-entry-first-task", [self.foreign_py,self.wrapper,"run","Write a practical spoken script from this synthetic desk reset brief.","--input",brief,"--intent","script","--new","--simulation","--title","Synthetic desk reset first use","--session",session], cwd=material)
        task = json.loads(raw)
        self.save("responses/first-task.json",task)
        self.base = task["service_url"]
        self.pid = task["project_id"]
        self.check("first task actually creates", task["project_created"] and task["start_at"] == "script" and bool(task["registered"]), task)
        records = list((self.state/"services").glob("*.json"))
        self.check("service auto-start identity", len(records)==1, [str(p) for p in records])
        self.service_record = json.loads(records[0].read_text())
        status = self.call("service-status", "GET", "/api/status")
        self.check("matching service root/model", Path(status["root"]).resolve()==self.root and status["model_present"] and self.service_record["base_url"]==self.base, status)
        capabilities = self.call("capabilities", "GET", "/api/agent/v1/capabilities")
        for name in ["task","submission","script","media-import","media-transcribe","media-review","media-export"]:
            self.cli("schema-"+name,"schema",name)
            self.check("schema discoverable "+name, name in capabilities["schemas"])
        state = self.cli("context-before-script", "context", self.pid)
        source = next(s for s in state["sources"] if FIRST in s["content"])
        self.check("synthetic source retained intact", source["nature"]=="simulation" and source["integrity"] and source["sha256"]==sha(brief), source)
        self.check("public bundled method", Path(state["skill"]["entry"]).resolve()==self.root/"skills/self-media-workflow/SKILL.md", state["skill"])
        payload = {"topic_artifact_id":None,"topic_id":None,"claims":[{"id":"C1","text":"A fictional desk reset demonstration with generated speech and background.","kind":"fictional","evidence":[{"source_id":source["id"],"quote":FIRST}],"limitation":"Synthetic demonstration; no productivity or customer evidence."}],"segments":[{"id":"S1","start":0.0,"end":19.0,"spoken":FIRST,"visual":"Generated blue background; illustrative desk labels to be added by a human if needed.","subtitle":FIRST,"claim_ids":["C1"]},{"id":"S2","start":19.0,"end":40.0,"spoken":SECOND,"visual":"Generated background only; no real desk footage.","subtitle":SECOND,"claim_ids":["C1"]}],"cta":"Write one clear question before the first paragraph.","production_limits":["Synthetic speech and background; no measured human reading or actual customer result."]}
        def submit(name, st, body, supersedes=None, reason=None):
            submission = {"request_id":name,"revision":st["project"]["revision"],"context_id":st["context_id"],"stage":"script","input_artifact_ids":[],"standalone_reason":"Focused first-use script request from provided synthetic brief; no account diagnosis or topic research requested.","payload":body,"declared_status":"needs_review","unresolved":["Human delivery and final visual review pending."],"supersedes":supersedes,"revision_reason":reason}
            path = self.save("requests/"+name+".json",submission)
            result = self.cli(name,"submit",self.pid,"--json",path)
            self.check(name+" accepted actual artifact", result.get("accepted") and result.get("artifact",{}).get("id") is not None, result)
            return result["artifact"]
        initial = submit("script-initial",state,payload)
        # Real production revision after timing/visual review, not an injected failure.
        timing_input = self.save("script-initial-payload.json",payload)
        timing_output = self.out/"script-speaking-budget.json"
        self.run("script-speaking-budget",[self.py,self.root/"skills/self-media-workflow/scripts/script_check.py",timing_input,"--out",timing_output])
        timing = json.loads(timing_output.read_text())
        self.check("speaking budget measured exact text",timing["total_counted_characters"]>0 and len(timing["segments"])==2,timing)
        self.save("script-production-review.json", {"finding":"The first draft estimates time and mentions desk labels that this generated-background fixture does not implement. Revise the visual promise and explicitly retain the drink safety qualification. The bundled character-budget checker does not establish English pronunciation timing; inspect its fit fields and retain that limitation.","character_budget_fits":timing["all_segments_fit_slow_estimate"],"initial_artifact":initial["id"],"synthetic":True})
        revised = json.loads(json.dumps(payload))
        revised["segments"][0]["visual"]="Generated blue background only; illustrative fixture, no desk labels or recorded footage."
        revised["production_limits"].append("Retain the full sentence: Never place a drink above the keyboard. Timing remains a production estimate; measure the generated audio separately.")
        st = self.cli("context-before-revision","context",self.pid)
        final = submit("script-revised",st,revised,initial["id"],"Remove unimplemented label promise and explicitly preserve the safety qualification after production review.")
        self.final_script = final
        latest = self.cli("context-after-script","context",self.pid)
        self.check("initial and revision retained", len([a for a in latest["artifacts"] if a["stage"]=="script"])==2 and latest["heads"]["script"]==final["id"] and final["supersedes"]==initial["id"])

    def media_workflow(self):
        material = self.out/"materials"
        for label,text in [("first",FIRST),("second",SECOND)]:
            path = material/(label+".txt")
            path.write_text(text, encoding="utf-8")
            self.run("say-"+label,["say","-v","Samantha","-r","155","-f",path,"-o",material/(label+".aiff")])
        first_probe = json.loads(self.run("probe-first-speech",["ffprobe","-v","error","-show_format","-of","json",material/"first.aiff"]))
        gap_start = float(first_probe["format"]["duration"])
        self.run("compose-synthetic-audio",["ffmpeg","-hide_banner","-v","error","-nostdin","-y","-i",material/"first.aiff","-i",material/"second.aiff","-filter_complex","[0:a]aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono[a0];anullsrc=r=16000:cl=mono:d=2[gap];[1:a]aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono[a1];[a0][gap][a1]concat=n=3:v=0:a=1[out]","-map","[out]","-c:a","pcm_s16le",material/"synthetic-original.wav"])
        video = material/"synthetic-source.mp4"
        self.run("wrap-explicit-generated-video",["ffmpeg","-hide_banner","-v","error","-nostdin","-y","-f","lavfi","-i","color=c=0x204866:s=640x360:r=25","-i",material/"synthetic-original.wav","-shortest","-c:v","libx264","-preset","fast","-pix_fmt","yuv420p","-c:a","aac","-metadata","comment=SYNTHETIC: native generated speech and generated color background; independent acceptance fixture",video])
        self.save("materials/provenance.json", {"synthetic":True,"speech_engine":"macOS say Samantha, 155 words/minute","authored_text":[FIRST,SECOND],"inserted_blank_pause":{"start":gap_start,"end":gap_start+2},"video":"generated solid-color wrapping; not recorded footage","source_sha256":sha(video),"no_actual_customer_or_publication_claim":True})
        imported = self.call("import-generated-source","POST",f"/api/projects/{self.pid}/media",{"path":str(video),"media_nature":"generated","source_note":"Independently authored synthetic desk-reset demonstration; native generated speech, two-second inserted blank pause, generated solid-color video wrapping.","usage_scope":"Local acceptance only. Remove inserted blank pause; preserve all spoken safety qualifications. No external publication."})
        media = imported["media"]
        self.mid = media["id"]
        self.check("immutable source actual hash", media["sha256"]==sha(video) and media["media_nature"]=="generated")
        prefix = f"/api/projects/{self.pid}/media/{self.mid}"
        job = self.call("transcribe-submit","POST",prefix+"/transcribe")
        terminal = self.wait("actual-asr",self.pid,job)
        self.asr_execution = terminal["result"]
        review = self.call("original-review","GET",prefix+"/review")
        words = review["words"]
        self.check("ASR actual nonempty word bounds", len(words)>=30 and all(0<=w["start"]<w["end"]<=review["duration"]+0.01 for w in words), {"words":len(words),"duration":review["duration"]})
        normalized = lambda text: re.findall(r"[a-z]+",text.lower())
        expected = normalized(FIRST+" "+SECOND)
        actual = normalized(review["text"])
        matcher = difflib.SequenceMatcher(None,expected,actual,autojunk=False)
        matched = sum(b.size for b in matcher.get_matching_blocks())
        recall = matched/len(expected)
        self.save("asr-content-check.json",{"expected_tokens":expected,"actual_tokens":actual,"ordered_token_recall":recall,"actual_asr_text":review["text"],"not_human_listening":True})
        self.check("ASR fresh content ordered recall", recall>=0.75,recall)
        self.check("negative safety qualification recognized", "never" in actual and "keyboard" in actual, actual)
        original = Path(review["source"]).parent/"asr"/review["asr_run"]/"transcript.original.json"
        self.check("original ASR file exists",original.is_file(),str(original))
        original_hash = sha(original)
        # Native speech includes a little natural edge silence. A valid candidate
        # must contain the known inserted gap's midpoint, stay near its extent,
        # and independently avoid every actual ASR word group.
        candidates = [c for c in review["candidates"] if c["start"]<=gap_start+1<=c["end"] and c["start"]>=gap_start-.8 and c["end"]<=gap_start+2.8 and c["end"]-c["start"]>=.35 and all(w["end"]<=c["start"] or w["start"]>=c["end"] for w in words)]
        self.check("explicit inserted pause candidate",bool(candidates),{"known_gap":[gap_start,gap_start+2],"candidates":review["candidates"]})
        cut = max(candidates,key=lambda c:c["end"]-c["start"])
        self.check("cut excludes all speech groups",all(w["end"]<=cut["start"] or w["start"]>=cut["end"] for w in words),cut)
        groups,current = [],[]
        for word in words:
            current.append(word["id"])
            if word["text"].rstrip().endswith((".","!","?",",")) or len(current)>=7:
                groups.append(current);current=[]
        if current:groups.append(current)
        edit = {"revision":review.get("revision",0),"asr_run":review["asr_run"],"source_sha256":review["source_sha256"],"corrections":{},"selected_ids":[cut["id"]],"speech_cuts":[],"caption_groups":groups}
        self.save("review-reason.json",{"pause_id":cut["id"],"reason":"Remove only the deliberately inserted synthetic non-speech blank pause inside the known two-second fixture interval. All speech is retained.","caption_grouping":"Use actual ASR IDs in order, punctuation or at most seven model word groups. Automated structural review, not human player review."})
        edited = self.call("review-save","PUT",prefix+"/review",edit)
        r = edited["review"]
        self.check("ASR word bounds unchanged after review",[(w["id"],w["start"],w["end"],w["text"]) for w in r["words"]]==[(w["id"],w["start"],w["end"],w["text"]) for w in words])
        self.check("original ASR immutable",sha(original)==original_hash)
        export = self.call("export-submit","POST",prefix+"/export",{"revision":r["revision"],"asr_run":r["asr_run"],"source_sha256":r["source_sha256"]})
        finished = self.wait("actual-export",self.pid,export)
        eid = finished["result"]["export_id"]
        source_copy = Path(review["source"])
        self.check("copied immutable original unchanged",sha(source_copy)==sha(video))
        export_dir = source_copy.parents[2]/"exports"/eid
        self.check("export files actually exist",all((export_dir/n).is_file() for n in finished["result"]["files"]),str(export_dir))
        delivered = self.out/"delivered"/eid
        shutil.copytree(export_dir,delivered)
        self.run("decode-output-entire-file",["ffmpeg","-hide_banner","-v","error","-nostdin","-i",delivered/"reviewed_cut.mp4","-map","0:v:0","-map","0:a:0","-f","null","-"],timeout=300)
        self.run("extract-output-proof-frame",["ffmpeg","-hide_banner","-v","error","-nostdin","-y","-ss","1","-i",delivered/"reviewed_cut.mp4","-frames:v","1",delivered/"proof-frame.png"])
        probe = json.loads(self.run("probe-output",["ffprobe","-v","error","-show_format","-show_streams","-of","json",delivered/"reviewed_cut.mp4"]))
        self.save("output-probe.json",probe)
        mapped = json.loads((delivered/"reviewed_cut.words.json").read_text())
        plan = json.loads((delivered/"edit-decision.json").read_text())
        provenance = json.loads((delivered/"provenance.json").read_text())
        self.check("export source/run/revision provenance",provenance["source_sha256"]==sha(video) and provenance["asr_run"]==r["asr_run"] and provenance["review_revision"]==r["revision"] and provenance["external_publication"] is False,provenance)
        self.check("all source words retained once",[w["id"] for w in mapped]==[w["id"] for w in words])
        cursor = 0.0
        windows=[]
        for keep in plan["keeps"]:
            windows.append((keep["start"],keep["end"],cursor));cursor+=keep["end"]-keep["start"]
        for source_word,output_word in zip(words,mapped):
            matching=[v for v in windows if source_word["start"]>=v[0]-1e-6 and source_word["end"]<=v[1]+1e-6]
            self.check("word timeline "+str(source_word["id"]),len(matching)==1 and abs(output_word["source_start"]-source_word["start"])<1e-6 and abs(output_word["source_end"]-source_word["end"])<1e-6 and abs(output_word["start"]-(source_word["start"]-matching[0][0]+matching[0][2]))<2e-6 and abs(output_word["end"]-(source_word["end"]-matching[0][0]+matching[0][2]))<2e-6 and output_word["text"]==source_word["text"],output_word)
        output_duration=float(probe["format"]["duration"])
        self.check("export duration matches explicit keeps",abs(output_duration-cursor)<0.2,{"actual":output_duration,"expected":cursor})
        self.check("only intended blank pause removed",abs(review["duration"]-cursor-(cut["end"]-cut["start"]))<0.03)
        self.check("decoded audio and video present",{s["codec_type"] for s in probe["streams"]}>={"audio","video"})
        srt=(delivered/"reviewed_cut.srt").read_text(encoding="utf-8")
        cues=[b.splitlines() for b in srt.strip().split("\n\n")]
        def seconds(text):
            h,m,tail=text.split(":");sec,ms=tail.split(",");return int(h)*3600+int(m)*60+int(sec)+int(ms)/1000
        self.check("SRT explicit group count",len(cues)==len(groups))
        lookup={w["id"]:w for w in mapped}
        for index,(cue,group) in enumerate(zip(cues,groups),1):
            a,b=cue[1].split(" --> ")
            self.check("SRT group "+str(index),int(cue[0])==index and "\n".join(cue[2:])=="".join(lookup[i]["text"] for i in group) and abs(seconds(a)-lookup[group[0]]["start"])<.0011 and abs(seconds(b)-lookup[group[-1]]["end"])<.0011 and seconds(b)<=output_duration+.05,{"cue":cue,"group":group})
        after=self.cli("context-after-export","context",self.pid)
        self.check("actual export context binding",any(e["id"]==eid for e in after["exports"]))
        resumed=json.loads(self.run("foreign-entry-resume",[self.foreign_py,self.wrapper,"run","Continue this project and inspect the existing script for a later review.","--project",self.pid,"--intent","script","--session",self.session],cwd=material))
        self.save("responses/resumed-project.json",resumed)
        self.check("existing project resume retains work",resumed["project_id"]==self.pid and not resumed["project_created"] and resumed["context"]["heads"]["script"]==self.final_script["id"] and any(e["id"]==eid for e in resumed["context"]["exports"]),resumed)
        services=list((self.state/"services").glob("*.json"))
        self.check("resume reuses same service",len(services)==1 and json.loads(services[0].read_text())["pid"]==self.service_record["pid"] and resumed["service_url"]==self.base)
        if self.args.expect=="arm64":
            self.check("actual MLX Metal GPU ASR",review.get("backend")=="mlx" and review.get("device")=="gpu" and review.get("execution",{}).get("gpu_kernel_verified") is True and not review.get("fallback_errors"),self.asr_execution,fatal=False)
        else:
            self.check("actual Intel CPU ASR",review.get("backend")=="faster-whisper" and review.get("device")=="cpu",self.asr_execution,fatal=False)
        self.check("product source unchanged",self.run("git-final-status",["git","status","--porcelain"])==self.initial_status)

    def finish(self, error=None):
        cleanup={"only_own_service":True}
        # A fresh state directory cannot contain any preexisting service. Still
        # validate both checkout identity and the live process command before SIGTERM.
        own_records = list((self.state/"services").glob("*.json")) if getattr(self,"fresh_state_confirmed",False) and getattr(self,"auto_start_attempted",False) else []
        for record in own_records:
            try:
                info=json.loads(record.read_text())
                if Path(info["root"]).resolve()!=self.root:
                    raise RuntimeError("service root mismatch; will not terminate")
                cmd=self.run("cleanup-process-identity",["ps","-p",str(info["pid"]),"-o","command="],ok=(0,1)).strip()
                if cmd:
                    if str(self.root/"workbench.py") not in cmd or "serve" not in cmd:
                        raise RuntimeError("process command mismatch; will not terminate")
                    os.kill(info["pid"],signal.SIGTERM)
                    cleanup.update(pid=info["pid"],terminated=True,command=cmd)
            except Exception as exc:
                cleanup["error"]=repr(exc)
        self.save("cleanup.json",cleanup)
        if self.state.exists():
            shutil.copytree(self.state,self.out/"state-snapshot",dirs_exist_ok=True)
        if self.agent.exists():
            shutil.copytree(self.agent,self.out/"agent-home-snapshot",dirs_exist_ok=True)
        shutil.copy2(Path(__file__),self.out/"acceptance-driver.py")
        failures=[item for item in self.results if not item["passed"]]
        summary={"passed":error is None and not failures,"architecture":platform.machine(),"expected_architecture":self.args.expect,"platform":sys.platform,"commit":getattr(self,"commit",None),"design_protocol_public_clone_commit":DESIGN_PUBLIC_COMMIT,"elapsed_seconds":time.time()-self.started_at,"driver_kind":"independent deterministic cloud acceptance orchestration; not a live LLM Agent","synthetic_fixture":True,"checks":len(self.results),"failures":failures,"exception":error,"asr_execution":getattr(self,"asr_execution",None),"limits":["Automated protocol/content/timeline/decode checks do not establish human listening, player subtitle appearance, marketing usefulness, customer validation or readiness for publication.","No external publication performed."]}
        self.save("final-result.json",summary)
        self.save("failure.json",{"failed":not summary["passed"],"exception":error,"checks":failures})
        excluded={"hf-home","foreign-python",".git"}
        files=[]
        for path in sorted(self.out.rglob("*")):
            if path.is_file() and not any(part in excluded for part in path.relative_to(self.out).parts) and path.name!="evidence-manifest.json":
                files.append({"path":path.relative_to(self.out).as_posix(),"bytes":path.stat().st_size,"sha256":sha(path)})
        self.save("evidence-manifest.json",files)
        print(json.dumps(summary,ensure_ascii=False,indent=2))
        return 0 if summary["passed"] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",required=True)
    parser.add_argument("--out",required=True)
    parser.add_argument("--expect",choices=["arm64","x86_64"],default=platform.machine())
    parser.add_argument("--download-models",action="store_true",help="Explicit authorization to download pinned public tiny test weights during installation only")
    args=parser.parse_args()
    audit=Audit(args)
    error=None
    try:
        audit.setup()
        audit.text_workflow()
        audit.media_workflow()
    except BaseException as exc:
        error={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        try:
            return audit.finish(error)
        except BaseException as exc:
            emergency={"passed":False,"exception":error,"finalization_exception":repr(exc),"traceback":traceback.format_exc()}
            audit.save("final-result.json",emergency)
            audit.save("failure.json",emergency)
            print(json.dumps(emergency))
            return 1


if __name__=="__main__":
    raise SystemExit(main())
