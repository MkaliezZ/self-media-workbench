"""Three-tier photographic-lighting plans, deterministic diagrams and immutable history."""
import hashlib
import html
import io
import json
import math
import uuid
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response
from PIL import Image, UnidentifiedImageError
from lighting_models import Generate, Scene, Selection, FieldCheck

TIERS = [('simple','简版','少投入，先把人脸拍清楚'),
         ('standard','标准','控制阴影与背景，方便重复拍摄'),
         ('ideal','理想','在现有空间内提高控光与稳定性')]
REFERENCES = [
    {'id':'R1','title':'ARRI中文灯光手册，光线特性与基础光源',
     'url':'https://www.arri.com/en/learn/lighting/lighting-handbook'},
    {'id':'R2','title':'访谈布光：机位、自然光变化与附件',
     'url':'https://www.godox.com/solutions-video/1032.html'},
    {'id':'R3','title':'摄影棚访谈：先构图，再逐灯调整',
     'url':'https://www.indepthcine.com/videos/studio-interview'}]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def world(scene):
    return (scene.width_m or 5, scene.depth_m or 4)


def segment_hit(a,b,ob,width,depth,z1,z2):
    """Slab intersection with an opaque box, including the height of a direct ray."""
    low=[ob.x*width,ob.y*depth,0]; high=[(ob.x+ob.width)*width,(ob.y+ob.depth)*depth,ob.height_m or 100]
    start=[a[0],a[1],z1]; end=[b[0],b[1],z2]; tmin,tmax=0.0001,.9999
    for i in range(3):
        delta=end[i]-start[i]
        if abs(delta)<1e-9:
            if start[i]<low[i] or start[i]>high[i]:return False
        else:
            x,y=(low[i]-start[i])/delta,(high[i]-start[i])/delta
            tmin=max(tmin,min(x,y));tmax=min(tmax,max(x,y))
            if tmin>tmax:return False
    return True


def free(point, scene, radius=.22):
    width,depth=world(scene); x,y=point
    if not (radius<=x<=width-radius and radius<=y<=depth-radius):return False
    for ob in scene.obstacles:
        near_x=max(ob.x*width,min(x,(ob.x+ob.width)*width))
        near_y=max(ob.y*depth,min(y,(ob.y+ob.depth)*depth))
        if math.hypot(x-near_x,y-near_y)<radius:return False
    return True


def position(scene, angle, used=(), height=None):
    width,depth=world(scene); sx,sy=scene.subject.x*width,scene.subject.y*depth
    dx,dy=(scene.camera.x-scene.subject.x)*width,(scene.camera.y-scene.subject.y)*depth
    length=math.hypot(dx,dy); dx/=length;dy/=length
    for distance in (1.2,.9,1.5,.65,1.8):
        for change in (0,-12,12):
            a=math.radians(angle+change)
            x=sx+distance*(dx*math.cos(a)-dy*math.sin(a))
            y=sy+distance*(dx*math.sin(a)+dy*math.cos(a))
            if not free((x,y),scene):continue
            if any(math.hypot(x-p[0],y-p[1])<.5 for p in used):continue
            if any(o.blocks_light and segment_hit((x,y),(sx,sy),o,width,depth,height or 1.6,scene.face_height_m or 1.2) for o in scene.obstacles):continue
            return {'x':round(x/width,5),'y':round(y/depth,5)}
    return None


def height_for(scene, role):
    if scene.face_height_m is None or scene.ceiling_m is None:return None
    if scene.ceiling_m-scene.face_height_m < .3:return None
    return round(min(scene.face_height_m+(.25 if role=='key' else .35),scene.ceiling_m-.25),2)


