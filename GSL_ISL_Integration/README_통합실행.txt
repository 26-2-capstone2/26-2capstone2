GSL -> ISL 논리적 통합 초안 (MATLAB)

1) MATLAB Current Folder를 이 폴더로 지정
2) addpath(fullfile(pwd,'gsl'));
3) CFG = configGSL(); CFG.openViewer = false;
4) R = main_gsl_simulation(CFG);
5) [E, S, T] = run_gsl_isl_bridge(R);
6) T / E(1:5,:) 확인

원본 코드 보존: 이 ZIP 안의 gsl/은 검증수정본 복사본이며,
isl/의 run_isl_sim.m은 외부 패킷 입력을 선택적으로 받도록 확장함.
기존 5인자 호출 방식은 그대로 지원.

해석 주의:
- 현재 GSL은 단일 지상국 다운링크 모델임. 통합에서는 이 결과를
  첫 구간 성공/지연의 대용으로만 사용. 실제 uplink 모델이 아님.
- ISL 6x6은 논리적 격자이며 GSL 1584개 위성과 실제 매핑하지 않음.
- 최종 다운링크 및 두 지상국간 전체 E2E는 아직 구현되지 않음.
- Deadline 초과 패킷은 ISL 통합 모드에서 중간 폐기하지 않고,
  늦게 도착하면 late delivered로 기록.
- GSL PHY high SNR 0 PER는 곡선 범위 밖 근사치.
- MATLAB 실행 검증은 수행하지 못함. MATLAB에서 출력/오류를 확인할 것.
