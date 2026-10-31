// Original explanatory diagram implementations, 2026-10-31.
// Motion mechanisms were studied from a user-provided reference; no source video,
// branded icons, presenter likeness, music or third-party implementation is copied.
import React from 'react';

export type DiagramSpec = {kind:string; center?:string; nodes?:string[];
  direction?:'relation'|'inward'|'outward'; label?:string; rows?:number; columns?:number;
  conclusion?:string; layers?:string[]; steps?:string[]; step_probability?:number|null;
  independent_assumption?:boolean; fail_step?:number|null; data_note?:string};

type Props = {shot:DiagramSpec; f:number; W:number; H:number; bodyY:number;
  foreground:string; accent:string; secondary:string; background:string;
  layout:{body:number; detail:number; hero:number; tick:number}};

const clamp=(x:number)=>Math.max(0,Math.min(1,x));
const ramp=(f:number,start:number,duration:number)=>clamp((f-start)/duration);
const ease=(x:number)=>1-Math.pow(1-clamp(x),3);

export const DiagramFilm:React.FC<Props> = p => {
  const {shot:s,f,W,H,bodyY,layout}=p;
  const fg='#'+p.foreground,acc='#'+p.accent,sec='#'+p.secondary,bg='#'+p.background;
  const portrait=H>W, margin=portrait?78:110,cw=W-2*margin,bottom=H-190;
  const label=(text:string,x:number,y:number,w:number,h:number,size=layout.body,opacity=1)=>
    <div data-fit="true" style={{position:'absolute',left:x,top:y,width:w,height:h,
      display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',
      fontSize:size,lineHeight:1.25,fontWeight:600,whiteSpace:'pre-wrap',overflowWrap:'anywhere',opacity}}>{text}</div>;
  const node=(text:string,x:number,y:number,w:number,h:number,q:number,color=acc)=>
    <div style={{position:'absolute',left:x-w/2,top:y-h/2,width:w,height:h,
      background:bg,border:`2px solid ${color}`,boxSizing:'border-box',opacity:q,
      transform:`translateY(${(1-q)*18}px)`}}>
      {label(text,12,8,w-24,h-16)}
    </div>;
  const line=(x1:number,y1:number,x2:number,y2:number,q:number,color=acc,arrow=false)=>
    <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={3}
      pathLength={1} strokeDasharray="1" strokeDashoffset={1-q} opacity={q}
      markerEnd={arrow&&q>.95?'url(#diagram-arrow)':undefined}/>;
  let body:React.ReactNode;
  let note='结构示意；位置、大小与数量不代表测量值';
  const cy=(bodyY+bottom)/2;
  if(s.kind==='concept-network'){
    const nx=W/2,rx=cw*.34,ry=(bottom-bodyY)*.37,nw=portrait?240:270,nh=100;
    const positions=s.nodes!.map((text,i)=>{const a=-Math.PI/2+i*2*Math.PI/s.nodes!.length;
      return {text,x:nx+Math.cos(a)*rx,y:cy+Math.sin(a)*ry,q:ease(ramp(f,12+i*10,18))};});
    body=<><svg width={W} height={H} style={{position:'absolute',inset:0}}>
      <defs><marker id="diagram-arrow" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={7} markerHeight={7} orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill={acc}/></marker></defs>
      {positions.map((v,i)=>{const dx=v.x-nx,dy=v.y-cy,len=Math.hypot(dx,dy),ux=dx/len,uy=dy/len;
        const edge=(w:number,h:number)=>Math.min(Math.abs(ux)<.0001?Infinity:w/2/Math.abs(ux),Math.abs(uy)<.0001?Infinity:h/2/Math.abs(uy));
        const a=edge(300,116)+8,b=edge(nw,nh)+8;
        const x1=nx+ux*a,y1=cy+uy*a,x2=v.x-ux*b,y2=v.y-uy*b;
        return <g key={i}>{s.direction==='inward'?line(x2,y2,x1,y1,v.q,acc,true):line(x1,y1,x2,y2,v.q,acc,s.direction==='outward')}</g>;})}
    </svg>{node(s.center!,nx,cy,300,116,ease(ramp(f,0,18)),sec)}
      {positions.map((v,i)=><React.Fragment key={i}>{node(v.text,v.x,v.y,nw,nh,v.q)}</React.Fragment>)}
    </>;
  }else if(s.kind==='concept-matrix'){
    const rows=s.rows!,cols=s.columns!,areaH=bottom-bodyY-100,cell=Math.min(cw/(cols+1),areaH/(rows+1),portrait?125:100);
    const x0=(W-(cols-1)*cell)/2,y0=bodyY+(areaH-(rows-1)*cell)/2;
    const conclusion=ease(ramp(f,76,20)); note=s.data_note!;
    body=<><svg width={W} height={H} style={{position:'absolute',inset:0,opacity:1-conclusion*.78}}>
      {Array.from({length:rows*cols},(_,i)=>{const row=Math.floor(i/cols),col=i%cols,q=ease(ramp(f,6+row*10+col*2,14));
        return <g key={i} transform={`translate(${x0+col*cell} ${y0+row*cell}) scale(${.7+.3*q})`} opacity={q}>
          <circle r={cell*.32} fill={acc}/><path d={`M${-cell*.11} ${-cell*.08}v${cell*.16} M${cell*.11} ${-cell*.08}v${cell*.16}`} stroke={bg} strokeWidth={cell*.055} strokeLinecap="round"/>
        </g>;})}
    </svg>{label(s.label!,margin,bottom-90,cw,70,layout.body)}
      <div style={{position:'absolute',left:margin,top:cy-85,width:cw,height:170,background:bg+'ed',opacity:conclusion,
        transform:`translateY(${(1-conclusion)*20}px)`}}>{label(s.conclusion!,32,12,cw-64,146,layout.hero)}</div>
    </>;
  }else if(s.kind==='layered-rings'){
    const rx=cw*.46,ry=(bottom-bodyY)*.45,n=s.layers!.length;
    const rings=s.layers!.map((text,i)=>({text,rx:rx*(.52+.48*(i+1)/n),ry:ry*(.36+.64*(i+1)/n),q:ease(ramp(f,12+i*24,22))}));
    body=<><svg width={W} height={H} style={{position:'absolute',inset:0}}>
      {rings.map((v,i)=><ellipse key={i} cx={W/2} cy={cy} rx={v.rx} ry={v.ry} pathLength={1}
        stroke={i===n-1?sec:acc} strokeWidth={3} fill="none" strokeDasharray="1" strokeDashoffset={1-v.q} opacity={v.q}/>)}
    </svg>{node(s.center!,W/2,cy,300,106,ease(ramp(f,0,18)))}
      {rings.map((v,i)=><div key={i} style={{position:'absolute',left:W/2-190,top:cy-v.ry-28,width:380,height:56,background:bg,opacity:v.q}}>
        {label(v.text,8,3,364,50,layout.body)}
      </div>)}
    </>;
  }else{
    const steps=s.steps!,n=steps.length,hasP=s.step_probability!=null,hasFail=s.fail_step!=null;
    const lineBottom=bottom-(hasP||hasFail?185:60),nw=portrait?Math.min(cw*.7,620):Math.min(235,cw/n-35),nh=portrait?100:135;
    const positions=steps.map((text,i)=>({text,x:portrait?W/2:margin+nw/2+i*(cw-nw)/(n-1),
      y:portrait?bodyY+nh/2+i*(lineBottom-bodyY-nh)/(n-1):bodyY+(lineBottom-bodyY)/2,
      q:ease(ramp(f,6+i*9,18))}));
    note=hasP?'独立、同概率示意模型；不是实测成功率。'+s.data_note:(hasFail?'失败路径示意。'+s.data_note:note);
    const fail=s.fail_step?positions[s.fail_step-1]:null,failed=ease(ramp(f,80,18));
    body=<><svg width={W} height={H} style={{position:'absolute',inset:0}}>
      {positions.slice(1).map((v,i)=>{const a=positions[i];return <g key={i}>{line(a.x+(portrait?0:nw/2),a.y+(portrait?nh/2:0),v.x-(portrait?0:nw/2),v.y-(portrait?nh/2:0),v.q)}</g>;})}
      {fail&&<g opacity={failed}>{line(fail.x,fail.y+nh/2,portrait?W-margin-30:W-margin, bottom-35,failed,sec)}
        <path d={`M${W-margin-42} ${bottom-47}l24 24m0 -24l-24 24`} stroke={sec} strokeWidth={5}/></g>}
    </svg>{positions.map((v,i)=><React.Fragment key={i}>{node(`${i+1}  ${v.text}`,v.x,v.y,nw,nh,v.q,s.fail_step===i+1&&failed>.5?sec:acc)}</React.Fragment>)}
      {hasP&&label(`(${(s.step_probability!*100).toFixed(1)}%) ^ ${n} = ${(Math.pow(s.step_probability!,n)*100).toFixed(1)}%`,margin,bottom-140,cw,120,layout.hero,ease(ramp(f,76,20)))}
      {hasFail&&label('局部失败可能使结果偏离',margin,bottom-130,cw*.75,100,layout.body,failed)}
    </>;
  }
  return <>{body}{label(note,margin,H-150,cw,105,layout.tick,.7)}</>;
};