def calculate(scene, lamp, fixture):
    if not (scene.width_m and scene.face_height_m and lamp['height_m'] and fixture and fixture.photometry):return None
    width,depth=world(scene); dx=(lamp['point']['x']-scene.subject.x)*width;dy=(lamp['point']['y']-scene.subject.y)*depth
    dz=lamp['height_m']-scene.face_height_m; distance=math.sqrt(dx*dx+dy*dy+dz*dz)
    photo=fixture.photometry
    if distance<photo.minimum_distance_m:
        return {'illuminance_lux':None,'reason':'距离小于该光度数据的有效下限，需近场/面积光源数据'}
    nx=(scene.camera.x-scene.subject.x)*width;ny=(scene.camera.y-scene.subject.y)*depth
    norm=math.hypot(nx,ny);cosine=max(0,(nx*dx+ny*dy)/(norm*distance))
    intensity=photo.reference_lux*photo.reference_distance_m**2
    return {'illuminance_lux':round(intensity*cosine/distance**2,2),'axis_intensity_cd':intensity,
            'distance_m':round(distance,3),'source':photo.model_dump(),
            'method':'轴向照度反推光强的小光源远场直射近似，满输出，受光面朝向相机；非现场实测',
            'target_lux':scene.target_lux,'dimmer_percent':None}


def generate_tiers(scene):
    width,depth=world(scene); measured=bool(scene.width_m)
    assumptions=list(scene.assumptions)
    if scene.assessment=='assumed':assumptions.append('未进行图片语义审阅；人物、机位和空间关系按可调整的默认示意，不是图像识别结果')
    if not measured:assumptions.append('尺寸未知：布局仅表示相对关系；不保证实际灯架和柔光箱能放入')
    if scene.face_height_m is None:assumptions.append('面部高度未知，灯高只给相对指引')
    if scene.ceiling_m is None:assumptions.append('层高未知，抬灯前需核对上方空间')
    elif scene.face_height_m and scene.ceiling_m-scene.face_height_m < .3:assumptions.append('面部上方余量不足，不能按常规抬灯；高度与反光需现场重新安排')
    if any(o.height_m is None for o in scene.obstacles):assumptions.append('障碍物高度未知时，挡光检查采用保守的全高遮挡')
    left=position(scene,40,height=height_for(scene,'key'));right=position(scene,-40,height=height_for(scene,'key'))
    key=right if scene.key_side=='right' else left
    if scene.key_side=='auto' and not key:key=right
    usable=next((win for win in scene.windows if win.usable),None)
    tiers=[]
    for code,name,goal in TIERS:
        lights=[];warnings=[];used=[]
        def add(role,label,point,reason,fixture=None,kind='lamp'):
            if point is None:
                warnings.append(label+'没有找到满足已知空间/障碍约束的位置；请移动人物、清理占地或改为墙面/反光方案')
                return
            z=height_for(scene,role) if kind=='lamp' else None
            lamp={'id':f'L{len(lights)+1}','role':role,'label':label,'kind':kind,'point':point,
                  'height_m':z,'height_instruction':'高于眼睛并向面部俯照；先检查眼窝、眼镜反光和上方空间' if role=='key' else '按目标区域调整，避免直射镜头',
                  'reason':reason,'aim':scene.subject.model_dump(),
                  'fixture':fixture.model_dump() if fixture else None,
                  'power':{'input_watts':fixture.input_watts if fixture else None,
                           'selection_hint':('使用已登记灯具，缺失功率按铭牌核对' if fixture else '可调连续灯与适合空间的柔光附件；额定瓦数须按型号/附件/距离核对，不按档次固定') if kind=='lamp' else '无需新增电灯',
                           'verified':False},
                  'distance_m':round(math.hypot((point['x']-scene.subject.x)*width,(point['y']-scene.subject.y)*depth),2) if measured else None,
                  'reference_ids':['R1','R2']}
            lamp['calculation']=calculate(scene,lamp,fixture) if kind=='lamp' else None
            lights.append(lamp);used.append((point['x']*width,point['y']*depth))
        first=scene.fixtures[0] if scene.fixtures else None
        if code=='simple' and usable:
            add('key','窗光主光',usable.point.model_dump(),'利用已确认可用窗光，减少器材；拍摄时段与天气变化会改变效果',kind='window')
            warnings.append('窗光方向可规划，但亮度和长时间稳定性未测量；背光/直射过强时需要窗帘或改用人工主光')
        else:
            add('key','主光',key,'从相机侧前方照向面部建立主体；位置按可用空间筛选，角度不是普适标准',first)
        if code=='simple':
            delta='优先已有器材；阴影过深时先用现有白色反光面，暂不为背景增加灯'
            compromise='对背景和长时间环境变化的控制较少；单灯不等于必须平光'
        elif code=='standard':
            fill=position(scene,-40 if key==left else 40,used)
            add('fill','反光板' if scene.look=='natural' else '负补光黑旗',fill,
                '用反射提亮阴影，避免第二个硬阴影' if scene.look=='natural' else '减少墙面回光，保留面部层次',kind='reflector' if scene.look=='natural' else 'flag')
            delta='增加对阴影的控制；主光仍可沿用简版，不因升级而强制提高瓦数'
            compromise='背景尚未独立照明；反光/遮光附件也需要占地'
        else:
            add('fill','反光板' if scene.look=='natural' else '负补光黑旗',position(scene,-40 if key==left else 40,used),
                '按内容风格控制阴影，而不是把所有区域照亮',kind='reflector' if scene.look=='natural' else 'flag')
            second=scene.fixtures[1] if len(scene.fixtures)>1 else None
            add('rim','分离光',position(scene,145,used,height_for(scene,'rim')),
                '将人物边缘与背景区分；用控光附件限制溢光，过亮或反射时可关闭',second)
            delta='在空间允许时增加独立分离控制，并安排遮光与稳定的人工光；不是越多越亮'
            compromise='需要额外占地与调光时间；分离光不是每种风格必需，空间不足时给出条件替代'
        if scene.glasses:warnings.append('戴眼镜：先从机位检查反光，调整灯的侧向/高度并试拍，不保证仅靠布局消除反射')
        if not scene.fixtures:warnings.append('未登记灯具/附件，不能给出精确瓦数、照度或调光百分比；按选型要求补型号后再计算')
        if scene.target_lux is not None:warnings.append('目标lux为用户输入，不是通用人像曝光标准；亮度调整需结合实际相机和光度数据')
        tiers.append({'id':code,'name':name,'goal':goal,'lights':lights,'upgrade':delta,'tradeoff':compromise,
                      'feasibility':'conditional' if warnings and any('没有找到' in w for w in warnings) else 'layout_checked' if measured else 'needs_dimensions',
                      'warnings':warnings,'steps':['先确认人物、相机和最宽画面，留出通道与灯架空间',
                        '只开主光/使用窗光，调位置与柔光，检查面部曝光和眼镜反光',
                        '再逐项加入本档附件/分离光，避免背景抢眼和器材入画',
                        '固定曝光与白平衡试拍，保留前后对照，每次只调整一个问题'],
                      'new_powered_lights':sum(l['kind']=='lamp' and l['fixture'] is None for l in lights)})
    return tiers,list(dict.fromkeys(assumptions))


