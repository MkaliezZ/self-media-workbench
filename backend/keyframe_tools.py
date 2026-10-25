"""Authored planar compositing and restrained image finish, not a 3D renderer."""
import numpy as np
from PIL import Image,ImageChops,ImageFilter,ImageOps


def quad_valid(q):
    e=np.roll(q,-1,axis=0)-q
    c=np.array([np.linalg.det(np.array([e[i],e[(i+1)%4]])) for i in range(4)])
    return bool(np.all(c>1e-5) and q[0,0]<q[1,0] and q[3,0]<q[2,0] and q[0,1]<q[3,1] and q[1,1]<q[2,1])


def validate(cue,duration):
    keys=cue['keys'];times=[k['at'] for k in keys]
    if abs(times[0])>1e-7 or abs(times[-1]-duration)>1e-7 or any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError('Layer keys must increase strictly from zero through the full cue duration')
    if cue['edge_blur'] and not cue['focus_rect']:raise ValueError('Edge blur needs an explicit clear focus_rect')
    if cue['highlights'] and cue['highlight_delay']+cue['highlight_seconds']>duration:raise ValueError('Highlight sweep exceeds layer duration')
    crop=cue['crop']
    for r in cue['highlights']:
        if r['x']<crop['x']-1e-6 or r['y']<crop['y']-1e-6 or r['x']+r['width']>crop['x']+crop['width']+1e-6 or r['y']+r['height']>crop['y']+crop['height']+1e-6:raise ValueError('Keyframe highlight must lie inside the source crop')
    quads=[np.array([[p['x'],p['y']] for p in k['quad']],float) for k in keys]
    if any(not quad_valid(q) for q in quads):raise ValueError('Layer quad must be convex upright TL/TR/BR/BL')
    # Each interpolated corner cross product is quadratic. Inspect its exact
    # extrema, rather than accepting convex endpoints with a folded middle.
    for a,b in zip(quads,quads[1:]):
        e=np.roll(a,-1,axis=0)-a;delta=np.roll(b-a,-1,axis=0)-(b-a)
        def cross(x,y):return float(np.linalg.det(np.array([x,y])))
        for i in range(4):
            j=(i+1)%4;c0=cross(e[i],e[j]);c1=cross(delta[i],e[j])+cross(e[i],delta[j]);c2=cross(delta[i],delta[j])
            u=-c1/(2*c2) if abs(c2)>1e-12 else -1
            if 0<u<1 and c0+c1*u+c2*u*u<=1e-5:raise ValueError('Layer interpolation folds between keys')


def state(cue,t):
    from motion_tools import ease
    keys=cue['keys'];j=next((i for i in range(len(keys)-1) if t<=keys[i+1]['at']),len(keys)-2)
    a,b=keys[j],keys[j+1];p=max(0.,min(1.,(t-a['at'])/(b['at']-a['at'])))
    if cue['easing']!='linear':p=ease(p,cue['easing'])
    aq=np.array([[v['x'],v['y']] for v in a['quad']]);bq=np.array([[v['x'],v['y']] for v in b['quad']])
    return aq+(bq-aq)*p,a['opacity']+(b['opacity']-a['opacity'])*p,a['blur']+(b['blur']-a['blur'])*p


def prepare(cue,size):
    w,h=size;yy,xx=np.mgrid[0:h,0:w];x=(xx+.5)/w;y=(yy+.5)/h
    result={}
    if cue['edge_blur']:
        r=cue['focus_rect'];dx=np.maximum(np.maximum(r['x']-x,x-r['x']-r['width']),0)
        dy=np.maximum(np.maximum(r['y']-y,y-r['y']-r['height']),0)
        result['focus']=Image.fromarray(np.uint8(np.clip(np.hypot(dx,dy)/.25,0,1)*255))
    if cue['vignette']:result['shade']=1-cue['vignette']*np.clip(((x-.5)/.71)**2+((y-.5)/.71)**2,0,1)
    if cue['halftone']:result['dots']=1-cue['halftone']*(np.sin(xx*2*np.pi/5)*np.sin(yy*2*np.pi/5)*.5+.5)
    return result


def render(image,cue,t,size,n,prepared):
    from motion_tools import warp,box
    q,opacity,blur=state(cue,t);w,h=size
    if cue['highlights']:
        image=image.copy();progress=max(0.,min(1.,(t-cue['highlight_delay'])/cue['highlight_seconds']))
        for index,r in enumerate(cue['highlights']):
            amount=max(0.,min(1.,progress*len(cue['highlights'])-index))
            if amount<=0:continue
            x,y,x2,y2=box(r,*image.size);x2=x+max(1,round((x2-x)*amount));area=image.crop((x,y,x2,y2))
            rgb=ImageOps.invert(area.convert('RGB')) if cue['highlight_mode']=='invert' else ImageChops.multiply(area.convert('RGB'),Image.new('RGB',area.size,tuple(bytes.fromhex(cue['highlight_colour']))))
            rgb.putalpha(area.getchannel('A'));image.paste(rgb,(x,y))
    piece=image.crop(box(cue['crop'],*image.size))
    if cue['grayscale']:piece=Image.merge('RGBA',(*([ImageOps.grayscale(piece)]*3),piece.getchannel('A')))
    layer=Image.new('RGBA',size);warp(piece,q*np.array([w,h]),layer,1. if cue['shadow'] else 0.)
    if blur:layer=layer.filter(ImageFilter.GaussianBlur(blur))
    # Finish affects this authored layer only; subtitles/clean A-roll remain separate.
    alpha=layer.getchannel('A');rgb=layer.convert('RGB')
    if cue['edge_blur']:rgb=Image.composite(rgb.filter(ImageFilter.GaussianBlur(cue['edge_blur'])),rgb,prepared['focus'])
    if cue['chroma_pixels']:
        shift=cue['chroma_pixels'];bands=rgb.split();out=[]
        for band,dx in zip(bands,[-shift,0,shift]):
            # No cyclic wrap-around at image edges.
            shifted=Image.new('L',size);shifted.paste(band,(dx,0));out.append(shifted)
        rgb=Image.merge('RGB',tuple(out))
    if cue['vignette'] or cue['grain'] or cue['halftone']:
        a=np.asarray(rgb,dtype=np.float32)
        for key in ('shade','dots'):
            if key in prepared:a*=prepared[key][...,None]
        if cue['grain']:a+=np.random.default_rng(n+1729).normal(0,cue['grain']*255,(h,w,1))
        rgb=Image.fromarray(np.uint8(np.clip(a,0,255)))
    rgb.putalpha(alpha.point(lambda v:round(v*opacity)))
    return rgb
