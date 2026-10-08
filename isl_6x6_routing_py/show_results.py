# 결과 보기 - 저장된 지표 표, 그래프, 애니메이션을 창에 띄움 (2. main_isl 다음에 실행)
#
# 저장된 결과를 창에 띄우기
# 1) 지표 요약 표 (터미널), 2) 지표 그래프, 3) 애니메이션 재생 (반복)
import csv
import glob
import os

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from PIL import Image, ImageSequence

baseDir = os.path.dirname(os.path.abspath(__file__))
outDir = os.path.join(baseDir, 'results')

with open(os.path.join(outDir, 'metrics_summary.csv'), newline='') as f:
    for row in csv.reader(f):
        print('  '.join(f'{v:>15}' for v in row))


def show_image(name, title):
    fig = plt.figure(title, facecolor='w')
    plt.imshow(Image.open(os.path.join(outDir, name)))
    plt.axis('off')
    fig.tight_layout()


show_image('metrics_summary.png', '성능 지표 비교')
if os.path.exists(os.path.join(outDir, 'run_analysis.png')):
    show_image('run_analysis.png', '실행 분석')
for png in sorted(glob.glob(os.path.join(outDir, 'node_*.png'))):   # 노드 기준 그림 (node_map: 요약 지도, node_time: 손실 많은 노드)
    name = os.path.basename(png)
    show_image(name, ('노드별 요약 지도: ' if name.startswith('node_map') else '노드 시간 변화: ') + name[:-4].split('_', 2)[2])

anims = []
for gif in sorted(glob.glob(os.path.join(outDir, 'anim_*.gif'))):
    frames = [fr.convert('RGB') for fr in ImageSequence.Iterator(Image.open(gif))]
    fig = plt.figure('애니메이션: ' + os.path.basename(gif), facecolor='w')
    h = plt.imshow(frames[0])
    plt.axis('off')
    fig.tight_layout()
    # 창을 닫을 때까지 반복 재생
    anims.append(FuncAnimation(fig, lambda k, h=h, frames=frames: h.set_data(frames[k]),
                               frames=len(frames), interval=80, repeat=True))

plt.show()
