# 툴박스 기반 GSL PHY 계산 (2026-11-21)

## 실행

MATLAB 현재 폴더를 이 `gsl` 폴더로 설정한 뒤 실행한다.

```matlab
main_gsl_toolbox_simulation
```

기존과 같은 600초 결과 창·환경감쇠 슬라이더·패킷 번호 재생 창이 열린다. 기본 감쇠는 8 dB다. 배포한 오류율 CSV가 있으므로 매번 신호 실험을 다시 할 필요는 없다. 기존 `main_gsl_simulation`은 기존 JPL 방식으로 유지해 비교할 수 있다.

```matlab
verify_gsl_toolbox_phy         % 무잡음 복원 + 소규모 SNR별 송수신
verify_gsl_toolbox_mapping     % CSV 연결·단위·범위·잘못된 설정 검사
run_gsl_toolbox_phy_comparison % 같은 경로/난수에서 기존/새 PHY, 6·8 dB 비교
compare_gsl_saved_phy_log      % 포함된 과거 8 dB DDQN 로그의 고정 경로 재평가
build_gsl_toolbox_phy_curve(1000) % 표 재측정: 42지점 × 1000패킷
```

기존 RL 환경에서도 `C=configGSLToolboxPHY(configGSL()); env=GSLRLEnvironment([],C);`로 새 PHY를 선택할 수 있다. 이 환경 클래스의 감쇠는 기존처럼 8 dB 상수다. 이 변경은 DDQN 재학습을 수행하지 않는다.

## 계산 방식

- Communications Toolbox의 `ldpcEncode`, `ldpcDecode`, `pskmod`, `pskdemod`, `convertSNR`를 사용한다.
- AR4JA 행렬은 CCSDS 131.0-B-5 7.4절의 식과 표 7-3·7-4로 구성한다. 일반 WLAN LDPC로 대체하지 않는다.
- 정보 1024비트, 내부 부호 2560비트 중 마지막 512비트를 보내지 않는다. 실제 전송은 2048비트여서 부호율은 1/2다. 복호 시 보내지 않은 비트의 LLR은 0이다.
- Gray QPSK, 위상 pi/4, 심볼당 복소 표본 1개, 복소 AWGN, 이상적인 동기·보상 상태다. 복호기는 실수 정밀도 belief propagation, 최대 50회, 패리티 검사 성공 시 조기 종료다. Wireless HDL의 정수 양자화 하드웨어 복호 성능과 동일하다고 주장하지 않는다.
- 패킷 160 B = 1280비트. 1024비트와 256비트로 나누고, 두 번째 블록 뒤에 768개의 0을 채운다. 원본 1280비트 중 하나라도 잘못 복원되면 패킷 오류로 센다. 패딩 비트만 틀린 경우는 패킷 오류에서 제외한다.
- 새 표의 PER은 패킷을 직접 시험한 결과다. `1-(1-CWER)^2`를 다시 적용하지 않는다. CWER은 참고용으로 별도 기록한다.
- 정보율 50 Mbps, 부호화 후 비트율 100 Mbps, QPSK 심볼률 50 Mbaud인 이상적 기준이다. 새 PHY의 패딩 포함 전송 시간은 2048/50e6 = 40.96 us다. 기존의 25.6 us와 다르므로 로그에 반영했다. 수신 처리시간 1 ms는 기존 시스템 가정이며 실제 복호기 실행 시간을 의미하지 않는다.
- 링크 버짓의 SNR(C/N)과 표의 정보 Eb/N0는 `Eb/N0 = SNR + 10log10(B/Rinfo)`로 연결한다. 현재 B=Rinfo=50e6이라 숫자가 같다. 부호율은 변조 신호의 잡음 환산에서 한 번만 반영한다.

## 표의 해석

`phy_toolbox/ar4ja_qpsk_awgn_160B.csv`: Eb/N0 -24~16 dB, 전이 구간은 0.25 dB 간격, 총 42지점, 각 1000패킷의 고정 표본. 원본 payload 53,760,000비트를 시험한다. 점별 PER·BER·CWER·오류 수·시험 수·95% Wilson 구간을 기록한다.

시험에서 0/1000 또는 1000/1000이 나올 수 있다. 이는 관측 비율이며, 참 오류 확률이 정확히 0 또는 1이라는 증명이 아니다. 0/1000의 Wilson 상한은 약 0.383%, 1000/1000의 하한은 약 99.617%다. 높은 SNR의 아주 작은 오류율을 정밀 측정하려면 표본을 더 늘려야 한다.

지점 사이는 PER을 선형 보간한다. 신뢰구간 열의 보간 값은 참고 범위이며, 보간 지점에 대한 별도 통계 검증이나 전체 GSL 손실률의 95% 신뢰구간이 아니다. 표 밖은 임의 0/1로 처리하지 않고 미확정으로 남긴다. 측정 범위 밖의 SNR이나 다른 패킷 크기·부호화 조건은 표를 확장/재측정해야 한다.

## 비교 결과의 범위

`run_gsl_toolbox_phy_comparison`은 기존 main의 고도각 기반 위성 선택(4도 전환 마진)을 그대로 사용하고 PHY만 바꾼 6·8 dB 한 시드 비교다. DDQN 개선 실험이나 학습 완료 결과가 아니다.

`compare_gsl_saved_phy_log(packetCSV)`는 과거 DDQN 실행 로그의 위성 ID·SNR·패킷 난수·핸드오버를 고정한 재평가다. 새 PHY에서 DDQN이 다시 내릴 행동이나 재학습 성능을 의미하지 않는다.

기존 손실률 식과 원인별 합산 검증을 모두 검사한다. 핸드오버 중단 100 ms와 연결 불가 처리, 패킷 번호와 연속 손실 집계는 유지한다. 송수신 전력·거리·환경감쇠의 실제 현장 보정, 잔여 도플러·동기 오류·간섭·재전송은 별도 과제다. 툴박스 사용만으로 현장 성능 검증이 완료되는 것은 아니다.

## 근거

- CCSDS 표준: https://ccsds.org/Pubs/131x0b5.pdf (7.4절)
- MATLAB LDPC: https://www.mathworks.com/help/comm/ref/ldpcdecode.html
- 잡음과 SNR 단위: https://www.mathworks.com/help/comm/ug/awgn-channel.html
- MathWorks AR4JA 블록: https://www.mathworks.com/help/wireless-hdl/ref/ccsdsldpcdecoder.html

이번 표는 명시한 복호기 설정에서 직접 측정했다. JPL 그림과 복호기·패킷 처리 조건이 완전히 같다는 전제는 두지 않는다. `phy_toolbox/metadata.json`에 설정과 난수 시드를 기록했다.
