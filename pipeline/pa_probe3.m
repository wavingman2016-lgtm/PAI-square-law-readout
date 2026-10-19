function pa_probe3()
PAI_ROOT = strrep(fileparts(fileparts(mfilename('fullpath'))), '\', '/');
addpath(genpath([PAI_ROOT '/pipeline']));
ids  = {'own1','own2','own4','own3'};
dirs = {'data1','data2','data4','data3'};
for i = 1:numel(ids)
    cfg = pa_cfg(ids{i}, 'unified');
    src = [PAI_ROOT '/' dirs{i}];
    try
        [sig, meta] = pa_load_signals(src, cfg);
    catch e
        fprintf('%-6s LOAD ERR %s\n', ids{i}, e.message); continue
    end
    D = pa_preprocess(sig, cfg);
    x = D.filtered; nS = size(x,1);
    win = hann(nS); P = zeros(floor(nS/2)+1,1);
    for k = 1:size(x,2)
        Pf = abs(fft(x(:,k).*win)).^2; P = P + Pf(1:floor(nS/2)+1);
    end
    P = P/size(x,2); fq = (0:floor(nS/2))'*cfg.fs/nS; Pn = P/max(P);
    fprintf('\n===== %s (%s) nS=%d fs=%.1fMHz rawStd=%.4g rawRange=[%.3g %.3g]\n', ...
        ids{i}, dirs{i}, nS, cfg.fs/1e6, std(sig(:)), min(sig(:)), max(sig(:)));
    for f = 1:20
        [~,idx] = min(abs(fq - f*1e6));
        fprintf('  %5.1f MHz %7.2f dB |%s\n', f, 10*log10(Pn(idx)+1e-12), ...
            repmat('=',1,max(0,round(35+10*log10(Pn(idx)+1e-12)))));
    end
    [~,ipk] = max(P); pdb = 10*log10(P/max(P));
    k=ipk; while k>1 && pdb(k)>-6, k=k-1; end
    k2=ipk; while k2<numel(pdb) && pdb(k2)>-6, k2=k2+1; end
    fprintf('  --> 峰位 %.2f MHz  -6dB [%.2f %.2f] MHz\n', fq(ipk)/1e6, fq(k)/1e6, fq(k2)/1e6);
end
end
