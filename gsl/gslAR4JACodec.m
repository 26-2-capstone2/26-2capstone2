function C=gslAR4JACodec()
% CCSDS 131.0-B-5 section 7.4: rate 1/2, k=1024, M=512.
% Full graph: 2560 variables; last 512 punctured; 2048 transmitted.
% Standard source: https://ccsds.org/Pubs/131x0b5.pdf (tables 7-3/7-4).
persistent cached
if ~isempty(cached), C=cached; return; end
M=512; q=M/4; i=(0:M-1).'; j=floor(i/q);
theta=[3 0 1 2 2 3 0 1];
phi=[16 0 0 0;103 53 8 35;105 74 119 97;0 45 89 112; ...
     50 47 31 64;29 0 122 93;115 59 1 99;30 102 69 94];
P=cell(1,8);
for k=1:8
    col=q*mod(theta(k)+j,4)+mod(phi(k,j+1).'+i,q);
    assert(numel(unique(col))==M);
    P{k}=sparse(i+1,col+1,1,M,M);
end
I=speye(M); Z=sparse(M,M);
H=mod([Z Z I Z I+P{1}; I I Z I P{2}+P{3}+P{4}; ...
       I P{5}+P{6} Z P{7}+P{8} I],2)~=0;
assert(isequal(size(H),[1536 2560]) && nnz(H)==7680);
enc=ldpcEncoderConfig(H);
dec=ldpcDecoderConfig(H,'bp');
assert(enc.NumInformationBits==1024);
C=struct('H',H,'encoder',enc,'decoder',dec,'informationBits',1024, ...
    'transmittedBits',2048,'puncturedBits',512,'iterations',50, ...
    'algorithm','belief propagation','codeRate',0.5);
cached=C;
end
