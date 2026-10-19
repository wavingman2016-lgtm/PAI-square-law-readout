function pa_smoke()
%_SMOKE  管线冒烟测试（含带宽审计）.仅供开发期使用，不进入交付.
%   用法（无界面）：matlab -batch "cd('<repo root>'); _smoke"

addpath(genpath(fullfile(pwd, 'pipeline')));

sets = { 'own1','data1'; 'own2','data2'; 'own4','data4' };

fprintf('\n=========== 带宽与预处理审计 ===========\n');
for i = 1:size(sets, 1)
    nm = sets{i, 1};  dd = fullfile(pwd, sets{i, 2});
    cfg = pa_cfg(nm);
    fprintf('\n--- %s (%s)  fs=%.0f MHz  vs=%d m/s  f0=%.1f MHz  band=[%.1f %.1f] MHz\n', ...
        nm, sets{i,2}, cfg.fs/1e6, cfg.vs, cfg.f0/1e6, cfg.f_low/1e6, cfg.f_high/1e6);
    sig = pa_load_signals(dd, cfg);
    D   = pa_preprocess(sig, cfg);

    B = pa_band_audit(D.filtered, cfg);
    fprintf('  谱峰 %.2f MHz | -6dB [%.2f %.2f] | 累积5-95%% [%.2f %.2f] | 尖峰=%d\n', ...
        B.f_peak/1e6, B.f_lo6/1e6, B.f_hi6/1e6, B.f05/1e6, B.f95/1e6, B.spurFlag);
    fprintf('  采用 %s : 真实带 [%.2f %.2f] MHz, B=%.2f MHz, 重心 %.2f MHz\n', ...
        B.bandSrc, B.f_lo/1e6, B.f_hi/1e6, B.B_used/1e6, B.fcnt/1e6);
    fprintf('  D2''判据 (B<2*f_low) ? %d   推荐低通 %.2f MHz   合法区间 [%.2f %.2f] MHz\n', ...
        B.ok, B.lp_cutoff/1e6, B.lp_range(1)/1e6, B.lp_range(2)/1e6);

    fprintf('  直流审计: |DC|中位 %.1f, AC rms %.3f, lsb %.3f\n', ...
        median(abs(D.info.dc.dcPerChannel)), ...
        sqrt(mean(D.filtered(:).^2)), ...
        median(diff(unique(sig(:)))));

    % D2' vs D1^2 一致性（超采样抽样，避免全量 corrcoef）
    a = D.sqlaw(:);  b = D.env2(:);
    if std(a) > 0 && std(b) > 0
        idx = randperm(numel(a), min(numel(a), 200000));
        c = corrcoef(a(idx), b(idx));
        fprintf('  Pearson(D2'', D1^2) = %.4f   (比值均值 %.4f)\n', ...
            c(1,2), mean(a(idx))./(mean(b(idx))+eps));
    end
    fprintf('  哨兵修复 %d 点；带通 %.2f-%.2f MHz order %d\n', ...
        D.info.sentinel.nFixedSamples, ...
        D.info.bandpass.f_low/1e6, D.info.bandpass.f_high/1e6, D.info.bandpass.order);
end

fprintf('\n=========== 反投影冒烟（data1, Nx=201）===========\n');
cfg = pa_cfg('own1');
sig = pa_load_signals(fullfile(pwd,'data1'), cfg);
D   = pa_preprocess(sig, cfg);
sigMap = struct('env', D.env, 'env2', D.env2, 'sqlaw', D.sqlaw, 'sq', D.sq);
t0 = tic;
[IMs, grid] = pa_backproject_multi(sigMap, cfg, 'Nx', 201);
fprintf('  反投影耗时 %.1f s ; grid FOV %.1f mm, dx %.4f mm\n', ...
    toc(t0), grid.FOV*1e3, grid.dx);
fn = fieldnames(IMs);
for i = 1:numel(fn)
    IM = IMs.(fn{i});
    [~, li] = max(IM(:));
    [r, c] = ind2sub(size(IM), li);
    fprintf('  %-6s 峰值 @ (%.2f, %.2f) mm  max %.4f  mean %.3e\n', ...
        fn{i}, grid.x(c), grid.y(r), max(IM(:)), mean(IM(:)));
end

fprintf('\n=========== 冒烟测试结束 ===========\n');
end
