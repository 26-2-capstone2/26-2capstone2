function [gamma,k,alpha]=ituRainSpecific(fGHz,R,el,tau)
% ITU-R P.838-3 eqs 1-5 and Tables 1-4. Instantaneous uniform rain layer.
validateattributes(fGHz,{'numeric'},{'scalar','>=',1,'<=',1000});
validateattributes(R,{'numeric'},{'scalar','nonnegative','finite'});
x=log10(fGHz);
fit=@(a,b,c,m,z)sum(a.*exp(-((x-b)./c).^2))+m*x+z;
kh=10^fit([-5.33980 -.35351 -.23789 -.94158],[-.10008 1.26970 .86036 .64552], ...
    [1.13098 .454 .15354 .16817],-.18961,.71147);
kv=10^fit([-3.80595 -3.44965 -.39902 .50167],[.56934 -.22911 .73042 1.07319], ...
    [.81061 .51059 .11899 .27195],-.16398,.63297);
ah=fit([-.14318 .29591 .32177 -5.37610 16.1721],[1.82442 .77564 .63773 -.96230 -3.29980], ...
    [-.55187 .19822 .13164 1.47828 3.43990],.67849,-1.95537);
av=fit([-.07771 .56727 -.20238 -48.2991 48.5833],[2.33840 .95545 1.14520 .791669 .791459], ...
    [-.76284 .54039 .26809 .116226 .116479],-.053739,.83433);
q=cosd(el).^2*cosd(2*tau);
k=(kh+kv+(kh-kv)*q)/2;
alpha=(kh*ah+kv*av+(kh*ah-kv*av)*q)./(2*k);
gamma=k.*R.^alpha;
end
