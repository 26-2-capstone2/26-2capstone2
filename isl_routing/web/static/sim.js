// 3-1 시뮬레이터: 서버(/api/stream)에서 0.1초마다 오는 상태를 2D 지도 위에 그림 (흐름 0 패킷만)
const $ = id => document.getElementById(id);
const BL = '#0877BD', OR = '#F59322';
let grid = { src: null, dst: null, queueMax: 200, burstMinLen: 3 };
let view = null, topoInfo = null, hotspots = [], flows = [], snap = null, history = [], valHist = [];
let running = false, loading = false, paused = false, validating = false, status = 'idle', selected = null;
const LV_C = { base: '#9CB3C2', high: BL, severe: OR };
const recentLoss = [];   // [{i, until}]
const fmt = n => (n === null || n === undefined) ? '-' : Number(n).toLocaleString('ko-KR');

// ---------- 위성망 지도 ----------
const cv = $('map');
function drawGrid() {
  const t = snap ? snap.t : 0, now = performance.now();
  drawMap(cv, view, {
    queues: snap && snap.queues.length === (view ? view.pairs.length : -1) ? snap.queues : null, queueMax: grid.queueMax,
    hot: new Set(hotspots.filter(([, a, b]) => t >= a && t <= b).map(h => h[0])),
    src: grid.src, dst: grid.dst, packets: snap ? snap.packets : null,
    losses: view ? recentLoss.filter(e => e.until > now).map(e => ({ i: e.i, a: (e.until - now) / 1200 })) : null,
    selected: selected && view ? selected[0] * view.sats + selected[1] : null });
}
cv.addEventListener('click', ev => { const i = mapPick(cv, view, ev); if (i == null) return;
  selected = [Math.floor(i / view.sats), i % view.sats]; drawGrid(); if (window.selectSat) selectSat(selected); });
window.addEventListener('resize', drawGrid);
EARTH.onload = drawGrid;

// 위 정보 띠, 대기 카드 (망 구조와 실행 조건 요약: /api/topology)
function showInfo(v) {
  topoInfo = v; const I = v.info;
  if (!snap) { view = v; grid.src = null; grid.dst = v.info.dst; }   // 대기 중: 끝점만 (출발은 시드로 정해짐)
  $('mapEn').textContent = `${v.topology.toUpperCase()}   2D 지도 (한 순간의 배치, 위성 위치 고정)   라우팅 RL`;
  $('info').innerHTML = [['위성', `${I.numSats} (궤도면 ${v.planes} x ${v.sats})`], ['흐름 0 끝점', `(${I.dst[0]}, ${I.dst[1]})`],
    ['가장 먼 거리 D', `${I.maxFlowDelay} ms`], ['기한 상한', `${I.deadline} ms`], ['핫스팟 빈도', `6x6의 ${I.hotRatio}배`],
    ['링크 지연', I.delay], ['고를 수 있는 구조', '이리듐 6x11, 스타링크 20x20, 36x36, 72x22']].map(([k, x]) => `<div><span>${k}</span><b>${x}</b></div>`).join('');
  $('lgPolar').style.display = v.polar ? '' : 'none';
  $('nOther').textContent = I.numFlows - 1; $('nAll').textContent = I.numFlows;
  $('idleTbl').innerHTML = [['위성망', `${v.name} (위성 ${I.numSats}${v.polar ? ', 극지방' : ''}${!I.wrap[0] ? ', seam' : ''})`],
    ['우리 흐름', `흐름 0: 시드마다 무작위 위성 → 끝점 (${I.dst[0]}, ${I.dst[1]}), 초당 ${I.genRate}개`],
    ['다른 흐름', `다른 지상국 ${I.numFlows - 1}개 (짧은, 중간, 긴 경로), 화면에는 그리지 않음`],
    ['혼잡 단계', `${I.levelRatio} (base : high : severe), 핫스팟 빈도 6x6의 ${I.hotRatio}배`],
    ['학습', `${I.simTime}초 에피소드 ${I.trainEpisodes}번, ${I.evalEvery}번마다 검증`],
    ['신경망', `${history.length ? '이어서 학습' : '새로 시작'} (관측 ${I.obsDim}개)`]].map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('');
  drawGrid(); showOverlay();
}
async function loadTopo(name) {
  const v = await api('/api/topology' + (name ? '?topology=' + encodeURIComponent(name) : ''));
  if (v.error) { showErr(v.error); return; } showInfo(v);
}
const STEPS = [['설정 읽기', 'config_isl.py, config_rl.py + 바꾼 값'], ['위성망 만들기', '끝점, 기한, 흐름 거리 계산'],
  ['PyTorch, 신경망 불러오기', '처음 실행은 몇 초 걸림'], ['첫 에피소드 환경 만들기', '흐름 4개 뽑기, 지역 핫스팟 일정 (36 x 36은 약 40초)'], ['시뮬레이션 시작', '1 ms씩 진행, 0.1초마다 화면 갱신']];
