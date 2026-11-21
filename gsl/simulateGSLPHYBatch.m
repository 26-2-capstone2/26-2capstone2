function S=simulateGSLPHYBatch(ebNo_dB,nPackets,seed)
% Ideal synchronized QPSK, complex AWGN, soft BP decoding, no ARQ/CRC.
% 160 B payload -> 1024 + 256 bits; zero fill to two information blocks.
% Only the original 1280 payload bits determine packet success.
stream=RandStream('mt19937ar','Seed',seed);
C=gslAR4JACodec(); K=C.informationBits;
payload=randi(stream,[0 1],1280,nPackets,'int8');
blocks=reshape([payload;zeros(768,nPackets,'int8')],K,2*nPackets);
fullCode=ldpcEncode(blocks,C.encoder);
assert(~any(mod(C.H*double(fullCode),2),'all'),'GSL:InvalidAR4JACodeword');
tx=pskmod(double(fullCode(1:2048,:)),4,pi/4,'gray','InputType','bit');
if isinf(ebNo_dB) && ebNo_dB>0
    llrTx=40*(1-2*double(fullCode(1:2048,:)));
    noiseVariance=0;
else
    % Information Eb/N0 -> Es/N0 at one complex sample/symbol.
    sampleSNR=convertSNR(ebNo_dB,'ebno','snr','BitsPerSymbol',2,'CodingRate',0.5);
    noiseVariance=10.^(-sampleSNR/10); % E|symbol|^2=1
    noise=sqrt(noiseVariance/2)*(randn(stream,size(tx))+1i*randn(stream,size(tx)));
    rx=tx+noise;
    llrTx=pskdemod(rx,4,pi/4,'gray','OutputType','llr','NoiseVariance',noiseVariance);
end
llr=[llrTx;zeros(512,2*nPackets)]; % puncturing means NO evidence, not a known zero
[decoded,iters]=ldpcDecode(llr,C.decoder,C.iterations,'Termination','early');
decodedPackets=reshape(decoded,2048,nPackets);
wrong=decodedPackets(1:1280,:)~=payload;
blockWrong=any(decoded~=blocks,1);
S=struct('packets',nPackets,'packetErrors',sum(any(wrong,1)), ...
    'bitErrors',sum(wrong,'all'),'codewords',2*nPackets, ...
    'codewordErrors',sum(blockWrong),'meanIterations',mean(iters), ...
    'noiseVariance',noiseVariance);
end
