// 2D 지구 지도 위 위성망 (메인 화면, 시뮬레이터가 함께 씀)
// 위성 위치는 서버(web/schema.map_data)가 보낸 [경도, 위도] (한 순간의 배치), 정거원통 도법: x = 경도, y = 위도
// 배경: NASA Visible Earth (공개 이미지, img/earth_2048.jpg)
const MAP_C = { gold: '#FFD54A', hot: '#FF8A1F', loss: '#FF8A1F', sat: '#FFFFFF', satLine: '#2B3A44' };
const EARTH = new Image();
EARTH.src = 'img/earth_2048.jpg';

function mapSize(cv) {
  // 캔버스 화면 크기(가로 기준 2:1)에 맞춰 내부 해상도를 맞춤
  const r = window.devicePixelRatio || 1, w = cv.clientWidth, h = Math.round(w / 2);
  if (cv.width !== Math.round(w * r) || cv.height !== Math.round(h * r)) { cv.width = Math.round(w * r); cv.height = Math.round(h * r); cv.style.height = h + 'px'; }
  const g = cv.getContext('2d'); g.setTransform(r, 0, 0, r, 0, 0); return [g, w, h];
}
const satIdx = (view, ps) => ps[0] * view.sats + ps[1];

// opt: queues(쌍마다), queueMax, hot(켜진 쌍 번호 Set), src, dst([p, s]), packets([[a, b]]), losses([{i, a}]), selected(위성 번호), path(위성 번호 목록), pathColor, hotColor
function drawMap(cv, view, opt = {}) {
  const [g, W, H] = mapSize(cv);
  const X = lon => (lon + 180) / 360 * W, Y = lat => (90 - lat) / 180 * H;
  g.clearRect(0, 0, W, H);
  if (EARTH.complete && EARTH.naturalWidth) g.drawImage(EARTH, 0, 0, W, H); else { g.fillStyle = '#0B1E2D'; g.fillRect(0, 0, W, H); }
  if (!view || !view.geo) return;
  const geo = view.geo, n = geo.length;
  // 극지방 띠 (옆 궤도면 링크 꺼짐)
  if (view.polar) {
    g.fillStyle = 'rgba(255,255,255,0.10)'; g.fillRect(0, 0, W, Y(view.polar)); g.fillRect(0, Y(-view.polar), W, H - Y(-view.polar));
    g.strokeStyle = 'rgba(255,255,255,0.45)'; g.setLineDash([5, 4]); g.lineWidth = 1;
    for (const y of [Y(view.polar), Y(-view.polar)]) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    g.setLineDash([]); g.fillStyle = 'rgba(255,255,255,0.85)'; g.font = '11px "Noto Sans KR", sans-serif'; g.textAlign = 'left';
    g.fillText(`극지방 (위도 ${view.polar}도 이상): 옆 궤도면 링크 꺼짐`, 8, Y(view.polar) - 6);
  }
  const big = n > 300, lw = n > 1000 ? 0.6 : big ? 0.9 : 1.6;
  // 링크 한 개 그리기: 날짜변경선을 넘으면 양쪽 끝으로 나눠 그리고, 극을 넘는 링크는 위아래 가장자리까지 점선
  const seg = (a, b, style, width, dash) => {
    const [x1, y1] = geo[a], [x2, y2] = geo[b], d = ((x2 - x1 + 540) % 360) - 180;
    g.strokeStyle = style; g.lineWidth = width; g.setLineDash(dash || []);
    if (Math.abs(d) <= 60) {
      g.beginPath(); g.moveTo(X(x1), Y(y1)); g.lineTo(X(x1 + d), Y(y2)); g.stroke();
      if (Math.abs(x1 + d) > 180) { g.beginPath(); g.moveTo(X(x2 - d), Y(y1)); g.lineTo(X(x2), Y(y2)); g.stroke(); }
    } else {
      g.setLineDash([3, 3]);
      for (const [x, y] of [[x1, y1], [x2, y2]]) { g.beginPath(); g.moveTo(X(x), Y(y)); g.lineTo(X(x), y > 0 ? 0 : H); g.stroke(); }
    }
    g.setLineDash([]);
  };
  const qmax = opt.queueMax || 200, qs = opt.queues;
  view.pairs.forEach(([a, b], k) => {
    const f = qs ? Math.min(1, qs[k] / qmax) : 0;
    const c = [0x6F + (0xD6 - 0x6F) * f, 0xA8 + (0xF2 - 0xA8) * f, 0xC8 + (0xFF - 0xC8) * f].map(Math.round);
    seg(a, b, `rgba(${c.join(',')},${0.55 + 0.45 * f})`, lw + f * (big ? 1.5 : 3));
  });
  if (opt.hot) for (const k of opt.hot) { const [a, b] = view.pairs[k]; seg(a, b, opt.hotColor || MAP_C.hot, big ? 2.5 : 4.5); }
  if (opt.path) for (const [c, w] of [['#0B1E2D', big ? 5 : 7], [opt.pathColor || MAP_C.gold, big ? 2.4 : 3.4]])   // 흐름 0 경로 (라우팅 비교), 어두운 테두리 위에 그림
    for (let k = 1; k < opt.path.length; k++) seg(opt.path[k - 1], opt.path[k], c, w);
  // 위성
  const r = n <= 100 ? 4.5 : n <= 500 ? 2.2 : 1.3;
  g.fillStyle = MAP_C.sat; g.strokeStyle = MAP_C.satLine; g.lineWidth = r > 2 ? 1 : 0.4;
  for (const [lon, lat] of geo) { g.beginPath(); g.arc(X(lon), Y(lat), r, 0, 7); g.fill(); if (r > 2) g.stroke(); }
  // 흐름 0 패킷 (금색 점)
  const P = i => [X(geo[i][0]), Y(geo[i][1])];
  if (opt.packets) {
    g.fillStyle = MAP_C.gold;
    opt.packets.forEach(([a, b], k) => {
      const [x1, y1] = P(a), [x2, y2] = P(b), far = Math.abs(x2 - x1) > W / 6;
      const j = ((k * 37) % 7 - 3) * 1.2, x = far ? x2 : (x1 + x2) / 2 + j, y = far ? y2 : (y1 + y2) / 2 + j;
      g.beginPath(); g.arc(x, y, big ? 2.4 : 3.4, 0, 7); g.fill();
    });
  }
  // 흐름 0 출발(채운 네모), 도착(테두리 네모), 지상국(삼각형)
  const sq = big ? 6 : 9;
  const mark = (ps, fill) => {
    if (!ps) return; const [x, y] = P(satIdx(view, ps));
    g.strokeStyle = MAP_C.gold; g.fillStyle = fill ? MAP_C.gold : '#183D4E'; g.lineWidth = 2.2;
    g.beginPath(); g.roundRect(x - sq, y - sq, 2 * sq, 2 * sq, 2); g.fill(); g.stroke();
    const ty = y + sq + 18; g.setLineDash([3, 3]); g.lineWidth = 1.4; g.beginPath(); g.moveTo(x, y + sq); g.lineTo(x, ty - 7); g.stroke(); g.setLineDash([]);
    g.fillStyle = MAP_C.gold; g.strokeStyle = '#5A4500'; g.lineWidth = 1; g.beginPath(); g.moveTo(x, ty - 7); g.lineTo(x + 7, ty + 5); g.lineTo(x - 7, ty + 5); g.closePath(); g.fill(); g.stroke();
  };
  mark(opt.src, true); mark(opt.dst, false);
  // 손실 X (잠깐 보였다 사라짐)
  if (opt.losses) {
    g.strokeStyle = MAP_C.loss; g.lineWidth = 2.4;
    for (const e of opt.losses) { const [x0, y0] = P(e.i), x = x0 + 10, y = y0 - 10; g.globalAlpha = e.a;
      g.beginPath(); g.moveTo(x - 5, y - 5); g.lineTo(x + 5, y + 5); g.moveTo(x + 5, y - 5); g.lineTo(x - 5, y + 5); g.stroke(); }
    g.globalAlpha = 1;
  }
  if (opt.selected != null) { const [x, y] = P(opt.selected); g.strokeStyle = MAP_C.hot; g.lineWidth = 2; g.setLineDash([4, 3]); g.strokeRect(x - 13, y - 13, 26, 26); g.setLineDash([]); }
  g.fillStyle = 'rgba(255,255,255,0.7)'; g.font = '10px sans-serif'; g.textAlign = 'right'; g.fillText('Image: NASA Visible Earth', W - 8, H - 8);
}

// 지도에서 누른 곳과 가장 가까운 위성 번호 (없으면 null)
function mapPick(cv, view, ev) {
  if (!view || !view.geo) return null;
  const rc = cv.getBoundingClientRect(), W = rc.width, H = rc.height, x = ev.clientX - rc.left, y = ev.clientY - rc.top;
  let best = null, bd = 18;
  view.geo.forEach(([lon, lat], i) => { const d = Math.hypot((lon + 180) / 360 * W - x, (90 - lat) / 180 * H - y); if (d < bd) { bd = d; best = i; } });
  return best;
}
