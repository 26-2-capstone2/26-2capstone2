# 에피소드 묶기 - 에피소드(짧은 독립 실행) 여러 개의 결과를 하나의 결과(R)로 합침
#
# 한 에피소드 = run_isl_sim 1회 (큐가 비어 있는 상태에서 시작, 핫스팟 시나리오 1개)
# 합친 결과는 기존 compute_metrics / plot_analysis가 그대로 쓸 수 있는 모양
#   - 패킷 생성/종료 시각은 에피소드 번호 x 에피소드 길이만큼 밀어서 이어 붙임 (시간축이 연속이 되도록)
#   - 패킷 id, 결정 기록의 packet_id도 이어서 번호를 다시 매김
import copy
from types import SimpleNamespace

import numpy as np


def merge_episodes(Rs, P):
    # Rs: 같은 (genRate, epsilon)으로 돌린 에피소드 결과 리스트 (에피소드 순서대로)
    M = SimpleNamespace()
    M.genRate = Rs[0].genRate
    M.epsilon = Rs[0].epsilon
    M.grid = Rs[0].grid
    M.numEpisodes = len(Rs)

    genT, endT, hops, status, ep, logs = [], [], [], [], [], []
    pktOffset = 0
    for e, R in enumerate(Rs):
        shift = e * P.simTime                       # 에피소드 길이만큼 시간 이동
        genT.append(R.genTime + shift)
        endT.append(R.endTime + shift)
        hops.append(R.hops)
        status.append(R.status)
        ep.append(np.full(R.numPackets, e, dtype=np.int64))
        D = R.decisionLog.copy()
        D[:, 0] += shift                            # t
        D[:, 1] += pktOffset                        # packet_id
        logs.append(D)
        pktOffset += R.numPackets

    M.genTime = np.concatenate(genT)
    M.endTime = np.concatenate(endT)
    M.hops = np.concatenate(hops)
    M.status = np.concatenate(status)
    M.packetEpisode = np.concatenate(ep)            # 패킷이 속한 에피소드 번호 (연속 손실 / 경로 변경 계산용)
    M.decisionLog = np.vstack(logs)
    M.numPackets = pktOffset
    M.endStep = sum(R.endStep for R in Rs)
    M.linkSent = sum(R.linkSent for R in Rs)
    M.bg = {k: sum(R.bg[k] for R in Rs) for k in Rs[0].bg}
    M.perEpisode = Rs                               # 에피소드별 원본 결과 (애니메이션 등에 사용)
    return M


def total_params(P):
    # 후처리(지표, 그래프)용: simTime을 전체 길이(에피소드 길이 x 개수)로 바꾼 설정 복사본
    Pt = copy.copy(P)
    Pt.episodeLen = P.simTime
    Pt.simTime = P.simTime * getattr(P, 'numEpisodes', 1)
    return Pt
