# 패킷 검증 코드 최신화 (2026-10-31)

문제: verify_packets가 기본 설정의 대역폭·정보율이 NaN이고 곡선 밖 오류율이 미확정이라고 기대했으나, 현재 기본 설정은 각각50e6과 ZERO_CWER/UNIT_CWER 정책이므로 충돌했습니다.

수정 내용:
- 입력 누락 검사는 별도 CFG 복사본에서 대역폭만 NaN / 정보율만 NaN / 둘 다 NaN인 세 경우로 검사합니다.
- 기본 범위 밖 정책은 Eb/N0=-1dB → PER=1, 3/24dB → PER=0 및 근사 출처 문자열까지 검사합니다.
- 범위 밖 NaN 검사는 별도의 UNRESOLVED 정책 CFG로 유지합니다.
- 미확정 패킷 집계는 대역폭·정보율을 명시적으로 누락시킨 테스트 CFG에서 검사합니다. 수신·손실 NaN, UNRESOLVED_PHY 원인, 구간별 미확정 통계를 유지합니다.
- verify_uplink도 기본 ZERO_CWER 정책에 맞추고, 이전 끝값 정책은 CONSERVATIVE_ENDPOINT 테스트용 CFG에서 별도로 검사합니다.

MATLAB R2026a 실행:
```matlab
verify_packets
verify_uplink
verify_weather
```
세 함수 모두 PASS. 논문 표 보간·단위 변환·2블록 PER·난수 독립성·패킷별 원인 중복 방지·핸드오버 경계·연속 손실·기한 구분·ITU 계수 검사를 포함합니다.

이번 변경은 검증 코드와 문서만 수정했습니다. getPERfromSNR, 실제 시뮬레이션 설정 및 계산 방식은 변경하지 않았습니다. 검증 PASS는 구현 일관성 검사이며 실제 위성 환경을 실측 검증했다는 뜻은 아닙니다.
