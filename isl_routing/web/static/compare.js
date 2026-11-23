// 라우팅 비교: 같은 시드로 돌린 DRA, RL 기록(web/compare.py)을 같은 시각으로 나란히 재생
const $ = id => document.getElementById(id);
const ROUTES = ['DRA', 'RL'], LOSS_NAME = { 2: '늦게 도착', 3: '가는 중 기한 초과', 4: '큐 넘침', 5: 'TTL 만료' };
const f1 = x => x == null ? '-' : Number.isInteger(+x) ? String(+x) : (+x).toFixed(1);   // 정수(횟수, 개수)는 소수점 없이
let D = null, t = 0, playing = false, last = 0;

function hiDPI(c) {
  if (!c.dataset.w) { c.dataset.w = c.getAttribute('width') || c.clientWidth; c.dataset.h = c.getAttribute('height') || c.clientHeight; }
  const r = window.devicePixelRatio || 1, w = c.clientWidth || +c.dataset.w, h = Math.round(w * +c.dataset.h / +c.dataset.w);
  if (c.width !== Math.round(w * r)) { c.width = Math.round(w * r); c.height = Math.round(h * r); c.style.height = h + 'px'; }
  const g = c.getContext('2d'); g.setTransform(r, 0, 0, r, 0, 0); g.clearRect(0, 0, w, h); return [g, w, h];
}
function msg(text, err) { $('msg').textContent = text || ''; $('msg').className = err ? 'err' : ''; }

// ---------- 준비 ----------
(async () => {
  const s = await api('/api/settings'), topo = s.fields.find(f => f.key === 'topology');
  $('selTopo').innerHTML = topo.options.map(o => `<option value="${o.value}" ${o.value === 'iridium' ? 'selected' : ''}>${o.label}</option>`).join('');
  $('selSeed').innerHTML = Array.from({ length: 20 }, (_, i) => `<option>${i + 1}</option>`).join('');
  const ms = await api('/api/compare/models');
  preview();
  $('selTopo').onchange = preview;
  $('selModel').innerHTML = ms.map(m => `<option>${m.name}</option>`).join('') || '<option value="">(모델 없음)</option>';
})();

$('bGo').onclick = async () => {
  const body = { topology: $('selTopo').value, level: $('selLv').value, seed: +$('selSeed').value, model: $('selModel').value };
  if (!body.model) return msg('학습된 모델이 없습니다.', true);
  $('bGo').disabled = true; pause(); D = null; preview();
  msg(`DRA와 RL로 같은 시나리오를 돌리는 중입니다 (이리듐 약 1분, 큰 망은 몇 분). 같은 조건은 다음부터 바로 열립니다.`);
  try {
    const r = await api('/api/compare', body);
    if (r.error) { msg(r.error, true); return; }
    D = r; prepare(); msg(''); seek(0); play();
  } catch (e) { msg('불러오기 실패: ' + e, true); }
  finally { $('bGo').disabled = false; }
};

// 계산 전: 고른 망 모양만 그리고, 나머지 칸은 안내 문구
async function preview() {
  if (D) return;
  const v = await api('/api/topology?topology=' + encodeURIComponent($('selTopo').value));
  if (v.error || D) return;
  for (const k of ROUTES) { drawMap($('m' + k), v, {}); hiDPI($('t' + k)); $('s' + k).textContent = '시뮬레이션 이후 확인할 수 있습니다'; }
  $('sideEn').textContent = `SIDE BY SIDE   ${v.topology.toUpperCase()}   아직 계산 전`;
  const [g, W, H] = hiDPI($('cum')); g.fillStyle = '#999'; g.font = '13px sans-serif'; g.textAlign = 'center'; g.fillText('시뮬레이션 이후 확인할 수 있습니다', W / 2, H / 2);
}

