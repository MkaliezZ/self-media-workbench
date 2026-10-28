"""Reproducible isolated HTTP integration run; synthetic declarations, no real room claims.

Usage: python evaluation/run_lighting_acceptance.py --base http://127.0.0.1:PORT --out ABS_DIR
The calling Agent has separately inspected scene-demo.png; this script does not parse images.
"""
import argparse
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not args.base.startswith('http://127.0.0.1:'):
        raise ValueError('Use an isolated loopback service')
    args.out.mkdir(parents=True,exist_ok=True)
    def api(path,body=None,raw=None):
        data=raw if raw is not None else json.dumps(body,ensure_ascii=False).encode() if body is not None else None
        req=Request(args.base+path,data=data,headers={'Content-Type':'application/octet-stream' if raw else 'application/json'})
        with urlopen(req,timeout=90) as r:return json.load(r)
    p=api('/api/projects',{'title':'布光合成平面图 · 技术验收','simulation':True})
    route='/api/projects/'+p['id']+'/lighting'
    image=api(route+'/images?name=scene-demo.png',raw=(Path(__file__).parent/'fixtures/lighting/scene-demo.png').read_bytes())
    first=api(route+'/plans',{'request_id':uuid.uuid4().hex,'project_revision':image['revision'],'scene':{'image_ids':[image['image']['id']]}})
    scene={'image_ids':[image['image']['id']],'assessment':'agent_reviewed',
        'observations':[{'image_id':image['image']['id'],'note':'Agent查看合成图：标注4m×3m，窗在左侧，左下为柜子，人物在中间，相机在下方；没有层高、柜高或灯具测光信息。'}],
        'assumptions':['合成技术验收：层高2.6m、面部1.2m、柜高1.8m为额外假设，并非图片事实。','窗光仅为演示可利用光源，不代表真实天气或现场照度。','模拟灯78W与1000lux@1m是测试输入，不是真实产品测光数据。'],
        'width_m':4.0,'depth_m':3.0,'ceiling_m':2.6,'face_height_m':1.2,
        'subject':{'x':470/860,'y':275/620},'camera':{'x':470/860,'y':544/620},
        'windows':[{'point':{'x':0.0,'y':.33},'usable':True,'note':'合成图左侧窗户；可用性为测试假设'}],
        'obstacles':[{'label':'柜子','x':45/860,'y':295/620,'width':185/860,'depth':170/620,'height_m':1.8}],
        'fixtures':[{'label':'模拟灯（合成数据）','input_watts':78.0,'modifier':'裸灯','photometry':{
            'reference_lux':1000.0,'reference_distance_m':1.0,'modifier':'裸灯','cct_k':5600,
            'source':'合成数学输入，不是真实厂商或现场测光','measured_at':'synthetic','basis':'user_measurement','minimum_distance_m':.5}}]}
    current=api(route+'/plans',{'request_id':uuid.uuid4().hex,'project_revision':first['revision'],'supersedes':first['plan']['id'],
        'revision_reason':'按Agent实际查看的合成图补场景；额外高度和光度均标记为假设','scene':scene})
    plan=current['plan']
    assert [t['id'] for t in plan['tiers']]==['simple','standard','ideal']
    assert plan['tiers'][0]['lights'][0]['kind']=='window'
    assert len(api(route+'/plans')['plans'])==2
    for filename in ('simple.svg','standard.svg','ideal.svg','plan.json','report.html'):
        with urlopen(args.base+route+'/plans/'+plan['id']+'/files/'+filename) as response:
            (args.out/filename).write_bytes(response.read())
    result={'project':p['id'],'plan':plan['id'],'revision':current['revision'],'url':args.base+'/ui/lighting.html?project='+p['id'],
        'three_tiers':True,'history_preserved':True,'assessment':plan['scene']['assessment'],
        'radiance':[{'tier':t['id'],**t['radiance']} for t in plan['tiers']],
        'scope':'synthetic HTTP integration and caller-reviewed fixture; not real-world lighting acceptance'}
    (args.out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
