# 측정 흐름만 골라내기 - 결과 지표와 그래프를 측정 흐름(흐름 0) 기준으로 계산할 때 사용
#
# 흐름 0 = 측정 흐름 (검증, 평가 때 srcSat -> dstSat 고정). 흐름 1 ~ numFlows-1 = 다른 GSL 흐름 (트래픽 역할)
# measured_view(R): 시뮬레이션 결과 R(에피소드 1개 또는 merge_episodes로 합친 것)에서 측정 흐름 패킷만 남긴 복사본
#   패킷 배열(status, genTime, endTime, hops, packetEpisode, packetFlow)과 결정 기록(decisionLog)을 함께 줄이고
#   패킷 번호를 0부터 다시 매김 -> compute_metrics, plot_analysis, plot_bursts를 그대로 쓸 수 있음
#   링크 사용량(linkSent), 배경 트래픽 통계(bg), 노드 기록(nodeLog)은 모든 패킷 기준 그대로 둠 (망 전체 상태)
import copy

import numpy as np

PACKET_FIELDS = ('genTime', 'endTime', 'hops', 'status', 'packetEpisode', 'packetFlow', 'flowSeq')


def measured_view(R, flow=0):
    pf = getattr(R, 'packetFlow', None)
    if pf is None or int(getattr(R, 'numFlows', 1)) <= 1:
        return R
    keep = np.asarray(pf) == flow
    newId = np.full(R.numPackets, -1, dtype=np.int64)
    newId[keep] = np.arange(int(keep.sum()))
    V = copy.copy(R)
    for name in PACKET_FIELDS:
        arr = getattr(R, name, None)
        if arr is not None and len(arr) == R.numPackets:
            setattr(V, name, np.asarray(arr)[keep])
    D = getattr(R, 'decisionLog', None)
    if D is not None and len(D):
        ids = D[:, 1].astype(np.int64)
        ok = (ids >= 0) & (ids < R.numPackets)
        ok[ok] = keep[ids[ok]]
        D2 = D[ok].copy()
        D2[:, 1] = newId[ids[ok]]
        V.decisionLog = D2
    V.numPackets = int(keep.sum())
    V.numFlows = 1
    V.measuredOnly = True
    return V


def scope_text(P):
    # 그래프 제목에 붙일 설명 (흐름이 1개면 빈 문자열)
    if int(getattr(P, 'numFlows', 1)) <= 1:
        return ''
    s, d = P.srcSat, P.dstSat
    return f'측정 흐름 ({int(s[0])},{int(s[1])})→({int(d[0])},{int(d[1])}) 기준'
