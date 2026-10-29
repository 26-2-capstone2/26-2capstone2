function gamma=ituCloudSpecific(fGHz,T_K,liquidDensity_g_m3)
% ITU-R P.840 double-Debye dielectric model, gamma=Kl*M [dB/km].
theta=300/T_K; f=fGHz;
e0=77.66+103.3*(theta-1); e1=.0671*e0; e2=3.52;
fp=20.20-146*(theta-1)+316*(theta-1)^2; fs=39.8*fp;
er=(e0-e1)/(1+(f/fp)^2)+(e1-e2)/(1+(f/fs)^2)+e2;
ei=f*(e0-e1)/(fp*(1+(f/fp)^2))+f*(e1-e2)/(fs*(1+(f/fs)^2));
eta=(2+er)/ei; kl=.819*f/(ei*(1+eta^2));
gamma=kl*liquidDensity_g_m3;
end
