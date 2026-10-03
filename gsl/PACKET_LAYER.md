# Packet layer

현재 구현과 실행 방법은 [README.md](README.md)를 따른다. 위성이 바뀌어도 하나의 UDP session을 유지한다.

핵심 경로: computeLinkState → simulatePacketTransmission → getPERfromSNR → computePacketMetrics → reportPacketResults / plotResults.

- Session: 600 s, 60 pps, 160 Bytes, packet ID 1..36000.
- Priority: OUTAGE_LOSS → HANDOVER_LOSS → PHY_LOSS / SUCCESS.
- Actual handover event에만 [tH,tH+100ms) 적용. Fixed drop count 없음.
- PHY: QPSK/AR4JA rate 1/2, k=1024; [JPL Figure 14 lookup](AR4JA_CURVE.md).
- Eb/N0 = C/N +10log10(Bnoise/Rinformation). Missing mapping/outside curve = UNRESOLVED_PHY.
- Packet PER =1-(1-CWER)^2, independent codeword assumption.
- Total and rolling PLR denominator is Generated. Unknown outcomes stay NaN/N/A.
- Default known handover/outage loss is reported separately; lower bound is never total PLR.
- No socket I/O, UDP retransmission, congestion control, queue or arrival-time KPI.

단위 테스트는 B/Rb 변환을 확인하는 synthetic mapping을 사용하며 연구 결과에 export하지 않는다. 현재 실행 검증은 validation_udp_session.log에 기록한다.
