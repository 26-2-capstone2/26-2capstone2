# 모델 정보 - 모델 폴더의 run_info.txt에서 학습(또는 적응)한 격자 이름을 읽음
import os
import re


def model_grid(modelPath):
    # 반환 예: 'grid:10x10 (10 x 10)', 'grid (6 x 6)', 적응한 모델은 'grid:10x10 (10 x 10) 학습, grid:24x24 (24 x 24) 적응'
    try:
        text = open(os.path.join(os.path.dirname(os.path.abspath(modelPath)), 'run_info.txt'), encoding='utf-8').read()
    except OSError:
        return '알 수 없음'
    adapt = re.search(r'적응 격자 ([^,\n]+)', text)
    if adapt:   # 적응한 모델: 원래 학습 격자 -> 적응 격자
        orig = re.search(r'원래 학습 격자: ([^\n]+)', text)
        return f"{orig.group(1).strip() if orig else '?'} 학습, {adapt.group(1).strip()} 적응"
    m = re.search(r'망 구조 ([^,\n]+)', text)
    return m.group(1).strip() if m else '알 수 없음'
