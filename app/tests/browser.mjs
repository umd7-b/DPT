// Chromium CDP QA using Node 24 built-ins only. No package install or mocked results.
import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const base='http://127.0.0.1:8765';
const debug='http://127.0.0.1:9224';
const evidence=resolve('app/evidence');
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
async function wait(expression){for(let i=0;i<120;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw new Error('DOM condition timed out: '+expression);}
async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}
async function input(selector,value){await evaluate(`(()=>{const x=document.querySelector(${JSON.stringify(selector)});x.value=${JSON.stringify(value)};x.dispatchEvent(new Event('input',{bubbles:true}));})()`);}
async function imagesReady(){await wait(`Array.from(document.querySelectorAll('#query-image,#results img')).every(i=>i.complete&&i.naturalWidth===256)`);}
async function screenshot(name,full=false){await imagesReady();await evaluate('window.scrollTo(0,0)');const options={format:'png',captureBeyondViewport:full};if(full){const {cssContentSize}=await send('Page.getLayoutMetrics');options.clip={x:0,y:0,width:Math.ceil(cssContentSize.width),height:Math.ceil(cssContentSize.height),scale:1};}const data=await send('Page.captureScreenshot',options);await writeFile(resolve(evidence,'screenshots',name),Buffer.from(data.data,'base64'));}
function withoutUrl(row){const {image_url,...rest}=row;return rest;}
const checks=[];
try {
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:base});
  await wait(`typeof state!=='undefined' && state.result?.status==='ok' && !state.busy`);await imagesReady();
  const baseline=JSON.parse(await readFile('database/four_feature_v1/queries/cfd_final_00001.json','utf8'));
  const initial=await evaluate('JSON.parse(JSON.stringify(state.result))');
  for(const mode of ['a','b','c1','c2','fusion'])assert.deepEqual(initial.modes[mode].map(withoutUrl),baseline.modes[mode]);
  assert.equal(await evaluate(`document.querySelector('#query-image').getAttribute('src')`),'/media/cfd_final_00001');
  assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('#results .result-card')).map(x=>({id:x.dataset.imageId,src:x.querySelector('img').getAttribute('src'),score:Number(x.dataset.score)}))`),baseline.modes.fusion.map(r=>({id:r.image_id,src:'/media/'+r.image_id,score:r.score})));
  await screenshot('desktop_fusion.png',true);checks.push('Initial query, all five API rankings, visible Top5 filenames/IDs/scores/images match SQLite baseline');
  for(const mode of ['a','b','c1','c2']){await click(`[data-mode="${mode}"]`);assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('#results .result-card')).map(x=>x.dataset.imageId)`),baseline.modes[mode].map(r=>r.image_id));assert.equal(await evaluate(`document.querySelector('#weights-fieldset').disabled`),true);}
  await click('[data-mode="fusion"]');assert.equal(await evaluate(`document.querySelector('#weights-fieldset').disabled`),false);checks.push('A/B/C1/C2 individual mode controls display their corresponding SQL rankings');
  await click('[data-mode="compare"]');assert.equal(await evaluate(`document.querySelectorAll('#results .result-group').length`),5);
  assert.equal(await evaluate(`document.querySelectorAll('#results .result-card').length`),25);
  for(const mode of ['a','b','c1','c2','fusion'])assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('[data-result-mode="${mode}"] .result-card')).map(x=>x.dataset.imageId)`),baseline.modes[mode].map(r=>r.image_id));
  await screenshot('five_mode_comparison.png',true);checks.push('Five comparison modes show 25 actual SQL results from the common pool');
  await click('[data-mode="fusion"]');await click('#results .result-card');await wait(`document.querySelector('#detail-content .metadata-grid')!==null`);
  assert.equal(await evaluate(`document.querySelector('#detail-content .detail-layout img').getAttribute('src')`),'/media/'+baseline.modes.fusion[0].image_id);
  assert.ok((await evaluate(`document.querySelector('#detail-content').textContent`)).includes('audit_remeasurement'));
  await screenshot('image_metadata.png');await click('#detail-dialog .close-dialog');checks.push('Result details show actual SQL metadata and audit eye role');
  const weights={a:.1,b:.2,c1:.3,c2:.4};for(const [kind,value] of Object.entries(weights))await input('#weight-'+kind,String(value));
  await click('#search-button');await wait(`!state.busy&&state.result?.weights.a===0.1`);
  const weighted=await evaluate('JSON.parse(JSON.stringify(state.result))');assert.deepEqual(weighted.weights,weights);
  assert.deepEqual(JSON.parse(requests.at(-1)).weights,weights);checks.push('Edited weights forwarded exactly in real HTTP request and SQL response');
  await click('#search-button');await wait('!state.busy');assert.deepEqual(await evaluate('state.result.modes'),weighted.modes);checks.push('Identical input and weights produce identical rankings/distances');
  await input('#weight-a','.9');assert.equal(await evaluate(`document.querySelector('#search-button').disabled`),true);assert.equal(await evaluate(`document.querySelector('#weight-error').hidden`),false);checks.push('Invalid sum blocks search with a visible error');
  await click('#reset-weights');await input('#query-input','hf_merged_00209.png');await click('#search-button');await wait(`!state.busy&&state.result?.query.image_id==='hf_merged_00209'`);
  assert.equal(await evaluate('state.result.status'),'fusion_unavailable');assert.equal(await evaluate(`document.querySelectorAll('#results .result-card').length`),0);
  assert.ok((await evaluate(`document.querySelector('#query-notice').textContent`)).includes('không') || (await evaluate(`document.querySelector('#query-notice').textContent`)).includes('Không'));
  await screenshot('missing_B.png');checks.push('HF00209 visibly unavailable, no fabricated or three-feature result');
  await input('#query-input','unknown.png');await click('#search-button');await wait(`!state.busy && state.result===null`);
  assert.ok((await evaluate(`document.querySelector('#query-notice').textContent`)).includes('Không tìm thấy'));
  checks.push('Unknown query produces a clear visible error and clears old results');
  await click('#open-gallery');await input('#gallery-filter','hf_merged_00001');await wait(`document.querySelectorAll('#gallery-grid .gallery-card').length===1`);
  await click('#gallery-grid .gallery-card');await wait(`!state.busy&&state.result?.query.image_id==='hf_merged_00001'`);checks.push('Gallery dialog filters and selects a real HF query');
  await click('#system-button');assert.ok((await evaluate(`document.querySelector('#method-dialog').textContent`)).includes('chưa anatomy-approved'));await click('#method-dialog .close-dialog');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await screenshot('mobile.png',true);
  assert.equal(await evaluate('document.documentElement.scrollWidth<=window.innerWidth'),true);checks.push('390px responsive viewport has no horizontal page overflow');
  await evaluate(`document.querySelector('#query-image').src='/media/browser_error_fixture_missing'`);
  await wait(`document.querySelector('#query-notice').textContent.includes('Không đọc được ảnh query')`);
  checks.push('Failed image request displays a visible query-image error without changing source images');
  await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
  assert.equal(errors.length,0);
  const version=await send('Browser.getVersion');
  await writeFile(resolve(evidence,'browser_verification.json'),JSON.stringify({status:'PASS',browser:version,viewport:{width:1600,height:1100},mobile:{width:390,height:844},checks,console_exceptions:errors,request_count:requests.length,screenshots:['desktop_fusion.png','five_mode_comparison.png','image_metadata.png','missing_B.png','mobile.png']},null,2));
  console.log(JSON.stringify({status:'PASS',checks:checks.length,browser:version.product,screenshots:5}));
} finally {socket.close();await fetch(debug+'/json/close/'+target.id);}
