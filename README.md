# 26-2capstone2


명지대학교 26-2 캡스톤디자인2


## 노션 링크


https://app.notion.com/p/3db5148e6a86803f8f6ee95d6399f367?v=3db5148e6a868062880c000ce3e49d72&source=copy_link

## GSL 시뮬레이터 — 1단계

MATLAB satelliteScenario 기반의 Starlink-like 위성군(1,584기), 지상국, elevation/visibility, 3D 시각화를 구현했습니다.

- [팀원용 설명 및 실행 가이드](gsl/README.md)
- [MATLAB 코드](gsl/)
- [실행 검증 로그](gsl/validation_stage1.log)

MATLAB에서 `gsl` 폴더를 Current Folder로 설정하고 실행하세요.

```matlab
R = main_gsl_simulation;
play(R.scenario);
```

검증 환경: MATLAB R2026a Update 5 + Aerospace Toolbox. GS 좌표와 실험 조건은 `gsl/configGSL.m`에서 변경합니다.

현재 범위는 궤도와 기하학적 가시성입니다. Propagation Delay/Doppler/Link Budget은 다음 단계에서 추가합니다.
