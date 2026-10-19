function pa_probe4()
PAI_ROOT = strrep(fileparts(fileparts(mfilename('fullpath'))), '\', '/');
addpath(genpath([PAI_ROOT '/pipeline']));
ids  = {'own1','own2','own4'};
dirs = {'data1','data2','data4'};
for i = 1:numel(ids)
    cfg = pa_cfg(ids{i}, 'own');
    src = [PAI_ROOT '/' dirs{i}];
    sig = pa_load_signals(src, cfg, 'Verbose', false);
    % 只去DC，不滤波，看原始谱
    x = pa_dc_remove(sig, 'median');
    nS = size(x,1); nHalf = floor(nS/2)+1; df = cfg.fs/nS;
    Lg = zeros(nHalf, size(x,2));
    win = hann(nS);
    for k = 1:size(x,2)
        Pk = abs(fft(x(:,k).*win)).^2; Pk = Pk(1:nHalf);
        Lg(:,k) = log(Pk + eps);
    end
    P = exp(median(Lg,2));
    Ps = movmean(P, round(0.25e6/df));
    fq = (0:nHalf-1)'*df; Pn = Ps/max(Ps);
    fprintf('\n===== %s (%s)  [仅去DC，未滤波]\n', ids{i}, dirs{i});
    for f = 0.25:0.25:15
        [~,idx] = min(abs(fq-f*1e6));
        fprintf('  %5.2f MHz %7.2f dB |%s\n', f, 10*log10(Pn(idx)+1e-12), ...
            repmat('=',1,max(0,round(30+10*log10(Pn(idx)+1e-12)))));
    end
end
end
