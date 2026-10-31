// 공통: 상단 띠(메뉴). 각 화면에서 <div id="topbar" data-on="sim"></div> 처럼 넣으면 그려짐
const MENU = [
  ['sim', '시뮬레이터', 'sim.html'],
  ['guide', '사용 설명', 'guide.html'],
  ['settings', '변수 설정', 'settings.html'],
  ['results', '결과 분석', '#'],
  ['compare', '라우팅 비교', '#'],
];
function renderTopbar() {
  const el = document.getElementById('topbar');
  if (!el) return;
  const on = el.dataset.on;
  el.className = 'topbar';
  el.innerHTML = `<a class="brand" href="index.html" style="text-decoration:none">ISL RL Simulator</a><nav>` +
    MENU.map(([k, n, h]) => `<a href="${h}" class="${k === on ? 'on' : ''}" ${h === '#' ? 'title="준비 중"' : ''}>${n}</a>`).join('') + `</nav>`;
}
async function api(path, body) {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  return r.json();
}
document.addEventListener('DOMContentLoaded', renderTopbar);
