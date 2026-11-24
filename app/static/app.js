'use strict';
const $ = id => document.getElementById(id);
const kinds = ['a', 'b', 'c1', 'c2'];
const modeInfo = {a:['A · Hình học','Euclid 150'], b:['B · Màu sắc','Euclid 144'], c1:['C1 · Kết cấu LBP','Chi-square × 0,5'], c2:['C2 · Root-HOG','Euclid 324'], fusion:['Fusion · Bốn bộ','Khoảng cách tổng hợp D']};
const state = {overview:null, mode:'fusion', selected:null, result:null, busy:false, galleryOffset:0, galleryTotal:0, gallerySerial:0};
function element(tag, className, text) { const el=document.createElement(tag); if(className) el.className=className; if(text!==undefined) el.textContent=text; return el; }
function message(id, text, error=false) { const el=$(id); el.textContent=text||''; el.hidden=!text; if(id==='query-notice') el.className='notice '+(error?'error':'info'); }
function format(value, digits=6) { return Number(value).toFixed(digits); }
function imageFor(item, className='') { const image=element('img',className); image.src=item.image_url; image.alt=item.filename; image.addEventListener('error',()=>{const failed=element('div','image-failed','Không đọc được ảnh nguồn. Kiểm tra catalog và file ảnh.'); failed.dataset.imageError=item.image_id; image.replaceWith(failed);}); return image; }
async function request(path, options={}) { const response=await fetch(path, {cache:'no-store',...options}); let data; try { data=await response.json(); } catch {throw new Error('Server không trả về JSON hợp lệ.');} if(!response.ok) throw new Error(data.error?.message||'Không thực hiện được yêu cầu.'); return data; }
function currentWeights() { return Object.fromEntries(kinds.map(k=>[k,Number($('weight-'+k).value)])); }
function validate() {
  const weights=currentWeights(); const values=Object.values(weights); const sum=values.reduce((a,b)=>a+b,0);
  const valid=kinds.every(k=>$('weight-'+k).value.trim()!=='') && values.every(v=>Number.isFinite(v)&&v>=0) && Math.abs(sum-1)<=1e-12;
  $('weight-total').textContent='Tổng trọng số: '+(Number.isFinite(sum)?sum.toLocaleString('vi-VN',{maximumFractionDigits:12}):'không hợp lệ');
  message('weight-error',valid?'':'Trọng số phải hữu hạn, không âm và tổng bằng 1 (sai số tuyệt đối 1e-12). Không tự chia lại trọng số.');
  $('search-button').disabled=state.busy||!valid||!state.overview;
  return valid;
}
function paintQuery(item) {
  state.selected=item; const image=$('query-image'); image.src=item.image_url; image.alt=item.filename; image.hidden=false; $('query-placeholder').hidden=true;
  $('query-filename').textContent=item.filename; $('query-source').textContent='Nguồn '+item.source.toUpperCase()+' · 256 × 256';
  $('query-features').replaceChildren(); for(const f of item.features||[]) $('query-features').append(element('span','feature-badge'+(f.status==='missing'?' missing':''),f.feature_name+(f.status==='missing'?' thiếu':' ✓')));
}
async function choose(item, run=true) { paintQuery(item); $('query-input').value=item.filename; if($('gallery-dialog').open) $('gallery-dialog').close(); if($('detail-dialog').open) $('detail-dialog').close(); if(run) await search(); }
function setMode(mode) { state.mode=mode; for(const tab of document.querySelectorAll('[data-mode]')) { const selected=tab.dataset.mode===mode; tab.classList.toggle('selected',selected); tab.setAttribute('aria-selected',String(selected)); } $('weights-fieldset').disabled=!['fusion','compare'].includes(mode); if(state.result) paintResults(); }
function resultCard(row) {
  const card=element('button','result-card'); card.type='button'; card.dataset.imageId=row.image_id; card.dataset.score=String(row.score); card.setAttribute('aria-label','Hạng '+row.rank+', '+row.filename+', khoảng cách '+row.score);
  const photo=element('div','card-photo'); photo.append(imageFor(row),element('span','rank','#'+row.rank));
  const copy=element('div','card-copy'); const name=element('strong','',row.filename); name.title=row.filename;
  const score=element('span','score',format(row.score)); score.title=String(row.score);
  copy.append(name,element('span','card-source',row.source.toUpperCase()+' · Gallery'),element('span','score-label',row.mode==='fusion'?'DISTANCE D':'DISTANCE'),score);
  card.append(photo,copy); card.addEventListener('click',()=>detail(row.image_id,row)); return card;
}
function paintResults() {
  const result=state.result; const root=$('results'); root.replaceChildren(); $('distance-body').replaceChildren();
  $('result-title').textContent=state.mode==='compare'?'So sánh năm chế độ':('Top-5 · '+modeInfo[state.mode][0]);
  $('result-meta').textContent=result.query.filename+' · '+result.candidate_count.toLocaleString('vi-VN')+' ứng viên · Loại self: '+result.self_exclusion_count;
  $('result-count').textContent=state.mode==='compare'?'5 CHẾ ĐỘ × TOP 5':'TOP 5';
  if(result.status!=='ok') { root.append(element('div','empty-state','fusion_unavailable · Ảnh thiếu B, không có kết quả từ backend bốn bộ.')); $('distance-panel').hidden=true; return; }
  const modes=state.mode==='compare'?['a','b','c1','c2','fusion']:[state.mode];
  for(const mode of modes) { const group=element('section','result-group'); group.dataset.resultMode=mode;
    if(state.mode==='compare') { const heading=element('div','group-heading'); heading.append(element('span','group-tag',mode.toUpperCase()),element('h3','',modeInfo[mode][0]),element('span','',modeInfo[mode][1])); group.append(heading); }
    const grid=element('div','result-grid'); for(const row of result.modes[mode]) grid.append(resultCard(row)); group.append(grid); root.append(group);
  }
  const tableMode=state.mode==='compare'?'fusion':state.mode;
  for(const row of result.modes[tableMode]) { const tr=element('tr'); tr.dataset.imageId=row.image_id; tr.append(element('td','',row.filename));
    for(const kind of kinds) { const td=element('td','',format(row['distance_'+kind])); td.title='Raw: '+row['distance_'+kind]+' | Normalized: '+row['normalized_'+kind]; td.append(element('small','', 'norm '+format(row['normalized_'+kind]))); tr.append(td); } tr.append(element('td','',format(row.D))); $('distance-body').append(tr);
  }
  $('distance-panel').hidden=false;
}
async function search() {
  if(!validate()||state.busy) return;
  state.busy=true; validate(); $('result-section').setAttribute('aria-busy','true'); $('search-button').textContent='Đang truy vấn SQLite…'; message('global-error','');message('query-notice','');
  try {
    const result=await request('/api/search',{method:'POST',headers:{'Content-Type':'application/json','X-Application-Token':state.overview.csrf_token},body:JSON.stringify({image:$('query-input').value.trim(),mode:state.mode,weights:currentWeights(),top_k:5})});
    state.result=result; paintQuery({...result.query,features:(await request('/api/images/'+encodeURIComponent(result.query.image_id))).features}); paintResults();
    if(result.status!=='ok') message('query-notice','fusion_unavailable — '+result.query.filename+' thiếu B: '+result.missing_reason+'. A/C1/C2 vẫn hợp lệ. Không zero-fill hoặc tự chuyển sang fusion ba bộ.',true);
  } catch(error) { state.result=null; $('results').replaceChildren(element('div','empty-state','Không có kết quả cho yêu cầu này.')); $('distance-panel').hidden=true; $('result-meta').textContent='Truy vấn không thành công';message('query-notice',error.message,true); }
  finally {state.busy=false;validate();$('result-section').setAttribute('aria-busy','false');$('search-button').replaceChildren(document.createTextNode('Tìm kiếm chân dung '),element('span','','⌕'));}
}
async function galleryPage(reset=false) {
  const serial=++state.gallerySerial;
  if(reset) {state.galleryOffset=0;$('gallery-grid').replaceChildren();} message('gallery-error','');$('gallery-more').disabled=true;
  try { const args=new URLSearchParams({q:$('gallery-filter').value.trim(),source:$('gallery-source').value,offset:state.galleryOffset,limit:24});
    const result=await request('/api/gallery?'+args); if(serial!==state.gallerySerial) return;
    state.galleryTotal=result.total;state.galleryOffset+=result.items.length; $('gallery-total').textContent=result.total.toLocaleString('vi-VN')+' ảnh';
    for(const item of result.items) { const card=element('button','gallery-card');card.dataset.imageId=item.image_id;card.title=item.filename;card.append(imageFor(item),element('strong','',item.filename)); const missing=item.features.some(f=>f.status==='missing');card.append(element('span','small-badge'+(missing?' missing':''),missing?'Thiếu B':item.source.toUpperCase()));card.addEventListener('click',()=>choose(item));$('gallery-grid').append(card); }
    if(result.total===0) $('gallery-grid').append(element('p','','Không có ảnh khớp bộ lọc.'));$('gallery-more').hidden=state.galleryOffset>=result.total;
  } catch(error) {message('gallery-error',error.message,true);} finally {if(serial===state.gallerySerial) $('gallery-more').disabled=false;}
}
function openGallery() { $('gallery-dialog').showModal(); galleryPage(true); }
async function detail(key,resultRow=null) {
  $('detail-content').replaceChildren(element('p','','Đang đọc metadata SQLite…')); $('detail-dialog').showModal();
  try { const data=await request('/api/images/'+encodeURIComponent(key)); const layout=element('div','detail-layout'); const left=element('div');left.append(imageFor(data));const use=element('button','primary','Dùng làm ảnh truy vấn');use.addEventListener('click',()=>choose(data));left.append(use);
    const right=element('div');right.append(element('h3','',data.filename));const dl=element('dl','metadata-grid');
    for(const [label,value] of [['Image ID',data.image_id],['Nguồn',data.source],['Kích thước',data.metadata.width+' × '+data.metadata.height],['Person ID nguồn',data.metadata.person_id||'Chưa có nhãn nguồn'],['Dataset version',data.metadata.dataset_version],['SHA-256',data.metadata.image_hash]]) {dl.append(element('dt','',label),element('dd','',value));}right.append(dl);layout.append(left,right);
    const content=$('detail-content');content.replaceChildren(layout);
    if(resultRow) { const section=element('section','detail-measures');section.append(element('h3','','Khoảng cách từ query hiện tại')); const raw=Object.fromEntries(kinds.map(k=>[k,{raw:resultRow['distance_'+k],normalized:resultRow['normalized_'+k]}]));section.append(element('pre','',JSON.stringify({...raw,D:resultRow.D,score:resultRow.score,mode:resultRow.mode},null,2)));content.append(section); }
    const features=element('section','detail-measures');features.append(element('h3','','Đặc trưng và metadata nguồn'));const pre=element('pre','',JSON.stringify({features:data.features,source_metadata:data.metadata.source_metadata},null,2));features.append(pre);content.append(features);
    const eyes=element('section','detail-measures');eyes.append(element('h3','','Tọa độ mắt có provenance'),element('p','','Các giá trị có role audit_remeasurement là phép đo lại khi audit; không phải bằng chứng tọa độ alignment lịch sử.'),element('pre','',JSON.stringify(data.eye_measurements,null,2)));content.append(eyes);
  } catch(error) { $('detail-content').replaceChildren(element('div','notice error',error.message)); }
}
function method() { $('method-dialog').showModal(); }
function debounce(fn,delay=200) {let handle;return (...args)=>{clearTimeout(handle);handle=setTimeout(()=>fn(...args),delay);};}
for(const button of document.querySelectorAll('[data-mode]')) button.addEventListener('click',()=>setMode(button.dataset.mode));
for(const input of document.querySelectorAll('[data-weight]')) input.addEventListener('input',()=>{validate();if(state.result?.status==='ok') message('query-notice','Trọng số mới chưa áp dụng. Nhấn Tìm kiếm để nhận kết quả từ SQLite.');});
$('reset-weights').addEventListener('click',()=>{for(const k of kinds) $('weight-'+k).value='.25';validate();if(state.result) message('query-notice','Đã đặt lại trọng số 0,25 mỗi bộ. Nhấn Tìm kiếm để áp dụng.');});
$('search-button').addEventListener('click',search);$('query-input').addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();search();}});
$('query-input').addEventListener('input',debounce(async()=>{try{const result=await request('/api/gallery?'+new URLSearchParams({q:$('query-input').value.trim(),limit:20}));$('query-suggestions').replaceChildren(...result.items.map(item=>{const option=element('option');option.value=item.filename;return option;}));}catch(error){message('global-error',error.message,true);}}));
for(const id of ['open-gallery','change-image','nav-gallery']) $(id).addEventListener('click',openGallery);
for(const id of ['nav-method','system-button','method-footer']) $(id).addEventListener('click',method);
$('nav-search').addEventListener('click',()=>{$('query-input').focus();$('overview').scrollIntoView({behavior:'smooth'});});
$('query-detail').addEventListener('click',()=>{if(state.selected) detail(state.selected.image_id);});
for(const close of document.querySelectorAll('.close-dialog')) close.addEventListener('click',()=>close.closest('dialog').close());
for(const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
$('gallery-filter').addEventListener('input',debounce(()=>galleryPage(true)));$('gallery-source').addEventListener('change',()=>galleryPage(true));$('gallery-more').addEventListener('click',()=>galleryPage(false));
$('query-image').addEventListener('error',()=>{message('query-notice','Không đọc được ảnh query. Ảnh có thể thiếu hoặc không còn khớp hash catalog.',true);});
async function init() {
  validate();
  try { state.overview=await request('/api/overview');
    for(const [id,key] of [['stat-images','image_count'],['stat-vectors','valid_vectors'],['stat-pool','comparison_pool'],['stat-missing','missing_vectors']]) $(id).textContent=state.overview[key].toLocaleString('vi-VN');
    document.querySelector('.key-hint').textContent=state.overview.image_count.toLocaleString('vi-VN')+' ảnh';
    const medians=element('div','method-median');for(const k of kinds){const box=element('div');box.append(element('strong','',k.toUpperCase()+' median'),element('span','',format(state.overview.medians[k],12)));medians.append(box);}$('method-values').replaceChildren(medians);
    $('version-details').textContent=JSON.stringify({feature_versions:state.overview.feature_versions,medians:state.overview.medians,epsilon:state.overview.epsilon,epsilon_c1:state.overview.epsilon_c1,calibration_id:state.overview.calibration_id,database_sha256:state.overview.database_sha256,readonly:state.overview.readonly,new_image_support:false},null,2);
    const data=await request('/api/images/cfd_final_00001');await choose(data);
  }catch(error){message('global-error',error.message,true);$('query-placeholder').textContent='Không đọc được gallery';}finally{validate();}
}
init();
