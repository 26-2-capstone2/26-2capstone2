// 3-2: 선택한 위성의 방향별 Q값, 선택 확률, 관측, 정책 지도
const DIRS = ['상', '하', '좌', '우'], ARROW = ['↑', '↓', '←', '→'];
const CELL = [1, 7, 3, 5];   // 3x3 십자에서 상, 하, 좌, 우 칸 위치
let policy = [], lastDec = null;

function selectSat(ps) { api('/api/control', { action: 'select', p: ps[0], s: ps[1] }); $('qSat').textContent = `(${ps[0]}, ${ps[1]})`; lastDec = null;
  $('qRecent').innerHTML = '<div class="sub" style="padding:8px 12px">이 위성을 지나는 패킷을 기다리는 중입니다.</div>'; render(); }

function cross(id, vals, dec, fmtv) {
  const cells = Array(9).fill('<div></div>');
  cells[4] = `<div class="c mid">위성<br>${dec ? `(${dec.sat[0]}, ${dec.sat[1]})` : '-'}</div>`;
  for (let d = 0; d < 4; d++) {
    const blocked = dec && !dec.mask[d], pick = dec && dec.action === d;
    const v = !dec ? '-' : blocked ? '막힘' : fmtv(vals[d]);
    const sub = blocked ? dec.why[d] : `${ARROW[d]} ${DIRS[d]}`;
    cells[CELL[d]] = `<div class="c ${blocked ? 'no' : ''} ${pick ? 'pick' : ''}">${sub}<b>${v}</b></div>`;
  }
  $(id).innerHTML = cells.join('');
}

const OBS_ROWS = [['큐 길이 ÷ 200', 0], ['이웃 부하 ÷ 200', 4], ['큐 증가 속도', 8], ['최근 큐 넘침', 12], ['링크 유무', 16]];
function obsTable(o) {
  let h = '<tr><th></th>' + DIRS.map(d => `<th style="text-align:right">${d}</th>`).join('') + '</tr>';
  for (const [name, k] of OBS_ROWS) h += `<tr><th>${name}</th>` + [0, 1, 2, 3].map(d => `<td>${o ? o[k + d].toFixed(2) : '-'}</td>`).join('') + '</tr>';
  h += `<tr><th>남은 거리 p, s ÷ 5</th><td colspan="2">${o ? o[20].toFixed(2) : '-'}</td><td colspan="2">${o ? o[21].toFixed(2) : '-'}</td></tr>`;
  h += `<tr><th>남은 기한 ÷ 70</th><td colspan="4">${o ? o[22].toFixed(2) : '-'}</td></tr>`;
  h += `<tr><th>남은 TTL ÷ 20</th><td colspan="4">${o ? o[23].toFixed(2) : '-'}</td></tr>`;
  $('obsTbl').innerHTML = h;
}

function drawPolicy() {
  const c = $('pmap'), g = c.getContext('2d'), r = window.devicePixelRatio || 1;
  if (c.width !== 300 * r) { c.width = 300 * r; c.height = 300 * r; }
  g.setTransform(r, 0, 0, r, 0, 0); g.clearRect(0, 0, 300, 300);
  const n = Math.max(grid.planes, grid.sats), GS = 260 / Math.max(n - 1, 1), X = p => 20 + p * GS, Y = s => 20 + s * GS;
  const map = {}; policy.forEach(([p, s, d]) => map[p + ',' + s] = d);
  for (let p = 0; p < grid.planes; p++) for (let s = 0; s < grid.sats; s++) {
    const src = p === grid.src[0] && s === grid.src[1], dst = p === grid.dst[0] && s === grid.dst[1];
    g.fillStyle = (src || dst) ? '#333' : '#BBB'; g.beginPath(); g.arc(X(p), Y(s), (src || dst) ? 5 : 3, 0, 7); g.fill();
    const d = map[p + ',' + s]; if (!d || dst) continue;
    const [dp, ds] = STEP[d], L = GS * 0.38, x2 = X(p) + dp * L, y2 = Y(s) + ds * L, a = Math.atan2(ds, dp);
    g.strokeStyle = g.fillStyle = BL; g.lineWidth = 2; g.beginPath(); g.moveTo(X(p), Y(s)); g.lineTo(x2, y2); g.stroke();
    g.beginPath(); g.moveTo(x2 + 5 * Math.cos(a), y2 + 5 * Math.sin(a));
    g.lineTo(x2 + 5 * Math.cos(a + 2.4), y2 + 5 * Math.sin(a + 2.4)); g.lineTo(x2 + 5 * Math.cos(a - 2.4), y2 + 5 * Math.sin(a - 2.4)); g.fill();
  }
  if (selected) { g.strokeStyle = OR; g.lineWidth = 2; g.setLineDash([4, 3]); g.strokeRect(X(selected[0]) - 12, Y(selected[1]) - 12, 24, 24); g.setLineDash([]); }
  c.onclick = ev => { const b = c.getBoundingClientRect(); const p = Math.round((ev.clientX - b.left - 20) / GS), s = Math.round((ev.clientY - b.top - 20) / GS);
    if (p >= 0 && p < grid.planes && s >= 0 && s < grid.sats) { selected = [p, s]; drawGrid(); selectSat(selected); } };
}

function render() {
  const dec = lastDec;
  cross('qCross', dec && dec.qRaw, dec, v => v.toFixed(2));
  cross('pCross', dec && dec.prob, dec, v => v.toFixed(2));
  $('pNote').textContent = dec ? `ε = ${dec.eps}, 가능한 방향 n = ${dec.mask.reduce((a, b) => a + b, 0)}. ${dec.random ? '이번엔 탐험으로 무작위 방향을 골랐습니다.' : '이번엔 점수가 가장 높은 방향을 골랐습니다.'}`
    : 'ε-greedy: 최고 점수 1 - ε + ε/n, 나머지 ε/n, 막힘 0';
  obsTable(dec && dec.obs);
  $('obsMeta').textContent = dec ? `t = ${dec.t} ms, 남은 기한 ${dec.remDeadline} ms, TTL ${dec.ttl}, 지나온 홉 ${dec.hops}` : '';
  drawPolicy();
}

function showQ(d) {
  policy = d.policy || policy;
  const sel = d.selected; if (!sel) { drawPolicy(); return; }
  if (sel.sat) { $('qSat').textContent = `(${sel.sat[0]}, ${sel.sat[1]})`; if (!selected) { selected = sel.sat; drawGrid(); } }
  const rec = sel.recent || [];
  if (rec.length) { lastDec = rec[rec.length - 1];
    $('qRecent').innerHTML = rec.slice().reverse().map(r => `<div class="rrow"><span>${r.t}</span>` +
      [0, 1, 2, 3].map(k => `<span class="${r.action === k ? 'pk' : ''}">${r.mask[k] ? r.qRaw[k].toFixed(2) : '<i class="kr" style="font-style:normal;font-family:var(--font);color:#AAA">막힘</i>'}</span>`).join('') +
      `<span class="pk kr">${ARROW[r.action]} ${DIRS[r.action]}</span><span class="kr ${r.random ? 'rnd' : ''}">${r.random ? '탐험' : '최고 점수'}</span><span>${r.remDeadline} ms</span></div>`).join(''); }
  render();
}
render();
