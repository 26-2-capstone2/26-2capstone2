# ISL 시뮬레이션 사용 안내 (Python 버전 - MATLAB isl_6x6_routing과 같은 구조, 같은 변수명)
#
# =====================================================================
# 0. 시뮬레이션 베이스라인
# =====================================================================
# 6x6 Grid ISL 위성망에서 출발 위성 (0,0) -> 도착 위성 (5,5)로 패킷을 보내고,
# 라우팅(링크 혼잡도를 보고 다음 방향 선택)으로 경로를 정함.
# 결과로 성능 지표 7개, 애니메이션, 강화학습용 결정 기록을 만듦.
#
# 필요한 패키지: numpy, matplotlib, Pillow
#   설치:  pip install numpy matplotlib pillow
#
# =====================================================================
# 1. 시뮬레이션 돌리는 방법 (VS Code)
# =====================================================================
# (1) VS Code에서 이 폴더(isl_6x6_routing_py) 열기
# (2) main_isl.py 를 열고, 오른쪽 위 ▶ "Run Python File" 버튼 클릭
#     또는 터미널에 입력:  python main_isl.py
# (3) 약 1~2분 기다리기
#     터미널에 아래 두 줄이 찍히고 결과가 나오면 끝
#       [rate60pps_eps0.0] ...   (성능 측정용 실행)
#       [rate60pps_eps0.1] ...   (강화학습 데이터 수집용 실행)
#       결과 저장 완료: ...
#
# =====================================================================
# 2. 결과 확인 방법
# =====================================================================
# 방법 1) 창으로 보기
#   show_results.py 를 열고 ▶ 실행, 또는 터미널에 입력:  python show_results.py
#   -> 지표 표(터미널) + 지표 그래프 창 + 실행 분석 창 + 애니메이션 창이 뜸
#   -> 애니메이션은 창을 닫을 때까지 반복 재생
#   노드 기준으로 보기: python show_node.py        (손실이 가장 많은 노드, ε = 0)
#                       python show_node.py 5 2    (노드 (5,2))
#   -> 노드 36개 요약 표(터미널) + 6x6 요약 지도 창 + 노드 1개 시간 변화 창
#   * show_results.py도 노드 요약 지도와 손실이 가장 많은 노드 그림을 같이 띄움
#
# 방법 2) 파일로 보기 (isl_6x6_routing_py\results 폴더 또는 아래 3번 저장 폴더)
#   metrics_summary.png               : 성능 지표 7개를 실행별 막대로 비교
#   run_analysis.png                  : 실행 분석 (지연 분포, 시간별 변화, 링크 사용량 지도, 홉 수, 선택 유형, 손실 원인)
#   metrics_summary.csv               : 성능 지표 숫자 (엑셀로 열림)
#   anim_rate60pps_eps0.0.gif         : 0~3초 애니메이션 (링크 색 = 큐가 찬 정도, 점 = 이동 중인 패킷)
#   packet_log_*.csv                  : 패킷 1개 = 1줄 (생성 시각, 도착 시각, 결과, 홉 수)
#   decision_log_rate60pps_eps0.1.csv : 라우팅 결정 1번 = 1줄 (강화학습 학습용 데이터)
#   node_log_*.csv                    : 노드 기준 기록 (100 step마다 노드 1개 = 1줄, 큐·보낸 수·손실)
#   node_map_*.png                    : 노드별 요약 지도 (6x6, 평균/최대 큐, 보낸 수, 오버플로, 기한 초과)
#   node_time_*.png                   : 주 흐름 손실이 가장 많은 노드의 시간 변화
#
#   결과 숫자(result) 의미: 1 기한 내 도착, 2 목적지 기한 초과, 3 중간 기한 초과, 4 큐 오버플로, 5 TTL 만료
#
# =====================================================================
# 3. 결과 저장 경로
# =====================================================================
# 시뮬레이션이 끝나면 라우팅 알고리즘 / 시드 종류 / 실행 이름 폴더에 자동 저장됨
#   C:\Users\eun\Desktop\capstone_isl\baseline_py\
#     routeA \ routeB \ routeC                 라우팅 알고리즘 (config_isl.py P.routeName)
#       baseline \ train \ evaluation           시드 종류 (학습용 시드 1~10 -> train, 평가용 101~110 -> evaluation, 그 외 -> baseline)
#         routeB_mid_102\                       라우팅알고리즘_부하단계_시드
#           code\     그때 사용한 .py 파일 전부 (어떤 설정으로 돌렸는지 확인용)
#           results\  이미지(.png, .gif) + CSV + run_info.txt (실행 시각, 부하, 시드)
#         routeB_summary_low-mid-high\          run_experiments.py 여러 시드 요약 (평균 ± 편차)
#   예) main_isl.py 기본 (높음, 시드 1001) -> routeB\baseline\routeB_high_1001
#   * 같은 이름으로 다시 돌리면 같은 이름의 파일은 덮어씀 (실행 시각은 run_info.txt)
#
# 저장 경로 바꾸는 법:
#   save_results.py 맨 위 SAVE_ROOT 한 줄만 수정
#     SAVE_ROOT = r'C:\Users\eun\Desktop\capstone_isl\baseline_py'   <- 본인 PC 경로로 변경
#   * 다른 PC에서는 C:\Users\eun 부분이 다르니 꼭 바꿔야 함
#   * 폴더가 없으면 자동으로 만들어짐
#   * 용량: main_isl.py 한 번 실행에 약 50 MB씩 쌓이니 필요 없는 폴더는 지워도 됨
#
# =====================================================================
# 4. 설정값 바꾸는 법
# =====================================================================
# config_isl.py 만 수정하면 됨 (다른 파일은 건드릴 필요 없음)
#   예) P.genRate = 60        1초마다 생성하는 패킷 수
#       P.packetSize = 160    패킷 크기 (Byte)
#       P.simTime = 600000    총 시뮬레이션 시간 (step, 1 step = 1 ms -> 600000 = 10분)
#       P.k, P.X, P.Y         B 라우팅 가중치 / 임계값
# 배경 트래픽(부하 단계, 시드, 여러 시드 실험 on/off)은 config_bg.py에서 수정
# 수정 후 main_isl.py 다시 실행
# 모든 변수 설명은 variables_isl.py 참고
#
# =====================================================================
# 5. 파일 역할
# =====================================================================
# 직접 실행하는 파일
#   main_isl.py        시뮬레이션 실행 + 결과 저장  (① 이것부터)
#   show_results.py    저장된 결과를 창에 띄움 (② 결과 볼 때)
#   show_node.py       노드 기준 상태를 창에 띄움 (② 노드별로 볼 때)
#   run_experiments.py 부하 단계 x 여러 시드 실험 -> 평균 ± 편차 표 (results/experiments)
# 수정하는 파일
#   config_isl.py      네트워크, 패킷, 라우팅 설정값
#   config_bg.py       배경 트래픽, 부하 단계, 시드, 실험 on/off
# 읽기용 파일
#   README_isl.py      이 안내문
#   simulation_instructions.py  시뮬레이션이 하는 일과 결과 파일 설명
#   variables_isl.py   변수 정리
# 자동으로 불리는 파일 (직접 실행 X)
#   run_isl_sim.py     시뮬레이션 1회 실행
#   route_A.py         A 라우팅 결정 (최단 경로, 부하 무시 - 기준선)
#   route_B.py         B 라우팅 결정 (부하 고려, Liu 단순화)
#   * 어떤 라우팅을 쓸지는 config_isl.py의 P.routeName ('routeA' / 'routeB')
#   build_grid.py      6x6 Grid 생성
#   compute_metrics.py 성능 지표 계산
#   node_log.py        노드 기준 기록 (node_log CSV)
#   plot_nodes.py      노드 그래프 (node_map, node_time PNG / show_node 창)
#   animate_run.py     애니메이션 GIF 저장
#   plot_metrics.py    지표 비교 그래프 PNG 저장
#   plot_analysis.py   실행 분석 그래프 PNG 저장
#   viz_colors.py      그래프 색 모음
#   save_results.py    결과를 저장 경로로 복사
#
# MATLAB 버전과 다른 점
#   * 좌표/패킷 id는 0부터 사용 (MATLAB 내부는 1부터, 기록 파일 숫자는 둘이 같음)
#   * 결과 저장 경로 기본값이 baseline_py (MATLAB 결과와 섞이지 않게)