function showOverlay(step) {
  $('idle').classList.toggle('on', status === 'idle' && !snap);
  $('loading').classList.toggle('on', status === 'loading');
  if (step != null) $('steps').innerHTML = STEPS.map(([a, b], k) => `<div class="${k < step ? 'done' : k === step ? 'now' : ''}"><i></i><span><b>${a}</b><small>${b}</small></span></div>`).join('');
}

// ---------- 타임라인, 그래프 ----------
function drawTimeline(tl) {
  const c = $('tl'), g = c.getContext('2d'); g.clearRect(0, 0, c.width, c.height); if (!tl) return;
  const isLoss = s => s >= 2 && s <= 5, burst = new Array(tl.length).fill(false);
  for (let i = 0; i < tl.length;) { if (!isLoss(tl[i])) { i++; continue; } let j = i; while (j < tl.length && isLoss(tl[j])) j++; if (j - i >= grid.burstMinLen) for (let k = i; k < j; k++) burst[k] = true; i = j; }
  const w = c.width / 120;
  tl.forEach((s, i) => { const l = isLoss(s); g.fillStyle = s === 0 ? '#EFEFEF' : l ? (burst[i] ? OR : '#F8C88E') : '#CFCFCF';
    g.fillRect(i * w, l ? 0 : 10, w - 2, l ? 26 : 6); });
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
function drawVal() {
  // 검증 곡선: 단계별 선, 가로축은 검증한 시점의 에피소드 번호
  const c = $('c3'), g = c.getContext('2d'), W = c.width, H = c.height; g.clearRect(0, 0, W, H);
  const levels = [...new Set(valHist.map(r => r.level))];
  $('valLegend').innerHTML = levels.map(lv => `<span style="color:${LV_C[lv]}">● ${lv}</span>`).join(' ');
  if (!valHist.length) { g.fillStyle = '#999'; g.textAlign = 'center'; g.font = '11px sans-serif'; g.fillText('첫 검증이 끝나면 표시됩니다', W / 2, H / 2); return; }
  const maxEp = Math.max(...valHist.map(r => r.episode)), X = e => 36 + (maxEp <= 1 ? 0 : (e - 1) / (maxEp - 1)) * (W - 46), Y = v => 10 + (100 - v) / 100 * (H - 30);
  g.strokeStyle = '#EEE'; g.fillStyle = '#999'; g.font = '10px monospace'; g.textAlign = 'right';
  for (let k = 0; k <= 2; k++) { const y = 10 + k * (H - 30) / 2; g.beginPath(); g.moveTo(32, y); g.lineTo(W, y); g.stroke(); g.fillText(100 - k * 50, 28, y + 4); }
  for (const lv of levels) { const rows = valHist.filter(r => r.level === lv); g.strokeStyle = g.fillStyle = LV_C[lv] || BL; g.lineWidth = 2; g.beginPath();
    rows.forEach((r, i) => i ? g.lineTo(X(r.episode), Y(r.onTimeRate)) : g.moveTo(X(r.episode), Y(r.onTimeRate))); g.stroke();
    rows.forEach(r => { g.beginPath(); g.arc(X(r.episode), Y(r.onTimeRate), 2.5, 0, 7); g.fill(); }); }
  g.fillStyle = '#999'; g.font = '10px monospace'; g.textAlign = 'center'; g.fillText(maxEp, X(maxEp), H - 4);
}
function drawCharts() { drawChart('c1', 'onTimeRate', 100, BL, '%'); drawChart('c2', 'burstCount', 0, OR, ''); drawVal(); }

// ---------- 숫자 ----------
function showSnap(s) {
  snap = s; const st = s.stats;
  $('sOn').textContent = st.onTimeRate + '%'; $('sLoss').textContent = st.lossRate + '%'; $('sMax').textContent = st.maxConsecLoss; $('sBurst').textContent = st.burstCount;
  $('sAll').textContent = st.allOnTimeRate + '%'; $('sCnt').textContent = `${fmt(st.generated)} / ${fmt(st.onTime)} / ${fmt(st.lost)} / ${fmt(st.inflight)}`;
  $('cT').textContent = `${fmt(s.t)} / ${fmt(s.simTime)} ms`; $('prog').style.width = Math.min(100, s.t / s.simTime * 100) + '%';
  const L = s.learn; $('lEps').textContent = L.epsilon; $('lBuf').textContent = `${fmt(L.buffer)} / ${fmt(L.bufferSize)}`; $('lUpd').textContent = fmt(L.updates); $('lLoss').textContent = L.loss ?? '-';
  const items = [['홉 (링크 지연)', L.rewardHop, '#9CB3C2'], ['도착, 단발 손실', L.rewardOutcome, BL], ['연속 손실 추가분 (시작 벌점 포함)', L.rewardBurst, OR]];
  const mx = Math.max(1, ...items.map(i => Math.abs(i[1])));
  $('bars').innerHTML = items.map(([k, v, c]) => `<div><span>${k}</span><i style="width:${Math.abs(v) / mx * 100}%;background:${c}"></i><span class="mono">${v > 0 ? '+' : ''}${fmt(v)}</span></div>`).join('');
  drawTimeline(s.timeline); drawGrid(); showOverlay();
}
function showState(state) {
  if (!state) return;
  status = state.status;
  running = ['running', 'loading', 'validating'].includes(status);
  validating = status === 'validating';
  loading = status === 'loading';
  if (state.error) showErr('실행 중 오류: ' + state.error);
  $('cEp').textContent = `${String(state.episode || 0).padStart(3, '0')} / ${String(state.totalEpisodes || 0).padStart(3, '0')}`;
  const f0 = flows[0];
  $('epInfo').textContent = `EPISODE ${String(state.episode || 0).padStart(3, '0')}  ${state.levelNow || ''}  시드 ${state.seed ?? '-'}` +
    (f0 ? `   흐름 0: (${f0[0].join(', ')}) → (${f0[1].join(', ')}), 기한 ${grid.deadline} ms` : '') + (validating ? '  (검증 중)' : '');
  $('sTopo').disabled = running;
  showOverlay(state.loadStep); setPlayIcon(state.prep);
}
function setPlayIcon(prep) {
  const playing = running && !paused;
  $('playIcon').innerHTML = playing ? '<rect x="5" y="3" width="4" height="16"/><rect x="13" y="3" width="4" height="16"/>' : '<path d="M6 3 L19 11 L6 19 Z"/>';
  $('cState').textContent = !running ? '대기' : loading ? '준비 중' : paused ? '멈춤' : validating ? '검증 중 (ε 0)' : prep ? '다음 에피소드 준비 중' : '실행 중';
  $('cState').style.color = loading || prep ? BL : '';
  $('bPlay').setAttribute('aria-label', playing ? '멈춤' : '재생');
}
function addEvent(e) {
  if (e.pos && view) recentLoss.push({ i: e.pos[0] * view.sats + e.pos[1], until: performance.now() + 1200 });
  while (recentLoss.length > 80) recentLoss.shift();
  const d = document.createElement('div'); d.className = 'ev';
  d.innerHTML = `<span class="mono sub">에피소드 ${e.episode}  t = ${fmt(e.t)} ms</span><span class="${e.cls}">${e.kind}</span><span>${e.text}</span>`;
  const list = $('evlist'); list.prepend(d); while (list.children.length > 80) list.lastChild.remove();
}
function showErr(m) { $('err').style.display = m ? 'block' : 'none'; $('err').textContent = m || ''; }
function startEpisode(d) {
  view = d.map; grid = d.grid; hotspots = d.hotspots; flows = d.flows || [];
  $('qmax').textContent = grid.queueMax; $('bmin').textContent = grid.burstMinLen;
  if (!selected) selected = grid.src;
}

// ---------- 서버 연결 ----------
function connect() {
  const es = new EventSource('/api/stream');
  es.onmessage = m => { const d = JSON.parse(m.data);
    if (d.type === 'hello') { history = d.history || []; valHist = d.val || []; (d.events || []).forEach(addEvent); drawCharts(); $('sSpeed').value = d.speed || 'normal';
      if (d.start && d.start.map && d.state.status !== 'idle') startEpisode(d.start); showState(d.state); drawGrid(); }
    else if (d.type === 'episode_start') { startEpisode(d); showState(d.state); drawGrid(); }
    else if (d.type === 'snap') { paused = d.paused; setPlayIcon(); showSnap(d); if (window.showQ) showQ(d); }
    else if (d.type === 'event') addEvent(d.event);
    else if (d.type === 'episode_end') { history.push(d.row); drawCharts(); showState(d.state); }
    else if (d.type === 'val') { valHist.push(d.row); drawVal(); }
    else if (d.type === 'state') showState(d.state);
    else if (d.type === 'reset') { history = []; valHist = []; snap = null; hotspots = []; flows = []; $('evlist').innerHTML = '';
      ['sOn', 'sLoss', 'sMax', 'sBurst', 'sCnt', 'sAll', 'lEps', 'lBuf', 'lUpd', 'lLoss'].forEach(k => $(k).textContent = '-'); $('bars').innerHTML = ''; $('prog').style.width = 0; drawCharts(); drawTimeline(null); loadTopo(); }
    else if (d.type === 'error') showErr('실행 중 오류: ' + d.message);
  };
  es.onerror = () => { $('cState').textContent = '서버 연결 끊김 (다시 연결 중)'; };
}
const opts = () => ({ mode: $('sMode').value, level: $('sLevel').value });
async function start(mode) {
  showErr('');
  if (mode) $('sMode').value = mode;
  paused = false; await api('/api/control', { action: 'start', ...opts() }); running = true; setPlayIcon();
}
$('bPlay').onclick = async () => {
  if (running && !paused) { paused = true; await api('/api/control', { action: 'pause' }); setPlayIcon(); }
  else start();
};
$('bGo').onclick = () => start('train');
$('bEval').onclick = () => start('eval');
$('bCancel').onclick = () => api('/api/control', { action: 'stop' });
$('bStep').onclick = () => api('/api/control', { action: 'step', ...opts() });
$('bReset').onclick = async () => {
  if (running) { await api('/api/control', { action: 'stop' }); await new Promise(r => setTimeout(r, 600)); }
  const r = await api('/api/control', { action: 'reset' }); if (r.result === 'busy') alert('아직 멈추는 중입니다. 잠시 후 다시 눌러 주세요.');
};
$('sSpeed').onchange = () => api('/api/control', { action: 'speed', speed: $('sSpeed').value });
// 망 구조 바꾸기: 저장된 설정에 망 구조만 바꿔 저장하고, 신경망과 기록을 처음으로 (실행 중에는 못 바꿈)
$('sTopo').onchange = async () => {
  const d = await api('/api/settings'), o = d.saved || {};
  o.topology = $('sTopo').value;
  const r = await api('/api/settings', { overrides: o });
  if (!r.ok) { showErr('저장 안 됨: ' + r.error); return; }
  selected = null; snap = null; view = null; drawGrid();
  await api('/api/control', { action: 'reset' });
};
(async () => {
  const d = await api('/api/settings'), f = d.fields.find(x => x.key === 'topology');
  $('sTopo').innerHTML = f.options.map(o => `<option value="${o.value}" ${o.value === f.value ? 'selected' : ''}>${o.label}</option>`).join('');
  await loadTopo();
})();
setInterval(() => { if (recentLoss.some(e => e.until > performance.now())) drawGrid(); }, 100);
drawCharts(); connect();
