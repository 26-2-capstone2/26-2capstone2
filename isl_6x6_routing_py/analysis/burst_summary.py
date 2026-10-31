# 연속 손실 요약 - 강화학습 학습 기록(train_rl), 평가(eval_routes), 테스트용
# 손실 구간 계산은 burst_loss.loss_runs(패킷 번호 순서, 에피소드 경계에서 끊음)를 그대로 씀
from types import SimpleNamespace

import numpy as np

from analysis.burst_loss import loss_runs


def loss_run_lengths(status, packet_episode=None):
    # 손실이 이어진 구간 길이 전부 (길이 1 포함). 끝나지 않은 패킷이 있으면 멈춤
    status = np.asarray(status)
    if np.any(status == 0):
        raise ValueError(f'종료되지 않은 주 흐름 패킷 {int(np.sum(status == 0))}개: 지표 계산을 중단합니다')
    if np.any((status < 1) | (status > 5)):
        raise ValueError('알 수 없는 패킷 상태가 있습니다')
    if packet_episode is not None and len(packet_episode) != len(status):
        raise ValueError('packet_episode 길이가 status와 다릅니다')
    return loss_runs(status, packet_episode)[1]


def burst_summary(status, min_len, packet_episode=None):
    # 길이 min_len 이상인 연속 손실과 그 안의 패킷 비율
    if min_len < 2:
        raise ValueError('burstMinLen은 2 이상이어야 합니다')
    runs = loss_run_lengths(status, packet_episode)
    bursts = runs[runs >= min_len]
    return SimpleNamespace(
        burstCount=int(len(bursts)),
        burstPackets=int(bursts.sum()),
        burstPacketRate=float(bursts.sum() / len(status)) if len(status) else 0.0,
        maxConsecLoss=int(runs.max()) if len(runs) else 0,
        lossRuns=runs,
    )