def svg(plan,tier):
    """Diagram and report use exactly the same saved lamp positions; escaped text only."""
    esc=lambda s:html.escape(str(s),quote=True)
    scene=plan['scene']; W,H=1000,760; x0,y0,dx,dy=70,95,860,560
    if scene.get('width_m'):
        ratio=scene['width_m']/scene['depth_m'];dx=min(860,560*ratio);dy=dx/ratio
        x0=(W-dx)/2;y0=95+(560-dy)/2
    pos=lambda p:(x0+p['x']*dx,y0+p['y']*dy)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(tier["name"])}布光布局">',
           '<rect width="100%" height="100%" fill="#f7f5ef"/>',
           f'<text x="40" y="38" font-size="24" font-family="sans-serif" fill="#183f35">{esc(tier["name"])} · {esc(tier["goal"])}</text>',
           f'<text x="40" y="67" font-size="15" font-family="sans-serif" fill="#5e6965">{esc(plan["precision_label"])}</text>']
    parts.append(f'<rect x="{x0}" y="{y0}" width="{dx}" height="{dy}" fill="none" stroke="#657e71" stroke-width="2"/>')
    for ob in scene['obstacles']:
        parts.extend([f'<rect x="{x0+ob["x"]*dx}" y="{y0+ob["y"]*dy}" width="{ob["width"]*dx}" height="{ob["depth"]*dy}" fill="#d5d6d0" stroke="#858c82"/>',
                      f'<text x="{x0+ob["x"]*dx+4}" y="{y0+ob["y"]*dy+18}" font-size="13">{esc(ob["label"])}</text>'])
    for win in scene['windows']:
        x,y=pos(win['point']);parts.append(f'<circle cx="{x}" cy="{y}" r="10" fill="#8cc9df"/><text x="{x+14}" y="{y}" font-size="14">{esc(win["label"])}</text>')
    sx,sy=pos(scene['subject']);cx,cy=pos(scene['camera'])
    parts.append(f'<line x1="{cx}" y1="{cy}" x2="{sx}" y2="{sy}" stroke="#7a8780" stroke-dasharray="5 5"/>')
    for lamp in tier['lights']:
        x,y=pos(lamp['point']);color='#d59428' if lamp['kind'] in ('lamp','window') else '#7c8a9e'
        parts.extend([f'<line x1="{x}" y1="{y}" x2="{sx}" y2="{sy}" stroke="{color}" stroke-width="2" stroke-dasharray="7 5"/>',
                      f'<circle cx="{x}" cy="{y}" r="26" fill="{color}"/><text x="{x}" y="{y+8}" text-anchor="middle" font-size="22" fill="white">{lamp["id"]}</text>',
                      f'<text x="{min(max(x-45,x0+4),x0+dx-145)}" y="{y-38}" font-family="sans-serif" font-size="26" fill="#334b40">{esc(lamp["label"])}</text>'])
    parts.extend([f'<circle cx="{sx}" cy="{sy}" r="32" fill="#245b48"/><text x="{sx}" y="{sy+8}" text-anchor="middle" font-size="22" fill="white">人物</text>',
                  f'<rect x="{cx-35}" y="{cy-20}" width="70" height="40" rx="5" fill="#344b46"/><text x="{cx}" y="{cy+8}" text-anchor="middle" font-size="22" fill="white">相机</text>',
                  '<text x="40" y="700" font-size="15" font-family="sans-serif" fill="#52655c">方向均以相机朝人物看过去为准；虚线表示照向人物，不表示实测光束或照度。</text>',
                  '<text x="40" y="729" font-size="14" font-family="sans-serif" fill="#52655c">布局通过不等于现场效果通过；按编号摆放后固定曝光试拍。</text></svg>'])
    return ''.join(parts)


