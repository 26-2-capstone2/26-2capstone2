// 3-2: 선택한 위성의 방향별 Q값, 선택 확률, 관측
const DIRS = ['상', '하', '좌', '우'], ARROW = ['↑', '↓', '←', '→'];
const CELL = [1, 7, 3, 5];   // 3x3 십자에서 상, 하, 좌, 우 칸 위치
let lastDec = null;

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

// 관측 15개 (coarse, 기본) 또는 19개 (coarseIn: + 들어온 방향 4, 이리듐 2차 모델): 큐 3단계 4, 이웃 부하 4, 링크 유무 4, 남은 거리 2, 남은 기한 1
const OBS_ROWS = [['큐 단계 (0, 0.5, 1)', 0], ['이웃 부하 ÷ 200 (30 ms 전)', 4], ['링크 유무', 8]];
function obsTable(o) {
  if (o) $('obsN').textContent = o.length;
  let h = '<tr><th></th>' + DIRS.map(d => `<th style="text-align:right">${d}</th>`).join('') + '</tr>';
  for (const [name, k] of OBS_ROWS) h += `<tr><th>${name}</th>` + [0, 1, 2, 3].map(d => `<td>${o ? o[k + d].toFixed(2) : '-'}</td>`).join('') + '</tr>';
  h += `<tr><th>남은 거리 p, s (한 축 최대 거리로 나눔)</th><td colspan="2">${o ? o[12].toFixed(2) : '-'}</td><td colspan="2">${o ? o[13].toFixed(2) : '-'}</td></tr>`;
  h += `<tr><th>남은 기한 ÷ ${grid.normDeadline || 70}</th><td colspan="4">${o ? o[14].toFixed(2) : '-'}</td></tr>`;
  if (o && o.length === 19) h += `<tr><th>들어온 방향</th>` + [0, 1, 2, 3].map(d => `<td>${o[15 + d].toFixed(0)}</td>`).join('') + '</tr>';
  if (o && o.length === 23) for (const [name, k] of [['큐 증가 속도 ÷ 50', 15], ['최근 큐 넘침 ÷ 300', 19]]) h += `<tr><th>${name}</th>` + [0, 1, 2, 3].map(d => `<td>${o[k + d].toFixed(2)}</td>`).join('') + '</tr>';
  $('obsTbl').innerHTML = h;
}

function render() {
  const dec = lastDec;
  cross('qCross', dec && dec.qRaw, dec, v => v.toFixed(2));
  cross('pCross', dec && dec.prob, dec, v => v.toFixed(2));
  $('pNote').textContent = dec ? `ε = ${dec.eps}, 가능한 방향 n = ${dec.mask.reduce((a, b) => a + b, 0)}. ${dec.random ? '이번엔 탐험으로 무작위 방향을 골랐습니다.' : '이번엔 점수가 가장 높은 방향을 골랐습니다.'}`
    : 'ε-greedy: 최고 점수 1 - ε + ε/n, 나머지 ε/n, 막힘 0';
  obsTable(dec && dec.obs);
  $('obsMeta').textContent = dec ? `t = ${dec.t} ms, 남은 기한 ${dec.remDeadline} ms, TTL ${dec.ttl}, 지나온 홉 ${dec.hops}` : '';
}

function showQ(d) {
  const sel = d.selected; if (!sel) return;
  if (sel.sat) { $('qSat').textContent = `(${sel.sat[0]}, ${sel.sat[1]})`; if (!selected) { selected = sel.sat; drawGrid(); } }
  const rec = sel.recent || [];
  if (rec.length) { lastDec = rec[rec.length - 1];
    $('qRecent').innerHTML = rec.slice().reverse().map(r => `<div class="rrow"><span>${r.t}</span>` +
      [0, 1, 2, 3].map(k => `<span class="${r.action === k ? 'pk' : ''}">${r.mask[k] ? r.qRaw[k].toFixed(2) : '<i class="kr" style="font-style:normal;font-family:var(--font);color:#AAA">막힘</i>'}</span>`).join('') +
      `<span class="pk kr">${ARROW[r.action]} ${DIRS[r.action]}</span><span class="kr ${r.random ? 'rnd' : ''}">${r.random ? '탐험' : '최고 점수'}</span><span>${r.remDeadline} ms</span><span>${r.dst ? `(${r.dst[0]}, ${r.dst[1]})` : '-'}</span></div>`).join(''); }
  render();
}
render();
