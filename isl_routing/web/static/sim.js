// 3-1 시뮬레이터: 서버(/api/stream)에서 0.1초마다 오는 상태를 그림
const $ = id => document.getElementById(id);
const BL = '#0877BD', OR = '#F59322', DK = '#183D4E';
let grid = { planes: 6, sats: 6, src: [0, 0], dst: [5, 5], queueMax: 200, burstMinLen: 3 };
let links = [], hotspots = [], snap = null, history = [], running = false, loading = false, paused = false, selected = null;
const recentLoss = [];   // [{p, s, until}]

// ---------- 위성망 ----------
const cv = $('grid'), ctx = cv.getContext('2d');
(function hiDPI() { const r = window.devicePixelRatio || 1; cv.width = 640 * r; cv.height = 640 * r; ctx.scale(r, r); })();
const geo = () => { const G0 = 44, GS = (640 - 2 * G0) / Math.max(grid.planes - 1, grid.sats - 1); return { G0, GS, X: p => G0 + p * GS, Y: s => G0 + s * GS }; };
const STEP = { 1: [0, -1], 2: [0, 1], 3: [-1, 0], 4: [1, 0] };
function mix(f) { const a = [0xC4, 0xD6, 0xE4], b = [0x08, 0x77, 0xBD]; return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * f)).join(',')})`; }

function drawGrid() {
  const { GS, X, Y } = geo();
  ctx.clearRect(0, 0, 640, 640);
  const off = d => (d === 2 || d === 4) ? 4 : -4;            // 방향마다 한쪽으로 살짝 띄움
  const seg = (l, k) => { const [dp, ds] = STEP[l.dir]; const x1 = X(l.p), y1 = Y(l.s), x2 = X(l.p + dp), y2 = Y(l.s + ds); const o = off(l.dir);
    const ox = dp === 0 ? o : 0, oy = ds === 0 ? o : 0, m = 14 / GS;
    return [x1 + (x2 - x1) * m + ox, y1 + (y2 - y1) * m + oy, x2 - (x2 - x1) * m + ox, y2 - (y2 - y1) * m + oy]; };
  // 핫스팟 (아래에 깔기)
  for (const h of hotspots) { const l = links.find(z => z.p === h.p && z.s === h.s && z.dir === h.dir); if (!l) continue; const [a, b, c, d] = seg(l);
    ctx.strokeStyle = OR; ctx.globalAlpha = 0.45; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(c, d); ctx.stroke(); ctx.globalAlpha = 1; }
  // 링크 큐
  links.forEach((l, k) => { const q = snap ? snap.queues[k] : 0; const f = Math.min(1, q / grid.queueMax); const [a, b, c, d] = seg(l);
    ctx.strokeStyle = mix(f); ctx.lineWidth = 1.5 + f * 3.5; ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(c, d); ctx.stroke(); });
  // 위성
  for (let p = 0; p < grid.planes; p++) for (let s = 0; s < grid.sats; s++) {
    const src = p === grid.src[0] && s === grid.src[1], dst = p === grid.dst[0] && s === grid.dst[1];
    ctx.fillStyle = src ? '#333' : '#fff'; ctx.strokeStyle = '#555'; ctx.lineWidth = dst ? 2.5 : 1.2;
    const r = src || dst ? 11 : 9; ctx.beginPath(); ctx.roundRect(X(p) - r, Y(s) - r, 2 * r, 2 * r, 3); ctx.fill(); ctx.stroke(); }
  // 좌표
  ctx.fillStyle = '#999'; ctx.font = '11px monospace'; ctx.textAlign = 'center';
  for (let i = 0; i < grid.planes; i++) ctx.fillText(i, X(i), 632);
  ctx.textAlign = 'left'; for (let i = 0; i < grid.sats; i++) ctx.fillText(i, 8, Y(i) + 4);
  // 패킷
  if (snap) { ctx.fillStyle = DK; snap.packets.forEach(([fp, fs, cp, cs], i) => { const j = ((i * 37) % 9 - 4) * 1.6, k = ((i * 53) % 9 - 4) * 1.6;
    const x = (X(fp) + X(cp)) / 2 + j, y = (Y(fs) + Y(cs)) / 2 + k; ctx.beginPath(); ctx.arc(x, y, 3.6, 0, 7); ctx.fill(); }); }
  // 손실 X (잠깐 보였다 사라짐)
  const now = performance.now(); ctx.strokeStyle = OR; ctx.lineWidth = 2.2;
  for (const e of recentLoss) if (e.until > now) { const x = X(e.p) + 12, y = Y(e.s) - 12; ctx.globalAlpha = (e.until - now) / 1200;
    ctx.beginPath(); ctx.moveTo(x - 5, y - 5); ctx.lineTo(x + 5, y + 5); ctx.moveTo(x + 5, y - 5); ctx.lineTo(x - 5, y + 5); ctx.stroke(); }
  ctx.globalAlpha = 1;
  if (selected) { ctx.strokeStyle = OR; ctx.setLineDash([4, 3]); ctx.lineWidth = 2; ctx.strokeRect(X(selected[0]) - 16, Y(selected[1]) - 16, 32, 32); ctx.setLineDash([]); }
}
cv.addEventListener('click', ev => { const r = cv.getBoundingClientRect(), { X, Y } = geo(); const x = ev.clientX - r.left, y = ev.clientY - r.top;
  let best = null, bd = 30; for (let p = 0; p < grid.planes; p++) for (let s = 0; s < grid.sats; s++) { const d = Math.hypot(X(p) - x, Y(s) - y); if (d < bd) { bd = d; best = [p, s]; } }
  selected = best; drawGrid(); if (best && window.selectSat) selectSat(best); });

// ---------- 타임라인, 그래프 ----------
function drawTimeline(tl) {
  const c = $('tl'), g = c.getContext('2d'); g.clearRect(0, 0, c.width, c.height); if (!tl) return;
  const isLoss = s => s >= 2 && s <= 5, burst = new Array(tl.length).fill(false);
  for (let i = 0; i < tl.length;) { if (!isLoss(tl[i])) { i++; continue; } let j = i; while (j < tl.length && isLoss(tl[j])) j++; if (j - i >= grid.burstMinLen) for (let k = i; k < j; k++) burst[k] = true; i = j; }
  const w = c.width / 120;
  tl.forEach((s, i) => { const l = isLoss(s); g.fillStyle = s === 0 ? '#EFEFEF' : l ? (burst[i] ? OR : '#F8C88E') : '#CFCFCF';
    g.fillRect(i * w, l ? 0 : 10, w - 1, l ? 26 : 6); });
}
function drawChart(id, key, max, color, unit) {
  const c = $(id), g = c.getContext('2d'), W = c.width, H = c.height; g.clearRect(0, 0, W, H);
  const vals = history.map(r => +r[key]); const top = max || Math.max(5, ...vals);
  g.strokeStyle = '#EEE'; g.fillStyle = '#999'; g.font = '10px monospace'; g.textAlign = 'right';
  if (!vals.length) { g.textAlign = 'center'; g.font = '11px sans-serif'; g.fillText('첫 에피소드가 끝나면 표시됩니다', W / 2, H / 2); return; }
  for (let k = 0; k <= 2; k++) { const y = 10 + k * (H - 30) / 2; g.beginPath(); g.moveTo(32, y); g.lineTo(W, y); g.stroke(); g.fillText(Math.round(top - k * top / 2), 28, y + 4); }
  const X = i => 36 + (vals.length === 1 ? 0 : i * (W - 46) / (vals.length - 1)), Y = v => 10 + (top - v) / top * (H - 30);
  g.strokeStyle = color; g.lineWidth = 2; g.beginPath(); vals.forEach((v, i) => i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v))); g.stroke();
  g.fillStyle = color; vals.forEach((v, i) => { g.beginPath(); g.arc(X(i), Y(v), i === vals.length - 1 ? 4 : 2.5, 0, 7); g.fill(); });
  g.textAlign = 'right'; g.font = '11px sans-serif'; g.fillText(vals[vals.length - 1] + unit, X(vals.length - 1) - 6, Y(vals[vals.length - 1]) - 8);
  g.fillStyle = '#999'; g.font = '10px monospace'; g.textAlign = 'center'; g.fillText('1', X(0), H - 4); if (vals.length > 1) g.fillText(vals.length, X(vals.length - 1), H - 4);
}
function drawCharts() { drawChart('c1', 'onTimeRate', 100, BL, '%'); drawChart('c2', 'burstCount', 0, OR, ''); }

// ---------- 숫자 ----------
const fmt = n => (n === null || n === undefined) ? '-' : Number(n).toLocaleString('ko-KR');
function showSnap(s) {
  snap = s; const st = s.stats;
  $('sOn').textContent = st.onTimeRate + '%'; $('sLoss').textContent = st.lossRate + '%'; $('sMax').textContent = st.maxConsecLoss; $('sBurst').textContent = st.burstCount;
  $('sGen').textContent = fmt(st.generated); $('sArr').textContent = fmt(st.onTime); $('sLost').textContent = fmt(st.lost); $('sIn').textContent = fmt(st.inflight);
  $('cT').textContent = `${fmt(s.t)} / ${fmt(s.simTime)} ms`; $('prog').style.width = Math.min(100, s.t / s.simTime * 100) + '%';
  const L = s.learn; $('lEps').textContent = L.epsilon; $('lBuf').textContent = `${fmt(L.buffer)} / ${fmt(L.bufferSize)}`; $('lUpd').textContent = fmt(L.updates); $('lLoss').textContent = L.loss ?? '-';
  const items = [['홉 벌점', L.rewardHop, '#9CB3C2'], ['결과 (+1 / -1)', L.rewardOutcome, BL], ['연속 손실 벌점', L.rewardBurst, OR]];
  const mx = Math.max(1, ...items.map(i => Math.abs(i[1])));
  $('bars').innerHTML = items.map(([k, v, c]) => `<div><span>${k}</span><i style="width:${Math.abs(v) / mx * 100}%;background:${c}"></i><span class="mono">${v > 0 ? '+' : ''}${fmt(v)}</span></div>`).join('');
  drawTimeline(s.timeline); drawGrid();
}
function showState(state) {
  if (!state) return;
  running = state.status === 'running' || state.status === 'loading';
  loading = state.status === 'loading';
  if (state.error) { $('err').style.display = 'block'; $('err').textContent = '실행 중 오류: ' + state.error; }
  $('cEp').textContent = `${String(state.episode || 0).padStart(3, '0')} / ${String(state.totalEpisodes || 0).padStart(3, '0')}`;
  $('epInfo').textContent = `EPISODE ${String(state.episode || 0).padStart(3, '0')}  ${state.levelNow || ''}  시드 ${state.seed ?? '-'}`;
  setPlayIcon();
}
function setPlayIcon() {
  const playing = running && !paused;
  $('playIcon').innerHTML = playing ? '<rect x="5" y="3" width="4" height="16"/><rect x="13" y="3" width="4" height="16"/>' : '<path d="M6 3 L19 11 L6 19 Z"/>';
  $('cState').textContent = !running ? '대기' : loading ? '준비 중 (신경망 불러오는 중)' : paused ? '멈춤' : '실행 중';
  $('bPlay').setAttribute('aria-label', playing ? '멈춤' : '재생');
}
function addEvent(e) {
  if (e.pos) recentLoss.push({ p: e.pos[0], s: e.pos[1], until: performance.now() + 1200 });
  while (recentLoss.length > 80) recentLoss.shift();
  const d = document.createElement('div'); d.className = 'ev';
  d.innerHTML = `<span class="mono sub">에피소드 ${e.episode}  t = ${fmt(e.t)} ms</span><span></span><span class="${e.cls}">${e.kind}</span><span>${e.text}</span>`;
  const list = $('evlist'); list.prepend(d); while (list.children.length > 80) list.lastChild.remove();
}

// ---------- 서버 연결 ----------
function connect() {
  const es = new EventSource('/api/stream');
  es.onmessage = m => { const d = JSON.parse(m.data);
    if (d.type === 'hello') { history = d.history || []; (d.events || []).forEach(addEvent); drawCharts(); $('sSpeed').value = d.speed || 'normal';
      if (d.start) { grid = d.start.grid; links = d.start.links; hotspots = d.start.hotspots; } showState(d.state); drawGrid(); }
    else if (d.type === 'episode_start') { grid = d.grid; links = d.links; hotspots = d.hotspots; $('gridSize').textContent = `${grid.planes} x ${grid.sats}`;
      $('qmax').textContent = grid.queueMax; $('bmin').textContent = grid.burstMinLen; showState(d.state); drawGrid(); }
    else if (d.type === 'snap') { paused = d.paused; setPlayIcon(); showSnap(d); if (window.showQ) showQ(d); }
    else if (d.type === 'event') addEvent(d.event);
    else if (d.type === 'episode_end') { history.push(d.row); drawCharts(); showState(d.state); }
    else if (d.type === 'state') { showState(d.state); }
    else if (d.type === 'reset') { history = []; snap = null; $('evlist').innerHTML = ''; drawCharts(); drawTimeline(null); drawGrid(); }
    else if (d.type === 'error') { $('err').style.display = 'block'; $('err').textContent = '실행 중 오류: ' + d.message; }
  };
  es.onerror = () => { $('cState').textContent = '서버 연결 끊김 (다시 연결 중)'; };
}
const opts = () => ({ mode: $('sMode').value, level: $('sLevel').value });
$('bPlay').onclick = async () => {
  $('err').style.display = 'none';
  if (running && !paused) { paused = true; await api('/api/control', { action: 'pause' }); }
  else { paused = false; await api('/api/control', { action: 'start', ...opts() }); running = true; }
  setPlayIcon();
};
$('bStep').onclick = () => api('/api/control', { action: 'step', ...opts() });
$('bReset').onclick = async () => {
  if (running) { await api('/api/control', { action: 'stop' }); await new Promise(r => setTimeout(r, 600)); }
  const r = await api('/api/control', { action: 'reset' }); if (r.result === 'busy') alert('아직 멈추는 중입니다. 잠시 후 다시 눌러 주세요.');
};
$('sSpeed').onchange = () => api('/api/control', { action: 'speed', speed: $('sSpeed').value });
setInterval(() => { if (recentLoss.some(e => e.until > performance.now())) drawGrid(); }, 100);
drawCharts(); drawGrid(); connect();
