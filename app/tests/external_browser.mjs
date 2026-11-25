// Chromium CDP QA using Node 24 built-ins only. No package install or mocked results.
import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const base=process.env.PORTRAIT_BASE||'http://127.0.0.1:8766';
const debug=process.env.PORTRAIT_DEBUG||'http://127.0.0.1:9225';
const evidence=resolve(process.env.PORTRAIT_EVIDENCE||'app/evidence/external_v1');
await mkdir(resolve(evidence,'screenshots'),{recursive:true});
const target=await (await fetch(debug+'/json/new?'+encodeURIComponent(base),{method:'PUT'})).json();
const socket=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((ok,fail)=>{socket.addEventListener('open',ok,{once:true});socket.addEventListener('error',fail,{once:true});});
let sequence=0;const pending=new Map();const errors=[];const requests=[];
socket.addEventListener('message',event=>{
  const message=JSON.parse(event.data);
  if(message.id){const waiter=pending.get(message.id);if(waiter){pending.delete(message.id);clearTimeout(waiter.timeout);message.error?waiter.fail(new Error(JSON.stringify(message.error))):waiter.ok(message.result);}}
  if(message.method==='Runtime.exceptionThrown')errors.push(message.params.exceptionDetails);
  if(message.method==='Network.requestWillBeSent' && message.params.request.url===base+'/api/search')requests.push(message.params.request.postData);
});
function send(method,params={}){return new Promise((ok,fail)=>{const id=++sequence;const timeout=setTimeout(()=>{pending.delete(id);fail(new Error('CDP timeout '+method));},20000);pending.set(id,{ok,fail,timeout});socket.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
async function wait(expression){for(let i=0;i<600;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw new Error('DOM condition timed out: '+expression);}
async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}
async function input(selector,value){await evaluate(`(()=>{const x=document.querySelector(${JSON.stringify(selector)});x.value=${JSON.stringify(value)};x.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
async function imagesReady(){await wait(`Array.from(document.querySelectorAll('#query-image,#results img')).every(i=>i.complete&&i.naturalWidth===256)`);}
async function screenshot(name,full=false){await evaluate('window.scrollTo(0,0)');const options={format:'png',captureBeyondViewport:full};if(full){const {cssContentSize}=await send('Page.getLayoutMetrics');options.clip={x:0,y:0,width:Math.ceil(cssContentSize.width),height:Math.ceil(cssContentSize.height),scale:1};}const data=await send('Page.captureScreenshot',options);await writeFile(resolve(evidence,'screenshots',name),Buffer.from(data.data,'base64'));}
function withoutUrl(row){const {image_url,...rest}=row;return rest;}
const checks=[];
async function upload(path){const doc=await send('DOM.getDocument');const node=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#upload-input'});await send('DOM.setFileInputFiles',{nodeId:node.nodeId,files:[resolve(path)]});await wait(`!state.busy&&document.querySelector('#crop-dialog').open&&externalUI.readyRevision===externalUI.revision&&!document.querySelector('#crop-confirm').disabled`);}
async function drag(from,to){await send('Input.dispatchMouseEvent',{type:'mouseMoved',...from});await send('Input.dispatchMouseEvent',{type:'mousePressed',...from,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseMoved',...to,button:'left',buttons:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',...to,button:'left',clickCount:1});}
async function point(a,b){return evaluate(`(()=>{const r=$('crop-canvas').getBoundingClientRect(),v=externalUI.view,c=externalUI.crop;return{x:r.left+(v.x+(c.x+c.size*${a})*v.scale)*r.width/760,y:r.top+(v.y+(c.y+c.size*${b})*v.scale)*r.height/460};})()`);}
try{
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:base});await wait(`typeof state!=='undefined'&&state.result?.status==='ok'&&!state.busy`);
  const gallery=await evaluate('JSON.parse(JSON.stringify(state.result.modes))');
  await click('#source-import');await upload(resolve(evidence,'fixtures/reencoded.png'));
  assert.equal(await evaluate(`document.querySelectorAll('#results .result-card').length`),0);
  await screenshot('crop_initial.png');checks.push('Real file picker uploads reencoded CFD image, clears previous Top5 and opens square crop/authoritative preview');
  const corner=await point(1,1);await drag(corner,{x:corner.x-55,y:corner.y-55});
  assert.ok(await evaluate('externalUI.crop.size<256&&externalUI.crop.size>100'));
  const center=await point(.5,.5);await drag(center,{x:center.x+20,y:center.y+10});
  const selected=await evaluate('JSON.parse(JSON.stringify(externalUI.crop))');
  assert.ok(selected.x>=0&&selected.y>=0&&selected.x+selected.size<=256&&selected.y+selected.size<=256);
  await click('#crop-zoom-in');await click('#crop-zoom-out');await click('#crop-pan');
  const pan=await point(.5,.5);const oldView=await evaluate('externalUI.view.x');await drag(pan,{x:pan.x+32,y:pan.y+18});
  assert.notEqual(await evaluate('externalUI.view.x'),oldView);assert.deepEqual(await evaluate('externalUI.crop'),selected);
  await wait(`externalUI.readyRevision===externalUI.revision&&!$('crop-confirm').disabled`);
  await screenshot('crop_zoom_pan.png');checks.push('Actual pointer resize/move, zoom in/out and pan retain original pixel coordinates, square aspect and bounds');
  await click('#crop-confirm');await wait(`externalUI.confirmed&&!$('crop-dialog').open`);
  assert.equal(await evaluate(`$('query-image').naturalWidth`),256);await screenshot('confirmed_256.png');
  await click('#search-button');await wait('state.busy');assert.equal(await evaluate(`document.querySelectorAll('#results .result-card').length`),0);
  await wait(`!state.busy&&(state.result!==null||$('external-state').textContent.startsWith('Failed'))`);
  const result=await evaluate('JSON.parse(JSON.stringify(state.result))');assert.equal(result?.status,'ok');assert.equal(result.candidate_count,1437);
  const pixelHash=await evaluate(`(async()=>{const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d');x.drawImage($('query-image'),0,0);const p=x.getImageData(0,0,256,256).data,b=new Uint8Array(256*256*3);for(let i=0,j=0;i<p.length;i+=4){b[j++]=p[i+2];b[j++]=p[i+1];b[j++]=p[i];}return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b))).map(v=>v.toString(16).padStart(2,'0')).join('');})()`);
  assert.equal(pixelHash,result.pixel_sha256);assert.equal(result.alignment_applied,false);
  for(const k of ['a','b','c1','c2'])assert.ok(result.extraction_status[k].status.startsWith('valid'));
  assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('#results .result-card')).map(x=>x.dataset.imageId)`),result.modes.fusion.map(x=>x.image_id));
  await imagesReady();await screenshot('external_fusion.png',true);
  const job=await evaluate('externalUI.job.job_id');const {cp}=await import('node:fs/promises');
  await cp(resolve('app/runtime/uploads',job),resolve(evidence,'browser_query'),{recursive:true,errorOnExist:true,force:false});
  await writeFile(resolve(evidence,'browser_query_result.json'),JSON.stringify(result,null,2));
  checks.push('Cropped pixels shown in browser have exact worker BGR SHA256; actual A150/B144/C1_236/C2_324 produce real SQL Top5');
  await click('[data-mode="compare"]');assert.equal(await evaluate(`document.querySelectorAll('#results .result-card').length`),25);await screenshot('external_five_modes.png',true);
  checks.push('Five comparison modes display 25 real results');
  await click('[data-mode="fusion"]');for(const [k,v]of Object.entries({a:.1,b:.2,c1:.3,c2:.4}))await input('#weight-'+k,String(v));
  await click('#search-button');await wait(`!state.busy&&state.result?.weights.a===.1`);assert.deepEqual(await evaluate('state.result.weights'),{a:.1,b:.2,c1:.3,c2:.4});
  const weighted=await evaluate('state.result.modes');await click('#search-button');await wait('!state.busy');assert.deepEqual(await evaluate('state.result.modes'),weighted);
  await input('#weight-a','.9');assert.equal(await evaluate(`$('search-button').disabled`),true);await click('#reset-weights');
  checks.push('External query applies exact changed weights, rejects invalid sum and repeats deterministically');
  await click('#source-gallery');await click('#search-button');await wait(`!state.busy&&state.result?.query.image_id==='cfd_final_00001'`);assert.deepEqual(await evaluate('state.result.modes'),gallery);
  checks.push('Gallery behavior and five baseline rankings remain unchanged after external search');
  await click('#source-import');await upload('D:/TuNam4/dataset_HF_CFD_final/images/hf_merged_00209.png');await click('#crop-confirm');await wait('externalUI.confirmed');await click('#search-button');await wait(`!state.busy&&state.result?.status==='fusion_unavailable'`);
  assert.equal(await evaluate(`document.querySelectorAll('#results .result-card').length`),0);await screenshot('external_missing_B.png');checks.push('Real parser missing hair displays missing_B/full fusion unavailable and no old Top5');
  await upload(resolve(evidence,'fixtures/no_face.png'));await click('#crop-confirm');await wait('externalUI.confirmed');await click('#search-button');await wait(`!state.busy&&$('external-state').textContent.startsWith('Failed')`);
  assert.equal(await evaluate('state.result'),null);await screenshot('external_no_face.png');checks.push('No-face extraction produces visible Failed state without fabricated landmarks/results');
  assert.equal(errors.length,0);
  const version=await send('Browser.getVersion');await writeFile(resolve(evidence,'browser_verification.json'),JSON.stringify({status:'PASS',browser:version,checks,pixelHash,crop:selected,console_exceptions:errors,screenshots:8},null,2));
  console.log(JSON.stringify({status:'PASS',checks:checks.length,pixelHash,crop:selected}));
}finally{socket.close();await fetch(debug+'/json/close/'+target.id);}
