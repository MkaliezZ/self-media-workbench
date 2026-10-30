// Adapted motion grammar from video-shotcraft, copyright 2026 Wei Yihao, Apache-2.0.
// Modified 2026-10-30: data-driven content, Chinese layouts, responsive canvases,
// shared normalized clock, frozen fonts/images, and fixed final reading hold.
// These are selected adaptations, not pixel-identical upstream demo replicas.
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Img, Freeze, staticFile, useCurrentFrame, delayRender, continueRender, cancelRender} from 'remotion';
import {DigitRoll} from './vendor/DigitRoll';

type Item = {label:string; detail:string; image?:unknown; image_file?:string};
type Shot = {kind:string; title:string; subtitle:string; initial?:string; replacement?:string;
  items?:Item[]; before_file?:string; after_file?:string; before_label?:string; after_label?:string;
  points?:{label:string; value:number}[]; unit?:string; value?:string};
export type FilmProps = {width:number; height:number; fps:number; duration_in_frames:number;
  background:string; foreground:string; accent:string; secondary:string;
  font_file:string; layout:{title:number; subtitle:number; body:number; detail:number; hero:number; tick:number}; shot:Shot};

const clamp = (n:number) => Math.max(0, Math.min(1, n));
const ramp = (f:number, start:number, duration:number) => clamp((f-start)/duration);
const out = (t:number) => 1-Math.pow(1-clamp(t),3);
const smooth = (t:number) => {t=clamp(t);return t*t*(3-2*t);};

// Marker polygon adapted from MarkerUnderlineTitle.buildStroke (seeded, no random state).
const marker = (len:number) => {
  let seed=77; const rand=()=>{let t=(seed+=0x6d2b79f5);t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};
  const a:string[]=[],b:string[]=[];
  for(let i=0;i<=40;i++){const t=i/40,wob=rand()-.5,mid=19-t*9+Math.sin(t*Math.PI*1.6+.4)*2.6+wob*1.6;
    const w=Math.max(2.2,14+Math.sin(t*Math.PI)*6-Math.max(0,t-.86)*46-Math.max(0,.06-t)*70+wob*3);
    a.push(`${t*len},${mid-w/2}`);b.push(`${t*len},${mid+w/2}`);}
  return `M${a.join('L')}L${b.reverse().join('L')}Z`;
};

