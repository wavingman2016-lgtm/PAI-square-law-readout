function pa_probe_widths()
S = load('results/study_resolution/study_resolution.mat');
ax = S.R1.ax(:)'; pM = S.R1.profM(:)'; pE = S.R1.profE(:)'; pEa = S.R1.profEa(:)';
IBS = S.R1.IM.^2;
[~,i0] = min(abs(ax)); pBS = IBS(i0,:)';

fprintf('peaks: I_M=%.5g  I_E=%.5g  sqrt(I_E)=%.5g  I_M^2=%.5g\n', ...
        max(pM), max(pE), max(pEa), max(pBS));
fprintf('FWHM(I_M)            = %.4f mm\n', wdt(ax,pM,0.5));
fprintf('env -3dB width       = %.4f mm\n', wdt(ax,pM,1/sqrt(2)));
fprintf('env -6dB width       = %.4f mm\n', wdt(ax,pM,0.5));
fprintf('FWHM(I_M^2) [img-sq] = %.4f mm\n', wdt(ax,pBS,0.5));
fprintf('FWHM(I_E)            = %.4f mm\n', wdt(ax,pE,0.5));
fprintf('FWHM(sqrt(I_E))      = %.4f mm\n', wdt(ax,pEa,0.5));
fprintf('I_E 0.25max width    = %.4f mm\n', wdt(ax,pE,0.25));

[~,j] = min(abs(ax));
fprintf('\n   x      I_M       sqrt(I_E)      I_E\n');
for k = j-12:j+12
    fprintf('%6.2f %10.4g %12.4g %12.4g\n', ax(k), pM(k), pEa(k), pE(k));
end
fprintf('\nratio FWHM(I_M^2)/FWHM(I_M)      = %.4f (expect ~ -3dB/-6dB ratio)\n', wdt(ax,pBS,0.5)/wdt(ax,pM,0.5));
fprintf('ratio (-3dB width)/(-6dB width)  = %.4f\n', wdt(ax,pM,1/sqrt(2))/wdt(ax,pM,0.5));
fprintf('ratio FWHM(sqrt(I_E))/FWHM(I_M)  = %.4f (1.0 => no resolution change)\n', wdt(ax,pEa,0.5)/wdt(ax,pM,0.5));
end

function w = wdt(ax, y, lvl)
y = y(:)'; pk = max(y); thr = lvl*pk; i0 = find(y == pk, 1);
L = i0; while L > 1 && y(L) > thr, L = L - 1; end
R = i0; while R < numel(y) && y(R) > thr, R = R + 1; end
w = abs(ax(min(numel(ax),R)) - ax(max(1,L)));
end
