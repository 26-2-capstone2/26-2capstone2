# 패킷 계층 안내

2026-10-29부터 평가 방향은 **GSL uplink(지상국→첫 위성)** 입니다.

최신 정의와 가정은 [GSL_UPLINK_GUIDE.md](GSL_UPLINK_GUIDE.md)를 참고하세요. 기존 1011 GSL→ISL 논리적 통합 결과와 이 GSL 전용 실행을 구분합니다.

ID와 생성 시각을 유지하고, 첫 위성 도착 시 GSL 완료로 판정합니다. packet_results.csv는 전체 원본 기록이고 isl_input_packets.csv는 도착한 패킷의 인계 파일입니다. 손실률·기한 내 도착률·연속 손실은 원본 ID 기준으로 집계합니다. 실제 UDP 소켓을 사용하는 실측은 아닙니다.
