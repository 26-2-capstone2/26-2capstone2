# 연속 패킷 손실 - 패킷 번호(packet_id) 순서로 손실이 P.burstMinLen개(기본 3개) 이상 이어진 구간을 '연속 손실' 1번으로 셈
#
# 손실 = 기한 내 도착(result 1)이 아닌 모든 패킷
#        (2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료 - 실시간 통신에서는 늦게 온 패킷도 못 쓰므로 손실)
# 패킷 번호 = packet_id (주 흐름 생성 순서, 초당 60개면 약 16.7 ms 간격)
# 에피소드 경계에서는 끊어서 셈 (서로 다른 에피소드의 손실끼리는 이어지지 않음)
#
#   예) 결과: 1 1 4 4 4 1 3 1 2 2 3 3 1   (minLen = 3)
#             손실 구간 = [4 4 4] 길이 3, [3] 길이 1, [2 2 3 3] 길이 4
#             연속 손실 = 2번 (길이 3, 4), 연속 손실에 속한 패킷 = 7개, 단발 손실 = 1개
from types import SimpleNamespace

import numpy as np

# 연속 손실 기록(burst_log CSV) 열: 연속 손실 1번 = 1줄
BURST_COLUMNS = ['burst_id', 'episode', 'first_packet_id', 'last_packet_id', 'length',
                 'first_gen_step', 'last_gen_step', 'span_ms',
                 'n_late_dst', 'n_late_mid', 'n_overflow', 'n_ttl', 'main_cause']
# span_ms: 첫 손실 패킷 생성 ~ 마지막 손실 패킷 생성 사이 시간 (끊긴 시간의 길이)
# n_*: 구간 안 손실 원인별 개수 (2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료)
# main_cause: 가장 많은 손실 원인 (result 번호 2~5, 같으면 작은 번호)
LOSS_CODES = [2, 3, 4, 5]


def loss_runs(status, episode=None):
    # 손실이 이어진 구간 전부 (길이 1 포함). 반환: 구간 시작 위치, 길이 (packet_id 순서)
    status = np.asarray(status)
    n = len(status)
    if n == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    episode = np.zeros(n, dtype=np.int64) if episode is None else np.asarray(episode)
    loss = status != 1
    newEp = np.r_[True, episode[1:] != episode[:-1]]          # 에피소드 첫 패킷
    start = loss & (newEp | ~np.r_[False, loss[:-1]])         # 손실 + (에피소드 시작 또는 직전이 손실 아님)
    end = loss & (np.r_[newEp[1:], True] | ~np.r_[loss[1:], False])   # 손실 + (에피소드 끝 또는 다음이 손실 아님)
    starts = np.flatnonzero(start)
    return starts, np.flatnonzero(end) - starts + 1


def burst_info(R, P):
    # R: run_isl_sim 결과 또는 merge_episodes 결과, P: 설정
    # 반환 B
    #   B.minLen             : 연속 손실 기준 길이
    #   B.runStart, B.runLen : 모든 손실 구간 (길이 1 이상)
    #   B.pktRunLen          : 패킷별, 속한 손실 구간 길이 (손실 아니면 0)
    #   B.pktBurstId         : 패킷별, 속한 연속 손실 번호 (연속 손실이 아니면 -1)
    #   B.table              : 연속 손실 1번 = 1줄 (BURST_COLUMNS 순서)
    minLen = int(getattr(P, 'burstMinLen', 3))
    episode = getattr(R, 'packetEpisode', None)
    if episode is None:
        episode = np.zeros(R.numPackets, dtype=np.int64)
    starts, lens = loss_runs(R.status, episode)

    B = SimpleNamespace(minLen=minLen, runStart=starts, runLen=lens)
    B.pktRunLen = np.zeros(R.numPackets, dtype=np.int64)
    B.pktBurstId = np.full(R.numPackets, -1, dtype=np.int64)
    rows = []
    for st, ln in zip(starts, lens):
        B.pktRunLen[st:st + ln] = ln
        if ln < minLen:
            continue
        bid = len(rows)
        B.pktBurstId[st:st + ln] = bid
        seg = R.status[st:st + ln]
        cnt = [int((seg == c).sum()) for c in LOSS_CODES]
        g0, g1 = int(R.genTime[st]), int(R.genTime[st + ln - 1])
        rows.append([bid, int(episode[st]), st, st + ln - 1, ln, g0, g1,
                     int(round((g1 - g0) * P.stepTime * 1e3)), *cnt, LOSS_CODES[int(np.argmax(cnt))]])
    B.table = np.array(rows, dtype=np.int64).reshape(-1, len(BURST_COLUMNS))
    return B