function prepare() {
  const S = D.map.sats, n = D.routes.DRA.status.length;
  D.period = D.simTime / n;
  for (const k of ROUTES) {
    const r = D.routes[k];
    r.lostCum = []; let c = 0; for (const s of r.status) { if (s >= 2) c++; r.lostCum.push(c); }
    r.bursts = runs(r.status).filter(b => b.len >= D.burstMinLen);
  }
  const m = k => D.routes[k].metrics;
  for (const k of ROUTES) $('s' + k).textContent = `도착 ${f1(m(k).onTime)}%   연속 손실 ${m(k).burstCount}번   최대 ${m(k).maxConsec}개`;
  $('scrub').max = D.simTime;
  const f0 = D.flow0, pos = a => `(${a[0]}, ${a[1]})`;
  $('sideNote').textContent = `흐름 0: ${pos(f0.src)}에서 ${pos(f0.dst)}로, 기한 ${f0.deadline} ms. 두 지도는 같은 시각을 함께 보여 줍니다. 핫스팟(주황 링크)이 켜지면 그 링크의 큐가 차고, 그 길로 계속 보내면 연속 손실이 납니다. 금색 선은 가장 최근에 끝난 흐름 0 패킷이 지나간 길입니다 (빨간 선이면 그 패킷은 손실).`;
  renderMetrics(); renderEvents();
}
function runs(st) {   // 손실이 이어진 구간 [{start, len}]
  const out = []; let s = -1;
  st.forEach((v, i) => { if (v >= 2) { if (s < 0) s = i; } else if (s >= 0) { out.push({ start: s, len: i - s }); s = -1; } });
  if (s >= 0) out.push({ start: s, len: st.length - s });
  return out;
}

// ---------- 재생 ----------
function play() { if (!D) return; if (t >= D.simTime) t = 0; playing = true; $('bPlay').textContent = '❚❚'; last = performance.now(); requestAnimationFrame(tick); }
function pause() { playing = false; $('bPlay').textContent = '▶'; }
function seek(v) { if (!D) return; t = Math.max(0, Math.min(D.simTime, v)); draw(); }
function tick(now) {
  if (!playing) return;
  t += (now - last) * +$('speed').value; last = now;
  if (t >= D.simTime) { t = D.simTime; pause(); }
  draw();
  if (playing) requestAnimationFrame(tick);
}
$('bPlay').onclick = () => playing ? pause() : play();
$('scrub').oninput = e => { if (!D) { e.target.value = 0; return; } pause(); seek(+e.target.value); };
window.addEventListener('resize', () => D && draw());
EARTH.onload = () => D && draw();

