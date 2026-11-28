# 노드 기록 - 일정 간격(step)마다 위성(노드)별 큐 상태와 그 사이에 일어난 일을 노드 1개 = 1줄로 기록
#
# decision_log는 패킷 기준(패킷이 지나간 순간만 기록)이고, node_log는 노드 기준(모든 노드를 같은 간격으로 기록)
# 1줄 = (기록 시각, 노드 1개). 기록 간격 P.nodeLogInterval step마다 36줄씩 쌓임
import numpy as np

NODE_LOG_COLUMNS = [
    'step', 'p', 's',
    'q_up', 'q_down', 'q_left', 'q_right',              # 기록 시각의 링크 큐 길이 (그 step 전송 후 남은 것)
    'qmax_up', 'qmax_down', 'qmax_left', 'qmax_right',  # 직전 기록 이후 링크 큐 최대 길이 (전송 직전 기준)
    'main_queued', 'bg_queued',                         # 기록 시각에 이 노드 큐에 있는 주 흐름 / 배경 패킷 수
    'min_rem_deadline',                                 # 이 노드 큐 안 주 흐름 패킷의 남은 기한 최솟값 (-1: 없음)
    'main_sent', 'bg_sent',                             # 직전 기록 이후 이 노드가 보낸 패킷 수
    'main_overflow', 'bg_overflow',                     # 직전 기록 이후 이 노드에서 큐 오버플로로 버려진 수
    'main_late_mid', 'main_ttl_expired',                # 직전 기록 이후 이 노드에서 중간 기한 초과 / TTL 만료된 수
    'main_on_time', 'main_late_dst',                    # 직전 기록 이후 이 노드(목적지)에 기한 내 / 기한 초과로 도착한 수
]
# 없는 방향(Grid 끝)은 -1


class NodeLog:
    def __init__(self, P, G, maxPackets):
        self.interval = P.nodeLogInterval
        self.deadline = P.deadline
        self.maxPackets = maxPackets
        self.nS = P.satsPerPlane
        self.numNodes = P.numPlanes * P.satsPerPlane
        # 노드 번호 = p * satsPerPlane + s (compute_metrics와 같음)
        self.nodeP = np.arange(self.numNodes) // self.nS
        self.nodeS = np.arange(self.numNodes) % self.nS
        self.nodeLink = np.full((self.numNodes, 4), -1)   # 노드 x 방향 -> 링크 번호 (-1: 없음)
        self.linkNode = np.full(G.numLinks, -1)           # 링크 -> 출발 노드
        for p in range(P.numPlanes):
            for s in range(P.satsPerPlane):
                for d in range(4):
                    if G.hasLink[p, s, d]:
                        l = G.linkId[p, s, d]
                        self.nodeLink[p * self.nS + s, d] = l
                        self.linkNode[l] = p * self.nS + s
        self.hasLink = self.nodeLink >= 0
        self.dstNode = G.dstSat[0] * self.nS + G.dstSat[1]

        # 구간 누적값 (기록할 때마다 0으로)
        self.qMax = np.zeros(G.numLinks, dtype=np.int64)
        self.sentAll = np.zeros(G.numLinks, dtype=np.int64)
        self.sentMain = np.zeros(G.numLinks, dtype=np.int64)
        self.count = np.zeros((self.numNodes, 6), dtype=np.int64)   # main/bg 오버플로, 중간 기한, TTL, 기한 내, 목적지 기한 초과
        self.rows = []

    def node(self, p, s):
        return np.asarray(p) * self.nS + np.asarray(s)

    def add(self, col, nodes):
        # col: 0 main 오버플로, 1 bg 오버플로, 2 중간 기한 초과, 3 TTL 만료, 4 기한 내 도착, 5 목적지 기한 초과
        np.add.at(self.count[:, col], nodes, 1)

    def peak(self, queueLen):
        # 라우팅 후 전송 전 (큐가 가장 찬 순간) 호출
        np.maximum(self.qMax, queueLen, out=self.qMax)

    def sent(self, active, n, links, ids):
        # active: 보낸 링크, n: 링크별 보낸 수, links/ids: 보낸 패킷별 링크 번호와 패킷 id
        self.sentAll[active] += n
        self.sentMain += np.bincount(links[ids < self.maxPackets], minlength=len(self.sentMain))

    def record(self, t, queueLen, queueBuf, queueHead, queueMax, genTime, force=False):
        # step 끝에 호출, 기록 간격마다 노드별 1줄
        if not force and t % self.interval:
            return
        mainQ = np.zeros(len(queueLen), dtype=np.int64)
        minRem = np.full(len(queueLen), np.iinfo(np.int64).max)
        for l in np.flatnonzero(queueLen > 0):
            ids = queueBuf[l, (queueHead[l] + np.arange(queueLen[l])) % queueMax]
            m = ids[ids < self.maxPackets]
            mainQ[l] = len(m)
            if m.size:
                minRem[l] = self.deadline - (t - genTime[m].min())   # 가장 오래된 패킷이 남은 기한 최소

        L = np.where(self.hasLink, self.nodeLink, 0)
        q = np.where(self.hasLink, queueLen[L], -1)
        qmax = np.where(self.hasLink, self.qMax[L], -1)
        mainQueued = np.where(self.hasLink, mainQ[L], 0).sum(1)
        bgQueued = np.where(self.hasLink, queueLen[L], 0).sum(1) - mainQueued
        rem = np.where(self.hasLink, minRem[L], np.iinfo(np.int64).max).min(1)
        rem = np.where(mainQueued > 0, rem, -1)
        sentMain = np.where(self.hasLink, self.sentMain[L], 0).sum(1)
        sentBg = np.where(self.hasLink, self.sentAll[L], 0).sum(1) - sentMain

        self.rows.append(np.column_stack([
            np.full(self.numNodes, t), self.nodeP, self.nodeS, q, qmax,
            mainQueued, bgQueued, rem, sentMain, sentBg, self.count]))

        self.qMax[:] = 0
        self.sentAll[:] = 0
        self.sentMain[:] = 0
        self.count[:] = 0

    def table(self):
        if not self.rows:
            return np.zeros((0, len(NODE_LOG_COLUMNS)), dtype=np.int64)
        return np.vstack(self.rows).astype(np.int64)
