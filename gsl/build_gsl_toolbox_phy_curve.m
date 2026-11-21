function R=build_gsl_toolbox_phy_curve(nPackets)
% Fixed sample size at EVERY Eb/N0 point; no outcome-dependent stopping.
if nargin<1, nPackets=1000; end
validateattributes(nPackets,{'numeric'},{'scalar','integer','>=',100});
root=fileparts(mfilename('fullpath')); out=fullfile(root,'phy_toolbox');
if ~isfolder(out), mkdir(out); end
ebGrid=unique([-24:2:-4 -3:0.5:-1.5 -1:0.25:3 3.5:0.5:5 6:2:16]);
C=gslAR4JACodec(); rows=table();
meta=struct('modulation','Gray QPSK, pi/4','channel','complex AWGN', ...
    'code','CCSDS 131.0-B-5 AR4JA rate 1/2, k=1024', ...
    'decoder',C.algorithm,'maxIterations',C.iterations,'puncturedBits',512, ...
    'packetBytes',160,'padBits',768,'packetErrorRule','any original payload bit incorrect', ...
    'samplesPerSymbol',1,'informationBitsPerModulatedSymbol',1, ...
    'confidence','pointwise 95% Wilson intervals, fixed sample size', ...
    'snrMeaning','curve x is INFORMATION Eb/N0; RF SNR converted by B/Rinfo', ...
    'synchronization','ideal; no Doppler/timing/phase residual, CRC, retransmission', ...
    'MATLAB',version,'seedBase',2026112100,'packetsPerPoint',nPackets, ...
    'standardURL','https://ccsds.org/Pubs/131x0b5.pdf');
fid=fopen(fullfile(out,'metadata.json'),'w'); fprintf(fid,'%s',jsonencode(meta,PrettyPrint=true)); fclose(fid);
for g=1:numel(ebGrid)
    t=tic; errors=0; bits=0; cwErrors=0; n=0;
    while n<nPackets
        count=min(50,nPackets-n);
        S=simulateGSLPHYBatch(ebGrid(g),count,meta.seedBase+10000*g+n);
        errors=errors+S.packetErrors; bits=bits+S.bitErrors;
        cwErrors=cwErrors+S.codewordErrors; n=n+count;
    end
    p=errors/n; z=1.95996398454005; den=1+z^2/n;
    center=(p+z^2/(2*n))/den;
    half=z*sqrt(p*(1-p)/n+z^2/(4*n^2))/den;
    lower=max(0,center-half); upper=min(1,center+half);
    row=table(ebGrid(g),n,errors,p,lower,upper,bits/(1280*n),cwErrors/(2*n),toc(t), ...
        'VariableNames',{'ebNo_dB','packets','packetErrors','PER','PER_lower95', ...
        'PER_upper95','payloadBER','CWER','elapsed_s'});
    rows=[rows;row]; %#ok<AGROW>
    writetable(rows,fullfile(out,'ar4ja_qpsk_awgn_160B.csv'));
    fprintf('PHY %d/%d EbNo=%+.2f PER=%.4f [%0.4f,%0.4f] (%d/%d), %.1f s\n', ...
        g,numel(ebGrid),ebGrid(g),p,lower,upper,errors,n,row.elapsed_s);
end
R=struct('curve',rows,'metadata',meta); save(fullfile(out,'curve.mat'),'R');
plotGSLToolboxPHYCurve(rows,out);
fprintf('TOOLBOX PHY CURVE COMPLETE: %d points\n',height(rows));
end
