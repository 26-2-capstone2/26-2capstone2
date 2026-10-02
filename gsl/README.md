# GSL 시뮬레이터 — 1단계

이번 버전은 satelliteScenario, Starlink-like 위성군, 지상국, elevation/visibility, 3D 시각화만 구현합니다. Serving 선택, handover, Propagation Delay, Doppler, Link Budget, UDP/PER는 다음 단계입니다. 저장한 slant range는 `aer`의 기하 출력이며 지연 모델은 아직 적용하지 않았습니다.

## 실행

MATLAB의 Current Folder를 이 README와 `.m` 파일들이 있는 `gsl` 폴더로 설정한 뒤 실행합니다.

```matlab
R = main_gsl_simulation;
play(R.scenario); % 3D viewer에서 위성 이동 재생
```

설정 변경 예시:

```matlab
CFG = configGSL();
CFG.gsLatitude_deg = 37.0;
CFG.gsLongitude_deg = 128.0;
CFG.gsAltitude_m = 0;
CFG.duration_s = 600;
R = main_gsl_simulation(CFG);
play(R.scenario);
```

`configGSL.m`에서 실험 조건을 수정합니다. 날짜는 UTC이며 기본 2026-10-02 00:00 UTC는 한국시간 09:00입니다. GS 기본 위치는 임시 예시(37°N, 128°E)로, 명지대학교나 확정된 연구 지점 좌표가 아닙니다. 고도는 WGS84 타원체 기준 m이며 지형의 해발고도와 다릅니다.

3D viewer에는 지구·1,584기 위성·GS와 유효 access 연결선이 표시됩니다. 궤도선/위성 이름을 기본적으로 줄이는 `ShowDetails=false`를 사용합니다. 여러 연결선은 후보 위성의 기하학적 access이며 serving link가 아닙니다. Viewer 재생은 계산 표본 간격(1초)과 별개이며 화면 성능에 따라 느릴 수 있습니다. 계산만 하려면 `CFG.openViewer=false; CFG.makePlots=false;`를 설정합니다.

## 모델과 단위

| 항목 | 기본값 / 해석 |
|---|---|
| 위성군 | Walker-Delta 53:1584/72/39, 원형 궤도 |
| 고도 | 550,000 m; WGS84 적도반지름 6,378,137 m에 더해 궤도반경 정의 |
| 경사각 | 53° |
| 궤도면 | 72개, RAAN 간격 360/72 = 5° |
| 면당 위성 | 22기, 면 내 위상 간격 360/22° |
| phaseFactor | F=39; 이웃 면의 대응 위성 위상차는 360×39/1584 ≈ 8.8636° |
| 전파기 | two-body-keplerian |
| 시간 | 600초, 1초 간격, 양 끝 포함 601개 표본 |
| 후보 조건 | GS 기준 elevation ≥ 25° |

550 km는 기준 반지름에 대한 원형 궤도 높이입니다. 타원체 표면 기준 위도별 실제 고도가 정확히 550 km로 일정하다는 의미는 아닙니다. 위상 인자 39는 39°가 아닙니다. 사용자가 제공한 수치를 이상화한 Starlink-like 참조 모델이며 실제 운용 Starlink TLE/정밀 궤도를 재현하지 않습니다. J2, 항력, 지형·건물 가림은 반영하지 않습니다. 짧은 시간의 1단계 geometry 검증을 위한 가정입니다.

`hasCandidate=true`는 위성이 기하학적으로 보인다는 뜻입니다. RF 연결 성공, 서비스 보장, 패킷 성공을 의미하지 않습니다. 후보가 없는 경우 count=0, hasCandidate=false로 저장합니다. 그래프의 최대 elevation은 모든 위성의 순간 최댓값이며 serving 위성 추적 결과가 아닙니다. 별도로 하나의 고정 위성 elevation도 표시합니다.

## 파일과 함수 설명

| 파일 / API | 역할과 출력 |
|---|---|
| `configGSL.m` | 단위가 표시된 CFG 설정 구조체 반환 |
| `main_gsl_simulation.m` | scenario/GS/access를 만들고 계산·저장·시각화 연결; R 반환 |
| `createConstellation.m` | `walkerDelta`로 1,584개 Satellite 객체 생성 |
| `computeGeometry.m` | elevation, slant range, 가시성, 표본 시각 계산; G 반환 |
| `plotResults.m` | elevation/후보 수/후보 유무 그래프와 오프라인 ECEF 3D 이미지 |
| `verify_stage1.m` | 전체 기본 시나리오와 후보 0개 경계 사례 검증 |
| `satelliteScenario` | 시작/끝/표본 간격이 있는 시뮬레이션 시간축과 객체 컨테이너 |
| `groundStation` | 고정 지상국, 타원체 좌표와 최소 elevation 설정 |
| `aer(gs,sats)` | GS 기준 azimuth·elevation(deg)·직선거리(m)·시각 반환 |
| `access(gs,sats)` / `accessStatus` | 가시선과 GS 최소 elevation을 적용한 표본별 접근 가능 여부 |
| `states(...,'CoordinateFrame','ecef')` | 지구 고정 좌표계 위치(m), 속도(m/s); 이번 단계는 양 끝 위치로 이동 확인 |
| `satelliteScenarioViewer` / `play` | 실제 scenario의 3D 표시 / 시간 재생 |

MATLAB의 `aer`/`accessStatus`는 위성×시간 배열을 반환합니다. 본 코드에서는 후속 처리를 위해 시간×위성으로 전치해 저장합니다. `states`는 3×시각×위성 형태이므로 한 시각의 위치를 3×위성으로 정리합니다. 향후 Doppler에서는 같은 좌표계의 상대 위치/속도를 사용해야 하며, 좌표계를 섞으면 안 됩니다.

