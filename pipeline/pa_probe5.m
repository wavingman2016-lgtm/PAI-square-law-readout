function pa_probe5()
PAI_ROOT = strrep(fileparts(fileparts(mfilename('fullpath'))), '\', '/');
%PA_PROBE5  只读频谱审计：own3(data3) / own5(data5) / own6(data6)
%
%   目的：在跑统一管线之前，先量出每个旋转扫描数据集的**真实频谱峰与 -6dB 带**，
%   用来判定 cfg 里的标称 f0 是否与实际信号带相符（data6 曾因标称 5 MHz 而实测
%   1.06 MHz 被整段滤掉，见 docs/10 §3）。
%
%   与 pa_probe4 同法：仅去直流（median），不滤波，看**原始谱**。
%   旋转扫描数据量大，用 Stride 抽角（抽角不影响频谱形状）。
%
%   本脚本只读，不写任何数据文件。
addpath(genpath([PAI_ROOT '/pipeline']));

ids   = {'own3',   'own5',   'own6'};
dirs  = {'data3',  'data5',  'data6'};
strid = [1,        4,        4];

for i = 1:numel(ids)
    cfg = pa_cfg(ids{i}, 'own');
    src = [PAI_ROOT '/' dirs{i}];
    t0 = tic;
    sig = pa_load_signals(src, cfg, 'Stride', strid(i), 'Verbose', false);
    x = pa_dc_remove(sig, 'median');

    nS = size(x,1); nHalf = floor(nS/2)+1; df = cfg.fs/nS;
    Lg = zeros(nHalf, size(x,2));
    win = hann(nS);
    for k = 1:size(x,2)
        Pk = abs(fft(x(:,k).*win)).^2; Pk = Pk(1:nHalf);
        Lg(:,k) = log(Pk + eps);
    end
    P  = exp(median(Lg,2));
    Ps = movmean(P, max(1,round(0.05e6/df)));
    fq = (0:nHalf-1)'*df;  Pn = Ps/max(Ps);

    fprintf('\n===== %s (%s)  nS=%d  ch=%d  fs=%.1f MHz  stride=%d  (%.1f s)\n', ...
        ids{i}, dirs{i}, nS, size(x,2), cfg.fs/1e6, strid(i), toc(t0));
    fprintf('  DC 中位数=%.4g  AC 中位数=%.4g  min=%.4g  max=%.4g\n', ...
        median(sig(:)), median(abs(sig(:)-median(sig(:)))), min(sig(:)), max(sig(:)));

    [~, ipk] = max(P);
    pdb = 10*log10(P/max(P));
    k1 = ipk; while k1>1        && pdb(k1)>-6, k1 = k1-1; end
    k2 = ipk; while k2<numel(pdb) && pdb(k2)>-6, k2 = k2+1; end
    fprintf('  --> 谱峰 %.3f MHz | -6dB 带 [%.3f, %.3f] MHz | 带宽 %.3f MHz | beta=B/f0nom(5MHz)=%.2f\n', ...
        fq(ipk)/1e6, fq(k1)/1e6, fq(k2)/1e6, (fq(k2)-fq(k1))/1e6, (fq(k2)-fq(k1))/5e6);
    fprintf('  --> 频率一致性 f_peak/f0nominal(5.00 MHz) = %.2f  %s\n', ...
        fq(ipk)/5e6, ternary(fq(ipk)/5e6 >= 0.5 && fq(ipk)/5e6 <= 2.0, 'OK', '**FAIL Q8**'));

    fgrid = 0.5:0.5:min(12, cfg.fs/2/1e6);
    for f = fgrid
        [~, idx] = min(abs(fq - f*1e6));
        fprintf('   %5.1f MHz %7.2f dB |%s\n', f, 10*log10(Pn(idx)+1e-12), ...
            repmat('=', 1, max(0, round(30+8*10*log10(Pn(idx)+1e-12)))));
    end
end
end

function s = ternary(c, a, b)
if c, s = a; else, s = b; end
end
