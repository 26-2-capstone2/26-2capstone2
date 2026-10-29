function gamma=ituGasSpecific(fGHz,T_K,dryPressure_hPa,rho)
% ITU-R P.676-12 Annex 1 spectral summation [dB/km].
% Coefficient tables: weather_data, numerical provenance and license included.
p=dryPressure_hPa; theta=300/T_K; e=rho*T_K/216.7; f=fGHz;
persistent O V
if isempty(O)
    root=fullfile(fileparts(mfilename('fullpath')),'weather_data');
    O=readmatrix(fullfile(root,'gas_oxygen.csv'),'NumHeaderLines',1);
    V=readmatrix(fullfile(root,'gas_water.csv'),'NumHeaderLines',1);
end
fo=O(:,1); a=O(:,2:7);
d=a(:,3)*1e-4.*(p*theta.^(0.8-a(:,4))+1.1*e*theta);
d=sqrt(d.^2+2.25e-6);
delta=(a(:,5)+a(:,6)*theta)*1e-4*(p+e)*theta^.8;
F=f./fo.*((d-delta.*(fo-f))./((fo-f).^2+d.^2)+(d-delta.*(fo+f))./((fo+f).^2+d.^2));
S=a(:,1)*1e-7*p*theta^3.*exp(a(:,2)*(1-theta));
dd=5.6e-4*(p+e)*theta^.8;
Nd=f*p*theta^2*(6.14e-5/(dd*(1+(f/dd)^2))+1.4e-12*p*theta^1.5/(1+1.9e-5*f^1.5));
oxygen=sum(S.*F)+Nd;
fw=V(:,1); b=V(:,2:7);
d=b(:,3)*1e-4.*(p*theta.^b(:,4)+b(:,5)*e.*theta.^b(:,6));
d=.535*d+sqrt(.217*d.^2+2.1316e-12*fw.^2/theta);
F=f./fw.*(d./((fw-f).^2+d.^2)+d./((fw+f).^2+d.^2));
S=b(:,1)*.1*e*theta^3.5.*exp(b(:,2)*(1-theta));
gamma=.182*f*(oxygen+sum(S.*F));
assert(isfinite(gamma) && gamma>=0);
end
