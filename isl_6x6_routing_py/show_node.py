# 노드 상태 보기 - node_log CSV로 노드별 요약(터미널 표 + 6x6 지도)과 노드 1개의 시간 변화를 창에 띄움 (main_isl 다음에 실행)
#
# 사용법
#   python show_node.py            -> 가장 손실이 많은 노드
#   python show_node.py 3 0        -> 노드 (p=3, s=0)의 시간 변화
#   python show_node.py 3 0 0.1    -> ε = 0.1 실행의 노드 (3,0)
# (show_results.py는 main_isl이 저장한 PNG를 보여 주고, 이 파일은 원하는 노드를 골라 볼 때 사용)
import os
import sys

import matplotlib.pyplot as plt

from plot_nodes import busiest_node, fig_node_map, fig_node_time, load_node_log, node_summary, print_node_table

# ---- 기본값 ----
epsilon = 0.0          # 볼 실행 (ε = 0: 성능 측정용, 0.1: 데이터 수집용)
genRate = 60           # 볼 실행의 생성률

if len(sys.argv) >= 4:
    epsilon = float(sys.argv[3])
baseDir = os.path.dirname(os.path.abspath(__file__))
tag = f'rate{genRate}pps_eps{epsilon:.1f}'
c = load_node_log(os.path.join(baseDir, 'results', f'node_log_{tag}.csv'))
summary = node_summary(c)

if len(sys.argv) >= 3:
    nodeP, nodeS = int(sys.argv[1]), int(sys.argv[2])
else:
    nodeP, nodeS = busiest_node(summary)

print_node_table(summary, tag)
fig = fig_node_map(summary, tag)
fig.canvas.manager.set_window_title(f'노드별 요약 지도 ({tag})')
fig = fig_node_time(c, nodeP, nodeS, tag)
fig.canvas.manager.set_window_title(f'노드 ({nodeP},{nodeS}) 시간 변화 ({tag})')
plt.show()
