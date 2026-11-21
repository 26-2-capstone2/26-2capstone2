function CFG=configGSLToolboxPHY(CFG)
if nargin<1, CFG=configGSL(); end
CFG.phyModel='TOOLBOX_AR4JA_AWGN';
CFG.phyToolboxCurveFile=fullfile(fileparts(mfilename('fullpath')),'phy_toolbox','ar4ja_qpsk_awgn_160B.csv');
CFG.perModelSource='Toolbox QPSK + CCSDS AR4JA r=1/2 k=1024 | AWGN | BP max 50 | 160 B direct packet tests';
end