export const ShotFilm:React.FC<FilmProps> = p => {
  const [handle] = useState(()=>delayRender('Load frozen font and verify layout'));
  useEffect(()=>{let cancelled=false; (async()=>{
    const font=new FontFace('FrozenShot', `url("${staticFile(p.font_file)}")`);
    await font.load(); document.fonts.add(font); await document.fonts.ready;
    if(cancelled)return;
    // Check stable layout boxes, not animated transforms. Hidden final text is checked too.
    await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
    for(const el of document.querySelectorAll<HTMLElement>('[data-fit]')){
      if(el.scrollWidth>el.clientWidth+2 || el.scrollHeight>el.clientHeight+2){
        throw new Error('Text exceeds its safe box: '+el.textContent?.slice(0,70));
      }
    }
    continueRender(handle);
  })().catch(e=>cancelRender(e));return()=>{cancelled=true;};},[handle,p.font_file]);
  const frame=useCurrentFrame();
  // All motion ends one actual second before the last frame at every output fps.
  const f=120*clamp(frame/Math.max(1,p.duration_in_frames-p.fps-1));
  const W=p.width>=p.height?1920:1080, H=W*p.height/p.width, portrait=H>W;
  const s=p.shot, margin=portrait?78:110, contentW=W-margin*2;
  const bg='#'+p.background,fg='#'+p.foreground,acc='#'+p.accent,sec='#'+p.secondary;
  const titleY=portrait?135:90, bodyY=portrait?410:310, bottom=H-125;
  const head:React.CSSProperties={position:'absolute',left:margin,top:titleY,width:contentW,height:130,
    fontSize:p.layout.title,fontWeight:700,lineHeight:1.2,whiteSpace:'pre-wrap',overflowWrap:'anywhere'};
  const sub:React.CSSProperties={position:'absolute',left:margin,top:titleY+150,width:contentW,height:100,
    color:fg,opacity:.65,fontSize:p.layout.subtitle,lineHeight:1.35,whiteSpace:'pre-wrap',overflowWrap:'anywhere'};
  const enter=(i:number):React.CSSProperties=>{const q=out(ramp(f,8+i*12,24));return{opacity:q,
    transform:`translateY(${(1-q)*44}px) scale(${.94+.06*q})`,filter:`blur(${(1-q)*5}px)`};};
  const fit=(text:React.ReactNode,style:React.CSSProperties)=> <div data-fit="true" style={style}>{text}</div>;
  const itemContent=(it:Item,style:React.CSSProperties)=> <div style={{position:'absolute',...style,overflow:'hidden',background:'#'+p.background,border:`1px solid ${fg}30`}}>
    {it.image_file && <Img src={staticFile(it.image_file)} style={{width:'100%',height:'100%',objectFit:'cover'}}/>}
    <div style={{position:'absolute',inset:0,background:it.image_file?'linear-gradient(transparent 25%, #000c)':undefined}}/>
    <div style={{position:'absolute',left:34,right:34,bottom:34}}>
      {fit(it.label,{height:p.layout.body*2.5,fontSize:p.layout.body,fontWeight:700,lineHeight:1.2,whiteSpace:'pre-wrap',overflowWrap:'anywhere'})}
      {fit(it.detail,{height:p.layout.detail*3.9,fontSize:p.layout.detail,color:fg,opacity:.75,lineHeight:1.3,whiteSpace:'pre-wrap',overflowWrap:'anywhere'})}
    </div>
  </div>;

  let body:React.ReactNode;
  if(s.kind==='typewriter-rewrite'){
    const first=Array.from(s.initial!),last=Array.from(s.replacement!);
    const n1=Math.floor(first.length*ramp(f,0,28));
    const shown=f<42?first.slice(0,n1).join(''):f<65?first.slice(0,Math.ceil(first.length*(1-ramp(f,42,23)))).join(''):last.slice(0,Math.floor(last.length*ramp(f,65,35))).join('');
    const cursor=f<100 && (f<28 || f>=42 || Math.floor(f/4)%2===0);
    const style:React.CSSProperties={position:'absolute',left:margin,top:H*.48,width:contentW,height:H*.27,
      fontSize:p.layout.hero,fontWeight:700,lineHeight:1.25,whiteSpace:'pre-wrap',overflowWrap:'anywhere'};
    body=<><div style={style}>{shown}<span style={{color:acc,opacity:cursor?1:0}}>▍</span></div>
      {fit(s.initial,{...style,visibility:'hidden'})}{fit(s.replacement,{...style,visibility:'hidden'})}</>;
  }else if(s.kind==='marker-title' || s.kind==='outline-title'){
    const q=out(ramp(f,0,25)); const lit=f>=68;
    body=<div style={{position:'absolute',left:margin,top:H*.4,width:contentW,height:H*.4,transform:`translateY(${(1-q)*30}px) scale(${s.kind==='outline-title'?1+(1-q)*1.3:1})`,opacity:q}}>
      {fit(s.title,{fontSize:p.layout.hero,lineHeight:1.25,fontWeight:700,whiteSpace:'pre-wrap',overflowWrap:'anywhere',height:H*.25,
        color:s.kind==='outline-title'&&!lit?'transparent':fg,WebkitTextStroke:s.kind==='outline-title'?`2px ${lit?acc:fg}`:undefined})}
      {s.kind==='marker-title' && <svg width={contentW} height={60} viewBox={`0 0 ${contentW} 44`} style={{position:'absolute',left:0,bottom:0}}>
        <defs><clipPath id="marker-clip"><rect width={out(ramp(f,45,20))*contentW} height={44}/></clipPath></defs>
        <path d={marker(contentW*.72)} fill={acc} clipPath="url(#marker-clip)"/>
      </svg>}
      {s.kind==='outline-title'&&lit&&<div style={{position:'absolute',inset:-25,border:`2px solid ${acc}`,opacity:(1-ramp(f,68,20))*.8,transform:`scale(${1+.3*ramp(f,68,20)})`}}/>}
    </div>;
  }else if(s.kind==='digit-roll'){
    body=<div style={{position:'absolute',left:margin,top:H*.47,width:contentW,height:H*.3}}>
      <Freeze frame={Math.round(f*.65)}><DigitRoll value={s.value!} fontSize={p.layout.hero} color={acc}/></Freeze>
      {fit(s.value,{position:'absolute',inset:0,visibility:'hidden',fontSize:p.layout.hero,height:p.layout.hero*1.3,lineHeight:1.15,whiteSpace:'nowrap'})}
    </div>;
  }else if(s.kind==='list-reveal'){
    const items=s.items!,rowH=Math.min(portrait?170:95,(bottom-bodyY)/items.length-18);
    body=items.map((it,i)=><div key={i} style={{position:'absolute',left:margin,top:bodyY+i*(rowH+18),width:contentW,height:rowH,
      background:i===0?acc+'20':fg+'08',borderLeft:`4px solid ${i===0?acc:sec}`,padding:'14px 30px',boxSizing:'border-box',...enter(i)}}>
      {fit(`${String(i+1).padStart(2,'0')}  ${it.label}`,{fontSize:p.layout.body,lineHeight:1.2,height:rowH*.55,whiteSpace:'pre-wrap',overflowWrap:'anywhere'})}
      {it.detail&&fit(it.detail,{fontSize:p.layout.detail,height:rowH*.36,lineHeight:1.2,color:fg,opacity:.65,whiteSpace:'pre-wrap',overflowWrap:'anywhere'})}
    </div>);
  }else if(s.kind==='card-stack'){
    const items=s.items!,cw=contentW*(portrait?.88:.62),ch=(bottom-bodyY)*.76;
    body=items.map((it,i)=>{const q=out(ramp(f,8+i*17,28));return <React.Fragment key={i}>
      {itemContent(it,{left:margin+(contentW-cw)/2+i*14,top:bodyY+i*22,width:cw,height:ch,opacity:q,
        transform:`translate(${(1-q)*W*.65}px,${(1-q)*90}px) rotate(${(1-q)*12+(i-(items.length-1)/2)*3}deg)`})}
    </React.Fragment>;});
    // Stacked content is not allowed to hide the preceding item's meaning.
    body=<>{body}{fit(items.map(i=>i.label).join('  /  '),{position:'absolute',left:margin,top:bottom-70,width:contentW,height:80,fontSize:p.layout.detail,lineHeight:1.3})}</>;
  }else if(s.kind==='split-screen'){
    const items=s.items!,cols=portrait?1:2,rows=Math.ceil(items.length/cols),gap=24,cw=(contentW-gap*(cols-1))/cols,ch=(bottom-bodyY-gap*(rows-1))/rows;
    body=items.map((it,i)=><React.Fragment key={i}>{itemContent(it,{left:margin+(i%cols)*(cw+gap),top:bodyY+Math.floor(i/cols)*(ch+gap),width:cw,height:ch,...enter(i)})}</React.Fragment>);
  }else if(s.kind==='before-after'){
    const q=f<52?.08+.68*out(ramp(f,8,44)):.76-.36*smooth(ramp(f,52,48));
    const h=bottom-bodyY;
    body=<div style={{position:'absolute',left:margin,top:bodyY,width:contentW,height:h,overflow:'hidden'}}>
      <Img src={staticFile(s.before_file!)} style={{width:'100%',height:'100%',objectFit:'contain'}}/>
      <div style={{position:'absolute',inset:0,clipPath:`inset(0 ${(1-q)*100}% 0 0)`,background:bg}}>
        <Img src={staticFile(s.after_file!)} style={{width:'100%',height:'100%',objectFit:'contain'}}/>
      </div>
      <div style={{position:'absolute',left:q*contentW,top:0,bottom:0,width:4,background:acc}}/>
      {fit(s.after_label,{position:'absolute',left:20,top:20,width:contentW*.4,height:70,fontSize:p.layout.body,color:fg,background:bg+'dd',padding:8})}
      {fit(s.before_label,{position:'absolute',right:20,bottom:20,width:contentW*.4,height:70,fontSize:p.layout.body,color:fg,background:bg+'dd',padding:8,textAlign:'right'})}
    </div>;
  }else if(s.kind==='line-chart'){
    const pts=s.points!,x0=portrait?140:220,x1=W-margin-50,y0=bodyY+40,y1=bottom-110;
    const max=Math.max(1,...pts.map(d=>d.value))*1.15;
    const coords=pts.map((d,i)=>({x:x0+i/(pts.length-1)*(x1-x0),y:y1-d.value/max*(y1-y0)}));
    const path=coords.map((v,i)=>`${i?'L':'M'}${v.x},${v.y}`).join(' '),draw=out(ramp(f,10,75));
    body=<svg width={W} height={H} style={{position:'absolute',inset:0}}>
      {[0,.25,.5,.75,1].map(k=><g key={k}><line x1={x0} x2={x1} y1={y1-k*(y1-y0)} y2={y1-k*(y1-y0)} stroke={fg+'20'}/>
        <text x={x0-20} y={y1-k*(y1-y0)+10} textAnchor="end" fill={fg} fontSize={p.layout.tick}>{Math.round(max*k).toLocaleString('en-US')}</text></g>)}
      <path d={path} pathLength={1} fill="none" stroke={acc} strokeWidth={7} strokeDasharray={1} strokeDashoffset={1-draw}/>
      {pts.map((d,i)=><g key={i} opacity={ramp(f,10+i*75/(pts.length-1),12)}>
        <circle cx={coords[i].x} cy={coords[i].y} r={9} fill={sec}/>
        <text x={coords[i].x} y={coords[i].y-26} textAnchor="middle" fill={fg} fontSize={p.layout.tick}>{d.value.toLocaleString('en-US')}{s.unit}</text>
        <text x={coords[i].x} y={y1+65} textAnchor="middle" fill={fg} fontSize={p.layout.tick}>{d.label}</text>
      </g>)}
    </svg>;
  }
  return <AbsoluteFill style={{background:bg,color:fg,fontFamily:'FrozenShot',overflow:'hidden'}}>
    <div style={{position:'absolute',width:W,height:H,transform:`scale(${p.width/W})`,transformOrigin:'top left'}}>
      <div style={{position:'absolute',left:margin,top:portrait?90:54,width:56,height:5,background:acc}}/>
      {s.kind!=='marker-title'&&s.kind!=='outline-title'&&fit(s.title,head)}
      {(s.kind==='marker-title'||s.kind==='outline-title')&&fit(s.subtitle,{...head,fontSize:p.layout.subtitle,color:sec})}
      {s.kind!=='marker-title'&&s.kind!=='outline-title'&&fit(s.subtitle,sub)}
      {body}
    </div>
  </AbsoluteFill>;
};
