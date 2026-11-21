function bits=gslPacketInformationBits(CFG)
% Link data rate is the information bit rate. Include AR4JA fill bits once.
bits=CFG.packetSize_bytes*8;
if isfield(CFG,'phyModel') && strcmp(CFG.phyModel,'TOOLBOX_AR4JA_AWGN')
    bits=ceil(bits/1024)*1024;
end
end
