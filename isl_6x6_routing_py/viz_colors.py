# 그래프 색 모음 - 모든 결과 그래프가 같은 색을 쓰도록 한 곳에서 정함
#
from types import SimpleNamespace

import matplotlib
from matplotlib import font_manager


def viz_colors():
    C = SimpleNamespace()
    # 실행(시리즈) 색: 고정 순서 1 파랑, 2 주황, 3 청록, 4 노랑 (색약 구분 검증된 순서)
    C.series = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']
    # 링크 사용량 (적음 -> 많음, 파랑 한 가지 색의 명암)
    C.seqLow = '#dbe9fa'
    C.seqHigh = '#0d3a73'
    C.unused = '#e6e5e0'
    # 글자 / 축 / 격자
    C.text = '#0b0b0b'
    C.muted = '#52514e'
    C.axis = '#8a8984'
    C.grid = '#e6e5e0'
    C.font = 'Malgun Gothic'
    return C


def use_korean_font(C):
    # 한글이 깨지지 않도록 matplotlib 기본 글꼴 설정
    names = {f.name for f in font_manager.fontManager.ttflist}
    if C.font in names:
        matplotlib.rcParams['font.family'] = C.font
    matplotlib.rcParams['axes.unicode_minus'] = False
