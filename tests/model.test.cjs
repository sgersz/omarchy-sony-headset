const assert = require('node:assert/strict');
const {test} = require('node:test');
const {snapshot, reconcile, escapeTooltip, powerOffModes, firmwareSupportUrl} = require('../Model.js');

function fixture() {
  return {connected: true, address: '00:00:00:00:00:01', name: 'WH-1000XM5', codec: 'LDAC', firmware: '2.5.1',
    capabilities: {anc: true, ambient: true, equalizer: true},
    features: Object.fromEntries(['noiseControl','equalizer','battery','dsee','autoPowerOff'].map(key => [key, {availability:'valid'}])),
    noiseControl: {mode:'ambient', ambientLevel:17, focusOnVoice:true},
    equalizer: {preset:160, clearBass:0, bands:[-3,0,3,-2,3]}, battery:{main:97}, dsee:false, autoPowerOff:5};
}

test('tooltip markup is escaped once per display and length bounded', () => {
  assert.equal(escapeTooltip('<img src="https://invalid.test/track"> & headset'),
    '&lt;img src=&quot;https://invalid.test/track&quot;&gt; &amp; headset');
  assert.equal(escapeTooltip('&lt;img&gt;'), '&amp;lt;img&amp;gt;');
  assert.equal(escapeTooltip('x'.repeat(1000)).length, 500);
});
test('malformed state cannot replace a usable snapshot', () => {
  for (const data of [null, [], {}, {connected:'true'}]) assert.throws(() => snapshot(data));
});
test('invalid readings disable controls rather than inventing confirmed values', () => {
  const data=fixture();
  data.equalizer.bands[2]=99; data.dsee='false'; data.autoPowerOff=2.5; data.battery.main=500;
  data.noiseControl.ambientLevel=0; data.capabilities.anc='true';
  const state=snapshot(data);
  for (const key of ['equalizer','dsee','autoPowerOff','battery','noiseControl'])
    assert.equal(state.features[key].availability,'unknown',key);
  assert.equal(state.capabilities.anc,false);
  assert.equal(state.battery.main,null);
});
test('valid false and zero readings remain valid', () => {
  const data=fixture(); data.battery.main=0; data.autoPowerOff=0;
  const state=snapshot(data);
  for (const key of ['equalizer','dsee','autoPowerOff','battery','noiseControl'])
    assert.equal(state.features[key].availability,'valid',key);
  assert.equal(state.dsee,false);
});
test('ambient level and voice preference survive ANC and Off', () => {
  const data=fixture(); const initial=reconcile(null,data);
  data.noiseControl={mode:'cancelling',ambientLevel:0,focusOnVoice:false};
  const anc=reconcile(initial,data);
  data.noiseControl.mode='off';
  assert.deepEqual(reconcile(anc,data).ambientPreference,{level:17,focusOnVoice:true});
});
test('ambient preferences do not transfer to a different headset', () => {
  const data=fixture(); const initial=reconcile(null,data);
  data.address='00:00:00:00:00:02'; data.noiseControl={mode:'off',ambientLevel:0,focusOnVoice:false};
  assert.deepEqual(reconcile(initial,data).ambientPreference,{level:10,focusOnVoice:false});
});
test('failed or stale ambient readings cannot overwrite the remembered level', () => {
  const data=fixture(); const initial=reconcile(null,data);
  data.features.noiseControl.availability='stale'; data.noiseControl.ambientLevel=1;
  assert.deepEqual(reconcile(initial,data).ambientPreference,{level:17,focusOnVoice:true});
});
test('power-off mapping matches backend V2 codes including removal detection', () => {
  const modes=powerOffModes(); const state=snapshot(fixture());
  assert.equal(modes.find(mode => mode.value===state.autoPowerOff).key,'whenRemoved');
  assert.equal(modes.find(mode => mode.value===0).key,'never');
  assert.deepEqual(modes.filter(mode => mode.count).map(mode => [mode.value,mode.key,mode.count]),
    [[1,'minutes',5],[2,'minutes',30],[4,'hours',3]]);
  assert.equal(modes.find(mode => mode.value===3).key,'hour');
});
test('firmware help opens only fixed official Sony URLs', () => {
  assert.equal(firmwareSupportUrl('WH-1000XM5'),'https://www.sony.com/electronics/support/wh-1000xm5/software/00278246');
  assert.equal(firmwareSupportUrl('WH-1000XM6'),'https://www.sony.com/electronics/support');
  assert.equal(firmwareSupportUrl('https://invalid.test/'),'https://www.sony.com/electronics/support');
});
