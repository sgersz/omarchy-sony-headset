function text(value, limit) {
  return typeof value === "string" ? value.substring(0, limit || 120) : "";
}
function escapeTooltip(value) {
  return text(value, 500).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function number(value, minimum, maximum, fallback) {
  return typeof value === "number" && isFinite(value) && value >= minimum && value <= maximum
    ? value : fallback;
}
function integer(value, minimum, maximum) {
  return number(value, minimum, maximum, null) !== null && Math.floor(value) === value;
}
function firmwareSupportUrl(name) {
  return name === "WH-1000XM5" || name === "WH-1000XM5SA"
    ? "https://www.sony.com/electronics/support/wh-1000xm5/software/00278246"
    : "https://www.sony.com/electronics/support";
}
// sonyd 0.1.6 ProtocolV2::APO_CODES, not the full app's mismatched UI labels.
function powerOffModes() {
  return [
    {value: 0, key: "never"}, {value: 1, key: "minutes", count: 5},
    {value: 2, key: "minutes", count: 30}, {value: 3, key: "hour"},
    {value: 4, key: "hours", count: 3}, {value: 5, key: "whenRemoved"}
  ];
}
function snapshot(data) {
  if (!data || typeof data !== "object" || Array.isArray(data) || typeof data.connected !== "boolean") throw new Error("Invalid Sony state");
  var result = { connected: data.connected === true, name: text(data.name, 80),
    deviceKey: text(data.address, 80) || text(data.name, 80),
    codec: text(data.codec, 40), firmware: text(data.firmware, 40),
    connectionState: text(data.connectionState, 40), lastError: text(data.lastError, 240),
    capabilities: {}, features: {}, battery: {}, noiseControl: {}, equalizer: {} };
  var capabilities = ["anc", "ambient", "focusOnVoice", "equalizer", "clearBass", "tenBandEqualizer",
    "dsee", "battery", "speakToChat", "adaptiveVolume", "autoPowerOff"];
  capabilities.forEach(function(key) { result.capabilities[key] = !!data.capabilities && data.capabilities[key] === true; });
  ["battery", "noiseControl", "equalizer", "dsee", "speakToChat", "adaptiveVolume", "autoPowerOff", "codec", "firmware"].forEach(function(key) {
    var f = data.features && data.features[key];
    result.features[key] = { availability: f && ["valid", "stale", "unknown", "unsupported"].indexOf(f.availability) >= 0 ? f.availability : "unknown",
      error: f ? text(f.error, 240) : "" };
  });
  var battery = data.battery || {};
  ["main", "left", "right", "case"].forEach(function(key) { result.battery[key] = number(battery[key], 0, 100, null); });
  result.battery.charging = battery.charging === true;
  var noise = data.noiseControl || {};
  result.noiseControl = { mode: ["cancelling", "ambient", "off"].indexOf(noise.mode) >= 0 ? noise.mode : "",
    ambientLevel: number(noise.ambientLevel, 1, 20, 10), focusOnVoice: noise.focusOnVoice === true };
  var eq = data.equalizer || {};
  result.equalizer = { preset: number(eq.preset, 0, 255, -1), presetName: text(eq.presetName, 40),
    clearBass: number(eq.clearBass, -10, 10, 0), bands: [] };
  if (Array.isArray(eq.bands) && eq.bands.length <= 10)
    result.equalizer.bands = eq.bands.map(function(value) { return number(value, -10, 12, 0); });
  ["dsee", "speakToChat", "adaptiveVolume"].forEach(function(key) { result[key] = data[key] === true; });
  result.autoPowerOff = number(data.autoPowerOff, 0, 5, -1);
  var readings = {
    battery: ["main", "left", "right", "case"].some(function(key) { return result.battery[key] !== null; }),
    noiseControl: result.noiseControl.mode !== "" && typeof noise.focusOnVoice === "boolean"
      && (noise.mode !== "ambient" || integer(noise.ambientLevel, 1, 20)),
    equalizer: Array.isArray(eq.bands) && eq.bands.length === (result.capabilities.tenBandEqualizer ? 10 : 5)
      && eq.bands.every(function(value) { return integer(value, result.capabilities.tenBandEqualizer ? 0 : -10, result.capabilities.tenBandEqualizer ? 12 : 10); })
      && integer(eq.preset, 0, 255) && (result.capabilities.tenBandEqualizer || integer(eq.clearBass, -10, 10)),
    autoPowerOff: integer(data.autoPowerOff, 0, 5),
    codec: result.codec !== "", firmware: result.firmware !== ""
  };
  ["dsee", "speakToChat", "adaptiveVolume"].forEach(function(key) { readings[key] = typeof data[key] === "boolean"; });
  Object.keys(readings).forEach(function(key) {
    if (!readings[key] && result.features[key].availability === "valid")
      result.features[key] = {availability: "unknown", error: "Invalid or incomplete device reading"};
  });
  return result;
}
function reconcile(previous, data) {
  var next = snapshot(data);
  var preference = {level: 10, focusOnVoice: false};
  if (previous && next.deviceKey && next.deviceKey === previous.deviceKey && previous.ambientPreference)
    preference = previous.ambientPreference;
  if (next.connected && next.features.noiseControl.availability === "valid" && next.noiseControl.mode === "ambient")
    preference = {level: next.noiseControl.ambientLevel, focusOnVoice: next.noiseControl.focusOnVoice};
  next.ambientPreference = preference;
  return next;
}
if (typeof module !== "undefined") module.exports = { snapshot: snapshot, reconcile: reconcile, escapeTooltip: escapeTooltip,
  powerOffModes: powerOffModes, firmwareSupportUrl: firmwareSupportUrl };