def register(w):
    app=w.app
    def assets(path, ids):
        p=w.read(path/'project.json'); by={a['id']:a for a in p.get('image_assets',[])}
        for aid in ids:
            if aid not in by:raise HTTPException(422,'图片不属于当前项目')
            a=by[aid];file=Path(a['path'])
            if not file.is_file() or w.file_sha256(file)!=a['sha256']:raise HTTPException(409,'图片原件变化，须重新登记和审阅')
        return [by[i] for i in ids]
    def read_plan(pid, lid):
        path=w.folder(pid)
        if len(lid)!=32 or any(c not in '0123456789abcdef' for c in lid):raise HTTPException(404,'方案不存在')
        file=path/'lighting/plans'/lid/'plan.json'
        if not file.is_file():raise HTTPException(404,'方案不存在')
        return path,w.read(file)
    @app.get('/api/lighting/status')
    def lighting_status():
        from lighting_radiance import status
        return {'tiers':[c for c,_,_ in TIERS],'image_reasoning':'calling_agent_or_explicit_user_scene; upload alone is an assumption draft',
                'radiance':status(),'ui':'/ui/#lighting','reference':'references/lighting.md'}
    @app.post('/api/projects/{pid}/lighting/images')
    async def upload(pid:str,request:Request):
        path=w.folder(pid);raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>10*1024*1024:raise HTTPException(413,'图片最多10MB')
        try:
            with Image.open(io.BytesIO(raw)) as im:
                if im.format not in ('PNG','JPEG','WEBP') or im.width*im.height>24000000:raise ValueError('请提供不超过2400万像素的PNG/JPEG/WebP')
                im.load();width,height=im.size
        except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError) as exc:raise HTTPException(422,'图片无法解码：'+str(exc))
        sha=hashlib.sha256(raw).hexdigest()
        with w.LOCK:
            p=w.read(path/'project.json')
            a=next((a for a in p.get('image_assets',[]) if a['sha256']==sha),None)
            if a:
                assets(path,[a['id']])
                return {'image':a,'revision':p['revision'],'reused':True}
            aid=uuid.uuid4().hex;file=path/'agent/assets'/(aid+'.image');file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
            name=Path(request.query_params.get('name','场景图片')).name[:120]
            a={'id':aid,'label':name,'sha256':sha,'path':str(file),'width':width,'height':height,'declaration_only':True}
            p.setdefault('image_assets',[]).append(a);w.snapshot(path,p);w.event(path,'lighting_image_registered',{'id':aid,'sha256':sha})
            return {'image':a,'revision':p['revision'],'reused':False}
    @app.get('/api/projects/{pid}/lighting/images/{aid}')
    def get_image(pid:str,aid:str):
        a=assets(w.folder(pid),[aid])[0]
        with Image.open(a['path']) as im:mime=Image.MIME.get(im.format,'application/octet-stream')
        return FileResponse(a['path'],media_type=mime,headers={'X-Content-Type-Options':'nosniff'})
    @app.get('/api/projects/{pid}/lighting/plans')
    def plans(pid:str):
        p=w.read(w.folder(pid)/'project.json')
        return {'plans':p.get('lighting_plans',[]),'head':p.get('lighting_head'),'selection':p.get('lighting_selection')}
    @app.get('/api/projects/{pid}/lighting/plans/{lid}')
    def plan(pid:str,lid:str):
        _,p=read_plan(pid,lid);return p
    @app.post('/api/projects/{pid}/lighting/plans')
    def save(pid:str,body:Generate):
        path=w.folder(pid)
        with w.LOCK:
            p=w.read(path/'project.json');sig=digest(body.model_dump())
            for prior in p.get('lighting_plans',[]):
                if prior['request_id']==body.request_id:
                    if prior['request_sha256']!=sig:raise HTTPException(409,'request_id已用于不同请求')
                    return {'plan':w.read(path/prior['relative_path']),'revision':p['revision'],'idempotent_replay':True}
            if body.project_revision!=p['revision'] or body.supersedes!=p.get('lighting_head'):raise HTTPException(409,'项目或布光方案版本已变化，请载入当前版本')
            bound=assets(path,body.scene.image_ids)
            if not bound:raise HTTPException(422,'请先登记至少一张场景图片')
            tiers,assumptions=generate_tiers(body.scene)
            from lighting_radiance import evaluate
            for tier in tiers:tier['radiance']=evaluate(body.scene,tier['lights'])
            lid=uuid.uuid4().hex;dest=path/'lighting/plans'/lid
            result={'id':lid,'created_at':w.now(),'scene':body.scene.model_dump(),
                    'source_images':[{'id':a['id'],'sha256':a['sha256'],'label':a['label']} for a in bound],
                    'precision_label':'按已确认尺寸的布局，器材占地仍须现场核对' if body.scene.width_m else '相对位置示意 · 未知尺寸，不是图片自动测量',
                    'tiers':tiers,'assumptions':assumptions,'references':REFERENCES,'supersedes':body.supersedes,
                    'revision_reason':body.revision_reason,'project_revision_at_save':p['revision'],
                    'human_acceptance':'not_tested','status':'needs_review','external_publication':False}
            w.write(dest/'plan.json',result)
            for tier in tiers:(dest/(tier['id']+'.svg')).write_text(svg(result,tier),encoding='utf-8')
            # No arbitrary photo projection: a schematic is never overlaid on uncalibrated perspective pixels.
            p.setdefault('lighting_plans',[]).append({'id':lid,'created_at':result['created_at'],'relative_path':(dest/'plan.json').relative_to(path).as_posix(),
                'request_id':body.request_id,'request_sha256':sig,'scene_sha256':digest(body.scene.model_dump())})
            p['lighting_head']=lid;p.pop('lighting_selection',None);w.snapshot(path,p);w.event(path,'lighting_plan_saved',{'id':lid,'supersedes':body.supersedes})
            return {'plan':result,'revision':p['revision']}
    @app.get('/api/projects/{pid}/lighting/plans/{lid}/files/{name}')
    def file(pid:str,lid:str,name:str):
        path,p=read_plan(pid,lid)
        if name not in ('simple.svg','standard.svg','ideal.svg','plan.json','report.html'):raise HTTPException(404,'文件不存在')
        if name=='report.html':
            sections=[]
            for tier in p['tiers']:
                rows=[]
                for lamp in tier['lights']:
                    power='无需用电' if lamp['kind']!='lamp' else str(lamp['power']['input_watts'])+'W（登记的额定输入）' if lamp['power']['input_watts'] else '瓦数待核对'
                    settings=[lamp['id'],lamp['label'],lamp['fixture']['label'] if lamp['fixture'] else lamp['power']['selection_hint'],power,
                              ('距人物平面距离 '+str(lamp['distance_m'])+'m') if lamp['distance_m'] is not None else '尺寸未知，见相对示意',
                              str(lamp['height_m'])+'m' if lamp['height_m'] is not None else lamp['height_instruction'],
                              lamp['fixture']['modifier'] if lamp['fixture'] else '附件待核对',lamp['reason']]
                    rows.append('<tr>'+''.join('<td>'+html.escape(s)+'</td>' for s in settings)+'</tr>')
                    if lamp.get('calculation'):
                        rows.append('<tr><td colspan="8">'+html.escape(json.dumps(lamp['calculation'],ensure_ascii=False))+'</td></tr>')
                rows.append('<tr><td colspan="8">'+html.escape('Radiance：'+json.dumps(tier['radiance'],ensure_ascii=False))+'</td></tr>')
                sections.append('<h2>'+tier['name']+'</h2>'+svg(p,tier)+'<p>'+html.escape(tier['upgrade'])+'</p><p>'+html.escape(tier['tradeoff'])+'</p><table>'+''.join(rows)+'</table><ol>'+''.join('<li>'+html.escape(s)+'</li>' for s in tier['steps'])+'</ol><ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in tier['warnings'])+'</ul>')
            assumptions='<ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in p['assumptions'])+'</ul>'
            assumptions+='<h2>图片观察</h2><ul>'+''.join('<li>'+html.escape(o['note'])+'</li>' for o in p['scene'].get('observations',[]))+'</ul>'
            assumptions+='<h2>方法依据</h2><ul>'+''.join('<li><a href="'+html.escape(r['url'],quote=True)+'">'+html.escape(r['title'])+'</a></li>' for r in p['references'])+'</ul>'
            return Response('<!doctype html><meta charset="utf-8"><title>三档布光方案</title><style>body{max-width:1000px;margin:30px auto;font:16px sans-serif}svg{width:100%;height:auto}td{border:1px solid #ccd5c9;padding:8px}table{border-collapse:collapse}</style><h1>三档布光方案</h1><p>'+html.escape(p['precision_label'])+'</p>'+assumptions+''.join(sections),media_type='text/html')
        return FileResponse(path/'lighting/plans'/lid/name,media_type='image/svg+xml' if name.endswith('.svg') else 'application/json',filename=name)
    @app.post('/api/projects/{pid}/lighting/plans/{lid}/select')
    def select(pid:str,lid:str,body:Selection):
        path,_=read_plan(pid,lid)
        with w.LOCK:
            p=w.read(path/'project.json')
            if body.project_revision!=p['revision'] or p.get('lighting_head')!=lid:raise HTTPException(409,'请载入当前方案后选择')
            p['lighting_selection']={'plan_id':lid,'tier':body.tier,'selected_at':w.now()};w.snapshot(path,p);w.event(path,'lighting_tier_selected',p['lighting_selection'])
            return {'selection':p['lighting_selection'],'revision':p['revision']}
    @app.post('/api/projects/{pid}/lighting/plans/{lid}/field-checks')
    def feedback(pid:str,lid:str,body:FieldCheck):
        path,_=read_plan(pid,lid)
        with w.LOCK:
            p=w.read(path/'project.json')
            if body.project_revision!=p['revision']:raise HTTPException(409,'请载入当前项目后记录试拍')
            bound=assets(path,body.image_ids);fid=uuid.uuid4().hex
            record={**body.model_dump(),'id':fid,'plan_id':lid,'created_at':w.now(),'declaration_only':True,
                    'image_hashes':{a['id']:a['sha256'] for a in bound},'human_acceptance':'not_independently_verified'}
            w.write(path/'lighting/field-checks'/f'{fid}.json',record)
            p.setdefault('lighting_field_checks',[]).append(record);w.snapshot(path,p);w.event(path,'lighting_field_check',{'id':fid,'plan_id':lid})
            return {'field_check':record,'revision':p['revision']}