## 설치 환경과 Toolbox

실제 확인 환경: MATLAB R2026a Update 5, Aerospace Toolbox 26.1. Satellite Communications Toolbox와 Communications Toolbox는 설치 목록에 없었습니다.

| 제품 | 이번 단계 필요 여부 |
|---|---|
| MATLAB | 필수 |
| Aerospace Toolbox | 현재 환경의 필수 geometry/viewer 제공 제품; 실제 API 호출 확인 |
| Satellite Communications Toolbox | 이번 환경에서는 추가 설치 불필요. 동일 scenario 계열 API와 향후 RF 관련 기능을 제공하는 대안 제품 |
| Communications Toolbox | 이번 단계 불필요. 향후 coding 기반 PER 곡선 생성 선택 시 검토 |
| Simulink / Mapping Toolbox / Parallel Computing Toolbox | 이번 코드에 필요 없음 |

다른 PC에서는 `ver`, `which satelliteScenario`, `help satelliteScenario.walkerDelta`로 설치/함수를 확인하세요. 필요한 제품이 없다면 본 코드는 명시적 오류를 반환합니다. Toolbox 없는 대안은 Kepler 2체 전파 → ECI/ECEF 회전 → WGS84 GS 좌표 → ENU elevation → `plot3`/`surf` 애니메이션을 직접 구현하는 것입니다. 정확한 시간·지구회전 처리가 별도로 필요하며 이번 버전에 해당 대안을 혼합하지 않았습니다.

## 결과 파일

실행 시 `results_stage1` 폴더에 저장합니다. 같은 폴더로 재실행하면 결과 파일은 갱신됩니다. 실험을 보존하려면 `CFG.outputDir`를 변경하세요.

- `geometry_stage1.mat`: CFG와 G. 시간×위성의 elevation_deg, slantRange_m, isVisible, accessStatus와 시각/위성 인덱스/시작·끝 위치.
- `visibility_summary.csv`: time_s, visibleSatelliteCount, hasCandidate, maxElevation_deg. Boolean은 0/1.
- `satellite_index.csv`: MATLAB 반환 배열의 1-based satelliteIndex와 이름 매핑. 실제 NORAD ID가 아닙니다.
- `visibility.png`: 시간별 elevation과 가시성.
- `environment_3d.png`: 초기 시각의 오프라인 3D 도식. 회색=전체 위성, 초록=가시 위성/연결선, 빨강=GS.

MAT에는 전체 후보 정보를 보존하고 CSV에는 간단한 요약만 기록합니다. 아직 serving ID, SNR, Doppler, PER 같은 미구현 항목을 0으로 채워 출력하지 않습니다. Python에서는 `scipy.io.loadmat(..., simplify_cells=True)`로 MAT v7의 수치 배열을 읽을 수 있고, 시간축은 숫자형 G.time_s를 사용하면 됩니다. MATLAB datetime은 Python에서 별도 해석이 필요합니다.

## 검증

```matlab
verify_stage1
```

1,584기/601개 표본, 1초 간격, 위성 이동, 원형 궤도 반경, elevation 범위, `elevation>=25`와 Toolbox access의 일치, 시간에 따른 가시성 변화, viewer의 60초 시점 이동을 확인합니다. 별도 90° elevation mask 사례로 후보가 없는 상황도 확인합니다. 자세한 실제 실행 결과는 `validation_stage1.log`에 있습니다. 검증에서 viewer 생성/시간 변경을 확인하는 것과 모든 화면의 시각적 품질 검수는 구별됩니다.

실제 실행 결과(2026-10-02): 두 검증 모두 PASS. 기본 시나리오에서 가시 위성 9~13기, 초기 11기, 후보 존재 표본 비율 100%. 시작/종료 위치의 최소 변위 4,295.3 km. 기본 계산·그림 저장·viewer 검증 소요 약 135초(실행 환경에 따라 달라짐). 90° mask 사례에서는 모든 표본에서 후보 0개. 저장된 PNG 두 장의 배치와 내용도 확인했습니다. 100%는 이 GS/시간 구간의 표본 결과이며 전 지구·장기 서비스 가용성을 뜻하지 않습니다.

## 공식 API 근거

웹 문서는 최신 릴리스로 바뀔 수 있어 설치된 R2026a의 `help`와 실제 실행을 우선했습니다.

- [satelliteScenario](https://www.mathworks.com/help/aerotbx/ug/satellitescenario.html)
- [walkerDelta](https://www.mathworks.com/help/aerotbx/ug/satellitescenario.walkerdelta.html)
- [Walker 위상차 정의 예제](https://www.mathworks.com/help/aerotbx/ug/analyze-access-between-a-satellite-constellation-and-an-aircraft.html)
- [Access 조건](https://www.mathworks.com/help/aerotbx/ug/matlabshared.satellitescenario.access.html)
- [3D Viewer](https://www.mathworks.com/help/satcom/ref/matlabshared.satellitescenario.satellitescenario.html)

다음 단계에서는 이 geometry를 바탕으로 Propagation Delay/Doppler/Link Budget을 추가합니다. 연구용 SNR 식과 대역폭 정의는 그 단계에서 단위를 검증하고, PER 근거가 확보되기 전에는 손실 그래프를 생성하지 않습니다.

## 팀원 빠른 시작

저장소의 GSL 브랜치를 내려받은 후 MATLAB에서 gsl 폴더를 열어 실행하세요. 기존 저장소 최상위 README의 팀 소개와 노션 링크는 그대로 유지합니다.

현재 단계의 코드는 검증된 geometry 기준 버전입니다. 이후 기능은 이 기준 버전의 결과와 비교하면서 추가합니다. 좌표와 시간 설정을 바꾼 실험은 CFG.outputDir도 바꿔 결과를 보관하세요.

