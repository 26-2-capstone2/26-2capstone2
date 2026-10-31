# 전 범위 근사와 그래프 연동 검증 (2026-10-31)

MATLAB R2026a. 기본 정책: 높은 Eb/N0 ZERO_CWER, 낮은 Eb/N0 UNIT_CWER, 공개 곡선 내부 보간.

- verify_environment_slider: 실제 main을 6초/1584위성으로 실행. 지구본이 생성되지 않음. 0/2/4/8/8.2/12/20dB의 실제 UI 콜백을 호출하여 성능 창과 채널/손실 구간 창의 SNR YData, Lost/On time XData, 연속 손실 stem YData가 새 결과와 일치함을 확인. 창 개수·패킷 재생 시각 유지, 미확정0, 유한 PLR 확인.
- verify_attenuation_slider: 곡선 위/아래 포화, 경계점에서 논문 값 유지, 명시적 UNRESOLVED 대체 정책, 동일 ID 난수의 단조 손실, 원인별 합계 일치 확인.
- verify_saturation_sweep: 저장된 실제600초 기하를 재사용하여 0:0.5:20dB의 41조건을 검사. 모든 조건에서 미확정0, 유한 PLR/기한 내 도착률, 생성=수신+손실, 손실=PHY+HO+연결불가, 같은 난수의 단조 손실을 검사. 0dB의 PHY손실0, 20dB 수신0을 확인.
- 결과 CSV: docs/saturation_sweep.csv. 화면: docs/environment_slider.png, docs/environment_diagnostics.png. 현재 모델의 저장 예시: results_attenuation/loss_8.2_dB/.

위 검증은 코드의 동작과 집계 일관성 검증입니다. 양 끝의 근사 정책을 실제 장비의 복호화 성능으로 실증한 검증이 아닙니다. 600초 궤도 전체의 새 전파는 반복하지 않고 저장된 기하에 새 PHY 모델을 적용했습니다. 기존 validation_environment/attenuation 문서의 미확정 예시는 이전 정책의 역사적 결과입니다.
