/* Guided editing is not automatic diagnosis. Empty fields stay unknown. */
'use strict';
window.DocumentForms=(()=>{
 const schemas={
  evidence:[['platform','本次平台'],['audience','受众的具体处境'],['identity','可证明的身份与经营关系'],['goal','这条内容的主目标'],['conditions','设备、时间和制作限制'],['sources','素材编号、来源与能证明什么']],
  diagnose:[['scope','连续作品范围、数量和采集时点'],['observations','观察：具体问题与对应作品/原句'],['hypotheses','原因假设与替代解释'],['unknown','缺少的数据或证据'],['priority','本轮优先处理的问题'],['next_action','一个可执行的下一步']],
  topics:[['candidates','候选：受众问题、解法与素材编号'],['selected','选定的选题与选择理由'],['promise','本条承诺交付什么'],['evidence','依据的素材编号'],['limits','适用条件与不能证明什么'],['rejected','放弃其他候选的理由']],
  script:[['topic_id','对应选题/素材编号'],['version','脚本版本与本轮修改理由']],
  publish:[['export','实际成片/字幕版本与位置'],['title','标题'],['cover','封面文字'],['description','发布说明和真实身份/示意标识'],['action','主行动与已存在的入口'],['checks','实际核对记录：成片、试读、规格与标识'],['published','实际发布链接与时间（未发就留空）']],
  review:[['account_id','账号编号'],['platform','平台'],['observations','观察与来源'],['hypotheses','原因假设、替代解释和缺失证据'],['keep','本轮保留什么'],['experiment','下一次只改变什么，如何判断']]
 };
 const spokenColumns=[['start','开始秒','number'],['end','结束秒','number'],['spoken','逐字口播','text'],['visual','可拍画面','text'],['subtitle','字幕提示','text'],['evidence_ids','素材依据','text'],['pause_s','计划停顿秒','number']];
 const metricColumns=[['id','作品编号','text'],['cohort','可比组','text'],['role','用途','role'],['provenance','数据来源','provenance'],['snapshot_hours','发布后小时','number'],['duration_s','作品时长秒','number'],['views','播放','number'],['likes','点赞','number'],['comments','评论','number'],['saves','收藏','number'],['shares','转发','number'],['followers_gained','新增关注','number'],['completed_views','完整播放','number'],['consultations','咨询','number']];
 let active='',data=null,notify=()=>{},simulation=false;
 const $=selector=>document.querySelector(selector);
 function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node}
 function columns(){return active==='script'?spokenColumns:metricColumns}
 function convertLegacy(doc){
  const next={schema_version:1,fields:{},notes:doc?.content||'',rows:[]};
  try{const raw=JSON.parse(doc?.content||'');
   if(active==='script'&&Array.isArray(raw.segments)){next.rows=raw.segments;next.notes=raw.verification||''}
   if(active==='review'&&raw.accounts?.length===1){next.fields.account_id=raw.accounts[0].id;next.fields.platform=raw.accounts[0].platform;next.rows=raw.accounts[0].videos||[];next.notes=raw.notice||''}
  }catch{}
  return next;
 }
 function mount(stage,doc,onDirty,isSimulation){
  active=stage;notify=onDirty;simulation=isSimulation;
  data=structuredClone(doc?.structured||convertLegacy(doc));data.fields||={};data.rows||=[];
  const root=$('#guidedFields');root.replaceChildren();
  for(const [key,label] of schemas[active]||[]){const box=el('div');const input=el('textarea');input.rows=2;input.value=data.fields[key]||'';input.id='field-'+key;input.oninput=()=>{data.fields[key]=input.value;notify()};const title=el('label',label);title.htmlFor=input.id;box.append(title,input);root.append(box)}
  $('#editor').value=data.notes||'';
  const relevant=['script','review'].includes(active);
  $('#rowEditor').classList.toggle('hidden',!relevant);
  $('#rowTitle').textContent=active==='script'?'逐字分镜':'发布数据';
  $('#rowGuide').textContent=active==='script'?'每段一行，保留原始素材依据。时间预算是估算，仍需实际试读。':'同一账号逐条填写，空白按缺失处理。不同观察年龄不能直接比较效果；可比组需你核对形式、受众、流量来源。';
  drawRows();
 }
 function drawRows(){
  const root=$('#dataRows');root.replaceChildren();
  if(!['script','review'].includes(active))return;
  const table=el('table');const head=el('tr');
  for(const [,label] of columns())head.append(el('th',label));head.append(el('th','行操作'));const thead=el('thead');thead.append(head);table.append(thead);
  const tbody=el('tbody');
  data.rows.forEach((row,index)=>{const tr=el('tr');for(const [key,label,type] of columns()){
   const cell=el('td');let input;
   if(['role','provenance'].includes(type)){input=el('select');const choices=type==='role'?[['baseline','基线'],['candidate','候选']]:[['user_provided','用户提供'],['observed','实际采集'],['synthetic','模拟'],['tool_estimate','工具估算']];for(const [v,t] of choices){const op=el('option',t);op.value=v;input.append(op)}input.value=row[key]||''}
   else{input=el(type==='text'&&active==='script'?'textarea':'input');if(input.tagName==='TEXTAREA')input.rows=2;else{input.type=type==='number'?'number':'text';if(type==='number'){input.step='any';input.min='0'}}input.value=row[key]??''}
   input.setAttribute('aria-label',label+' 第'+(index+1)+'行');input.oninput=()=>{row[key]=type==='number'?(input.value===''?null:Number(input.value)):input.value;notify()};cell.append(input);tr.append(cell);
  }const cell=el('td');const remove=el('button','移除此行');remove.type='button';remove.onclick=()=>{data.rows.splice(index,1);notify();drawRows()};cell.append(remove);tr.append(cell);tbody.append(tr)});
  table.append(tbody);root.append(table);
 }
 function addRow(){
  if(active==='script')data.rows.push({start:data.rows.at(-1)?.end??0,end:null,spoken:'',visual:'',subtitle:'',evidence_ids:'',pause_s:0});
  else data.rows.push({id:'V'+(data.rows.length+1),cohort:'',role:'candidate',provenance:simulation?'synthetic':'user_provided'});
  notify();drawRows();
 }
 function calculation(validate=true){
  if(data.rows.length&&active==='script'){
   let cursor=0;
   if(validate)data.rows.forEach((row,i)=>{if(typeof row.start!=='number'||typeof row.end!=='number'||!Number.isFinite(row.start)||!Number.isFinite(row.end)||row.end<=row.start)throw Error(`第${i+1}段：请填写有效的开始和结束秒数`);if(row.start!==cursor)throw Error(`第${i+1}段：开始时间须接上上一段结束时间${cursor}秒`);if(typeof row.spoken!=='string'||!row.spoken.trim())throw Error(`第${i+1}段：逐字口播为空`);if(row.pause_s!=null&&(!Number.isFinite(row.pause_s)||row.pause_s<0))throw Error(`第${i+1}段：计划停顿秒数无效`);cursor=row.end});
   return {segments:data.rows.map(row=>({...row,pause_s:row.pause_s??0}))};
  }
  if(data.rows.length&&active==='review'){
   if(validate&&(!data.fields.account_id?.trim()||!data.fields.platform?.trim()))throw Error('先填写账号编号和平台；没有真实平台时请明确写模拟平台');
   if(validate)data.rows.forEach((row,i)=>{if(!row.id?.trim()||!row.cohort?.trim())throw Error(`第${i+1}行：作品编号和可比组须填写`);for(const [key,label,type] of metricColumns){if(type==='number'&&row[key]!=null){if(!Number.isFinite(row[key])||row[key]<0)throw Error(`第${i+1}行：${label}须为非负数或留空`);if(!['snapshot_hours','duration_s'].includes(key)&&!Number.isInteger(row[key]))throw Error(`第${i+1}行：${label}须为整数`);}}});
   return {notice:simulation?'模拟验收数据，未真实发布':'用户录入，来源与定义须核对',accounts:[{id:data.fields.account_id||'',platform:data.fields.platform||'',videos:structuredClone(data.rows)}]};
  }
  try{return JSON.parse($('#editor').value)}catch{throw Error('先在表格中填写脚本或发布数据。已有完整JSON也可放入补充记录后校验。')}
 }
 function collect(){
  data.notes=$('#editor').value;
  let content=(simulation?'模拟验收数据，未真实发布。\n\n':'');
  for(const [key,label] of schemas[active]||[])content+='## '+label+'\n\n'+(data.fields[key]||'未提供')+'\n\n';
  if(data.rows.length)content+='## '+(active==='script'?'逐字分镜':'原始发布数据')+'\n\n'+JSON.stringify(calculation(false),null,2)+'\n\n';
  content+='## 补充记录\n\n'+data.notes;
  return {content,structured:structuredClone(data)};
 }
 function showResult(result){
  const root=$('#readableResult');root.replaceChildren();root.classList.remove('hidden');
  if(result.verification_level==='text_estimate_not_recording'){
   root.append(el('h3','文字预算核对'),el('p',`实算 ${result.total_counted_characters} 字；估算 ${result.estimate_fast_s}—${result.estimate_slow_s} 秒；时间轴 ${result.timeline_seconds} 秒。`));
   root.append(el('p',result.all_segments_fit_slow_estimate?'各段按当前语速假设可容纳。仍待实际试读。':'有段落超出预算，需要改稿或调整时间。','guide'));
   for(const [i,seg] of result.segments.entries())if(!seg.fits_slow_estimate)root.append(el('p',`第${i+1}段：${seg.counted_characters}字，慢速估算${seg.estimate_slow_s}秒，分配${seg.end-seg.start}秒。`));
  }else if(result.accounts){
   root.append(el('h3','指标核对'),el('p',result.contains_synthetic?'含模拟数据，未真实发布；只能验收流程和计算。':'这里只计算已提供数据，不解释因果。','guide'));
   const fmt=n=>n==null?'缺失':(n*100).toFixed(2)+'%';
   for(const account of result.accounts){root.append(el('h4',account.id+' · '+account.platform));const table=el('table');const head=el('tr');['作品','观察年龄','播放','点赞率','完整播放比例','互动合计','时间窗条件'].forEach(v=>head.append(el('th',v)));table.append(head);
    for(const row of account.videos){const tr=el('tr');[row.id,row.snapshot_hours?row.snapshot_hours+'小时':'缺失',row.views??'缺失',fmt(row.rates.like_rate),fmt(row.rates.completion_rate),row.engagements_complete??'缺字段',row.baseline_comparison_allowed?'年龄一致，仍需核对其他条件':'禁止直接比较：观察年龄不齐'].forEach(v=>tr.append(el('td',String(v))));table.append(tr)}root.append(table)
   }
   root.append(el('p','时间窗一致只满足一项比较条件，不证明同类、可比或因果；没有留存曲线不能定位某秒流失。','guide'));
  }
 }
 return {mount,addRow,collect,calculation,showResult};
})();