function draw() {
  $('scrub').value = t;
  $('tNow').textContent = `${Math.round(t).toLocaleString()} / ${D.simTime.toLocaleString()} ms`;
  $('sideEn').textContent = `SIDE BY SIDE   ${D.topology.toUpperCase()}, ${D.level}, 평가 시드 ${D.seed}   t = ${Math.round(t).toLocaleString()} ms`;
  const hot = new Set(D.hotspots.filter(h => h[1] <= t && t < h[2]).map(h => h[0]));
  for (const k of ROUTES) { drawRoute(k, hot); drawStrip(k); }
  drawCum();
}
function drawRoute(k, hot) {
  const r = D.routes[k], fr = r.frames[Math.max(0, Math.min(r.frames.length - 1, Math.floor(t / D.frame) - 1))] || [0, [], []];
  const q = new Array(D.map.pairs.length).fill(0); for (const [i, v] of fr[1]) q[i] = v;
  // 가장 최근에 끝난 흐름 0 패킷의 경로
  let path = null, lost = false;
  for (let i = Math.min(r.status.length - 1, Math.floor(t / D.period)); i >= 0; i--) if (r.end[i] <= t && r.paths[i].length > 1) { path = r.paths[i]; lost = r.status[i] >= 2; break; }
  const losses = [];
  r.status.forEach((s, i) => { if (s >= 2 && r.end[i] <= t && t - r.end[i] < 400 && r.lossPos[i] != null) losses.push({ i: r.lossPos[i], a: 1 - (t - r.end[i]) / 400 }); });
  drawMap($('m' + k), D.map, { queues: q, queueMax: D.queueMax, hot, packets: fr[2], losses: losses.slice(-12), src: D.flow0.src, dst: D.flow0.dst, path, pathColor: lost ? '#FF6B6B' : '#FFD54A', hotColor: 'rgba(255,138,31,0.45)' });
}
function drawStrip(k) {
  const r = D.routes[k], [g, W, H] = hiDPI($('t' + k)), n = 120, hi = Math.min(r.status.length, Math.floor(t / D.period) + 1), lo = Math.max(0, hi - n), cw = W / n;
  for (let i = lo; i < hi; i++) {
    const done = r.end[i] <= t;
    g.fillStyle = !done ? '#EEF1F3' : r.status[i] >= 2 ? '#F59322' : '#D8E3EA';
    g.fillRect((i - lo) * cw, 0, Math.max(1, cw - 1), H);
  }
}
function drawCum() {
  const [g, W, H] = hiDPI($('cum')), px = 46, py = 12, pw = W - px - 16, ph = H - py - 28;
  const top = Math.max(10, ...ROUTES.map(k => D.routes[k].lostCum.at(-1))) * 1.08, X = v => px + v / D.simTime * pw, Y = v => py + (top - v) / top * ph;
  g.font = '10px sans-serif'; g.fillStyle = '#999'; g.textAlign = 'right';
  for (const f of [0, 0.5, 1]) { g.strokeStyle = '#EEE'; g.beginPath(); g.moveTo(px, Y(top * f)); g.lineTo(px + pw, Y(top * f)); g.stroke(); g.fillText(Math.round(top * f), px - 8, Y(top * f) + 4); }
  g.textAlign = 'center'; for (let s = 0; s <= D.simTime; s += 2000) g.fillText(`${s / 1000} s`, X(s), H - 8);
  ROUTES.forEach((k, j) => {
    const r = D.routes[k], col = k === 'RL' ? '#0877BD' : '#8FA8B8';
    for (const b of r.bursts) { g.fillStyle = k === 'RL' ? 'rgba(8,119,189,0.10)' : 'rgba(143,168,184,0.16)'; g.fillRect(X(r.gen[b.start]), py + ph - (j + 1) * 7, Math.max(2, X(r.gen[b.start + b.len - 1]) - X(r.gen[b.start])), 6); }
    for (const [from, to, a] of [[0, t, 1], [t, D.simTime, 0.25]]) {
      g.strokeStyle = col; g.globalAlpha = a; g.lineWidth = 2; g.beginPath(); let on = false;
      r.gen.forEach((gt, i) => { if (gt < from || gt > to) return; on ? g.lineTo(X(gt), Y(r.lostCum[i])) : g.moveTo(X(gt), Y(r.lostCum[i])); on = true; });
      g.stroke(); g.globalAlpha = 1;
    }
    const i = Math.min(r.gen.length - 1, Math.floor(t / D.period));
    g.fillStyle = col; g.textAlign = 'left'; g.font = '500 11px sans-serif'; g.fillText(`${k} ${r.lostCum[i]}`, X(t) + 6, Y(r.lostCum[i]) - 4);
  });
  g.strokeStyle = '#F59322'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X(t), py); g.lineTo(X(t), py + ph); g.stroke(); g.lineWidth = 1;
}

