% 그래프 색 모음 - 모든 결과 그래프가 같은 색을 쓰도록 한 곳에서 정함
%
function C = viz_colors()
% 실행(시리즈) 색: 고정 순서 1 파랑, 2 주황, 3 청록, 4 노랑 (색약 구분 검증된 순서)
C.series = hex2rgb({'#2a78d6', '#eb6834', '#1baf7a', '#eda100'});
% 링크 사용량 (적음 -> 많음, 파랑 한 가지 색의 명암)
C.seqLow = hex2rgb({'#dbe9fa'});
C.seqHigh = hex2rgb({'#0d3a73'});
C.unused = hex2rgb({'#e6e5e0'});
% 글자 / 축 / 격자
C.text = hex2rgb({'#0b0b0b'});
C.muted = hex2rgb({'#52514e'});
C.axis = hex2rgb({'#8a8984'});
C.grid = hex2rgb({'#e6e5e0'});
C.font = 'Malgun Gothic';
end

function rgb = hex2rgb(hexList)
rgb = zeros(numel(hexList), 3);
for i = 1:numel(hexList)
    h = hexList{i};
    rgb(i, :) = [hex2dec(h(2:3)), hex2dec(h(4:5)), hex2dec(h(6:7))] / 255;
end
end
