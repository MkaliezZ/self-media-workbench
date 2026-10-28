"""Historical developer diagnostic only; shooting plans never call this module.

No result here selects electrical wattage. Uploaded scene commands are never executed.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def binaries():
    from settings import CONFIG
    directory = os.environ.get('SELF_MEDIA_RADIANCE_BIN', CONFIG.get('radiance_bin', ''))
    root = Path(directory).expanduser() if directory else None
    suffix = '.exe' if os.name == 'nt' else ''
    paths = {n: (str(root / (n+suffix)) if root else shutil.which(n)) for n in ('oconv', 'rtrace')}
    return paths if all(p and Path(p).is_file() for p in paths.values()) else None


def status():
    return {'available': bool(binaries()), 'optional': True,
            'method': 'Radiance direct-light point approximation; no reflected/near-field/spectral/camera prediction',
            'auto_download': False}


def evaluate(scene, lights):
    paths = binaries()
    valid = [l for l in lights if l.get('calculation') and l['calculation'].get('illuminance_lux') is not None]
    if not paths or not valid:
        return {'state': 'unavailable' if not paths else 'insufficient_data',
                'reason': '需要已配置的Radiance，以及尺寸、面部高度和匹配附件的有效光度数据',
                'illuminance_lux': None}
    import math
    width, depth = scene.width_m, scene.depth_m
    sx, sy = scene.subject.x*width, scene.subject.y*depth
    nx, ny = (scene.camera.x-scene.subject.x)*width, (scene.camera.y-scene.subject.y)*depth
    norm = math.hypot(nx, ny); nx /= norm; ny /= norm
    rad = []
    for i, lamp in enumerate(valid):
        intensity = lamp['calculation']['axis_intensity_cd']
        radius = .005
        radiance = intensity / (math.pi*radius**2*179)
        x, y = lamp['point']['x']*width, lamp['point']['y']*depth
        z = lamp['height_m']
        rad.append(f'void light emission{i}\n0\n0\n3 {radiance} {radiance} {radiance}\n'
                   f'emission{i} sphere source{i}\n0\n0\n4 {x} {y} {z} {radius}\n')
    # Only validated numeric geometry is compiled. Unknown obstacle height is conservative.
    for i, ob in enumerate(scene.obstacles):
        if not ob.blocks_light: continue
        x,y=ob.x*width,ob.y*depth; x2,y2=(ob.x+ob.width)*width,(ob.y+ob.depth)*depth
        h=ob.height_m or scene.ceiling_m or 3
        faces=[[(x,y,0),(x2,y,0),(x2,y,h),(x,y,h)],
               [(x2,y,0),(x2,y2,0),(x2,y2,h),(x2,y,h)],
               [(x2,y2,0),(x,y2,0),(x,y2,h),(x2,y2,h)],
               [(x,y2,0),(x,y,0),(x,y,h),(x,y2,h)],
               [(x,y,h),(x2,y,h),(x2,y2,h),(x,y2,h)]]
        rad.append(f'void plastic block{i}\n0\n0\n5 0 0 0 0 0\n')
        for j, face in enumerate(faces):
            rad.append(f'block{i} polygon face{i}_{j}\n0\n0\n12 '+' '.join(str(v) for p in face for v in p)+'\n')
    env=dict(os.environ)
    binary_dir=Path(paths['rtrace']).parent
    env['PATH']=str(binary_dir)+os.pathsep+env.get('PATH','')
    env['RAYPATH']='.'+os.pathsep+str(binary_dir.parent/'lib')
    try:
        with tempfile.TemporaryDirectory(prefix='lighting-radiance-') as temp:
            root=Path(temp); file=root/'scene.rad'; octree=root/'scene.oct'
            file.write_text('\n'.join(rad),encoding='ascii')
            built=subprocess.run([paths['oconv'],str(file)],capture_output=True,env=env,cwd=root,timeout=15,check=True)
            octree.write_bytes(built.stdout)
            proc=subprocess.run([paths['rtrace'],'-I+','-ab','0','-h','-w','-dj','0','-ds','.02',str(octree)],
                input=f'{sx} {sy} {scene.face_height_m} {nx} {ny} 0\n',text=True,
                capture_output=True,env=env,cwd=root,timeout=30,check=True)
            values=[float(v) for v in proc.stdout.split()]
            if len(values)!=3 or not all(math.isfinite(v) and v>=0 for v in values):
                raise ValueError('Invalid Radiance result')
            return {'state':'done','illuminance_lux':round(179*sum(v*w for v,w in zip(values,(.265,.670,.065))),2),
                    'raw_rgb_irradiance':values,'engine':'Radiance',
                    'included_lights':[l['id'] for l in valid],
                    'excluded_lights':[l['id'] for l in lights if l not in valid],
                    'scope':'仅计入有匹配光度数据的灯，非整套方案总照度；轴向小光源直射近似，面部朝向相机，不含头部自遮挡、墙面反射、柔光近场或相机观感'}
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        return {'state':'failed','illuminance_lux':None,'reason':str(exc)[-1000:]}