// ---------- 지표, 사건 ----------
function renderMetrics() {
  const a = D.routes.DRA.metrics, b = D.routes.RL.metrics;
  $('metEn').textContent = `METRICS   흐름 0 기준, ${D.topology}, ${D.level}, 평가 시드 ${D.seed} 하나 (평균은 결과 분석에서)`;
  const rows = [['기한 내 도착률', 'onTime', '%', 1], ['1분당 연속 손실', 'burstPerMin', '', -1], ['연속 손실 횟수', 'burstCount', '번', -1], ['최대 연속 손실', 'maxConsec', '개', -1],
    ['연속 손실에 속한 손실', 'burstShare', '%', -1], ['평균 지연 (도착 패킷)', 'latency', ' ms', 0], ['평균 홉 수 (도착 패킷)', 'hops', '', 0]];
  $('metTbl').innerHTML = `<table class="t"><tr><th>지표</th><th>DRA</th><th>RL</th><th>차이</th></tr>` + rows.map(([n, key, u, better]) => {
    const x = a[key], y = b[key], d = x == null || y == null ? null : y - x;
    const cls = d == null || better === 0 || Math.abs(d) < 1e-9 ? '' : d * better > 0 ? 'good' : 'bad';
    const ds = d == null ? '-' : key === 'maxConsec' && x ? `${d <= 0 ? '−' : '+'}${f1(Math.abs(d / x * 100))}%` : `${d >= 0 ? '+' : '−'}${f1(Math.abs(d))}${u === '%' ? '%p' : u}`;
    return `<tr><td>${n}</td><td>${f1(x)}${u}</td><td class="rl">${f1(y)}${u}</td><td class="${cls}">${ds}</td></tr>`;
  }).join('') + '</table>';
  const lines = [];
  if (b.maxConsec < a.maxConsec && b.burstCount > a.burstCount) lines.push('RL은 긴 연속 손실을 짧은 몇 개로 쪼갭니다. 그래서 최대 연속 손실은 줄지만, 3개 이상 손실 횟수는 DRA보다 많아질 수 있습니다 (쪼개짐).');
  else if (b.maxConsec < a.maxConsec) lines.push('RL이 연속 손실을 더 짧게 끊었습니다.');
  else if (b.maxConsec > a.maxConsec) lines.push('이 시드에서는 RL의 최대 연속 손실이 더 깁니다. 아래 사건 목록에서 어느 시각인지 확인하세요.');
  lines.push(b.onTime >= a.onTime ? `도착률은 RL이 ${f1(b.onTime - a.onTime)}%p 높습니다.` : `도착률은 DRA가 ${f1(a.onTime - b.onTime)}%p 높습니다.`);
  $('metRead').innerHTML = `<h3>읽는 법</h3>${lines.map(l => `<p>${l}</p>`).join('')}<p style="color:var(--sub)">한 시드 결과라 우연이 섞여 있습니다. 평가 시드 20개 평균은 결과 분석 화면에서 봅니다.</p>`;
}
function renderEvents() {
  const S = D.map.sats, ev = [];
  for (const k of ROUTES) {
    const r = D.routes[k], o = D.routes[k === 'RL' ? 'DRA' : 'RL'];
    for (const b of r.bursts) {
      const ids = Array.from({ length: b.len }, (_, j) => b.start + j), cnt = {};
      ids.forEach(i => cnt[r.status[i]] = (cnt[r.status[i]] || 0) + 1);
      const main = Object.entries(cnt).sort((x, y) => y[1] - x[1])[0][0], sat = r.lossPos[b.start];
      const ost = ids.map(i => o.status[i]), oLost = ost.filter(s => s >= 2).length, oRun = Math.max(0, ...runs(ost).map(x => x.len));
      const other = oLost === 0 ? `${k === 'RL' ? 'DRA' : 'RL'}: 모두 도착` : oRun >= D.burstMinLen ? `${k === 'RL' ? 'DRA' : 'RL'}: 연속 손실 (최대 ${oRun}개)` : `${k === 'RL' ? 'DRA' : 'RL'}: 단발 손실 ${oLost}개`;
      ev.push({ t0: r.gen[b.start], k, len: b.len, cause: LOSS_NAME[main] + (sat != null ? ` (${Math.floor(sat / S)}, ${sat % S})` : ''), other, good: oLost === 0 });
    }
  }
  ev.sort((x, y) => x.t0 - y.t0);
  $('evTbl').innerHTML = ev.length ? `<table class="t"><tr><th>시작 시각</th><th>라우팅</th><th>길이</th><th>원인 (첫 손실 위치)</th><th>같은 패킷, 다른 라우팅</th><th></th></tr>` +
    ev.map(e => `<tr><td>${Math.round(e.t0).toLocaleString()} ms</td><td class="${e.k === 'RL' ? 'rl' : 'dra'}">${e.k}</td><td>${e.len}개</td><td>${e.cause}</td><td class="${e.good ? 'good' : ''}">${e.other}</td><td><a class="jump" data-t="${e.t0}">재생 ▶</a></td></tr>`).join('') + '</table>'
    : '<div class="empty">이 시드에서는 두 라우팅 모두 연속 손실이 없습니다.</div>';
  document.querySelectorAll('a.jump').forEach(a => a.onclick = () => { seek(+a.dataset.t - 2000); $('mDRA').scrollIntoView({ behavior: 'smooth', block: 'center' }); play(); });
}
