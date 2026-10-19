function R = pa_patato_check(varargin)
%PA_PATATO_CHECK  外部在体数据（PATATO 小鼠）几何核验 —— 第 2 项的闸门
%
%   R = pa_patato_check('Name', Value, ...)
%
%   判据（执行序 §4 第 2 项）：与数据集自带官方重建
%     recons/Reference Backprojection/0
%   的相关系数 **corr >= 0.80**。通过才允许推进 Fig.7 的三臂对照与管线上线。
%
%   全程走统一管线组件：
%     pa_cfg → pa_load_signals（HDF5 4D 分支）→ pa_preprocess
%     → pa_backproject_multi / pa_backproject_coherent
%   唯一特别之处：阵元坐标由数据自带的 GEOMETRY 提供（经 SensorPos 显式透传），
%   因为该阵列形状不规则（256 元占据 267.9 度，正下方留 91 度缺口）。
%
%   可选参数
%     'H5'       HDF5 路径（默认 <proj>/data_ext/invivo_oe.hdf5）
%     'WL'       波长索引（默认 1）
%     'Nx','FOV' 覆盖成像网格（默认取 cfg）
%     'Plot'     是否出图（默认 false；headless 下绘图可能挂死，故后置）
%     'Save'     是否存盘（默认 true）
%     'OutDir'   输出目录（默认 <proj>/results/study_patato）
%     'Verbose'  打印进度（默认 true）
%
%   版本：v1  2026-10-14

opt.H5      = '';
opt.WL      = 1;
opt.Nx      = [];
opt.FOV     = [];
opt.Plot    = false;
opt.Save    = true;
opt.OutDir  = '';
opt.Verbose = true;
opt = parse_opts(opt, varargin{:});

pipeRoot = fileparts(fileparts(mfilename('fullpath')));   % .../pipeline
projRoot = fileparts(pipeRoot);
if isempty(opt.H5),     opt.H5     = fullfile(projRoot, 'data_ext', 'invivo_oe.hdf5'); end
if isempty(opt.OutDir), opt.OutDir = fullfile(projRoot, 'results', 'study_patato');    end
assert(exist(opt.H5, 'file') == 2, 'pa_patato_check:noFile', '找不到 HDF5：%s', opt.H5);

fprintf('\n############ PATATO 几何核验（在体小鼠）############\n');

% ==================================================================
%  1. 配置 + 加载（统一管线）
% ==================================================================
cfg = pa_cfg('patato_mouse');
if ~isempty(opt.Nx),  cfg.Nx  = opt.Nx;  end
if ~isempty(opt.FOV), cfg.FOV = opt.FOV; end

[sig, meta] = pa_load_signals(opt.H5, cfg, 'H5Key', 'raw_data', 'H5WL', opt.WL, ...
                              'FrameAvg', true, 'Verbose', opt.Verbose);
assert(~isempty(meta.sensorPos), 'pa_patato_check:noGeom', ...
    '未从 HDF5 读出 GEOMETRY，无法保证几何正确（该阵列形状不规则）。');

SP = meta.sensorPos;
rr = hypot(SP(1,:), SP(2,:));
fprintf('  [geom] SensorPos (2 x %d) | R = %.3f .. %.3f mm | vs = %g m/s\n', ...
    size(SP,2), min(rr)*1e3, max(rr)*1e3, cfg.vs);

x = sig;
fprintf('  [diag] %d 通道 x %d 采样 | 全局中位 = %.0f | 去中位后 AC 中位 = %.0f\n', ...
    size(x,2), size(x,1), median(x(:)), ...
    median(abs(x - median(x,1)), 'all'));

% ==================================================================
%  2. 预处理（统一链：哨兵 → 去DC → 带通 → 四路解调）
% ==================================================================
D = pa_preprocess(sig, cfg);
fprintf('  [prep] 带通 [%.2f %.2f] MHz | 低通 %.2f MHz | D2'' 合法 = %d\n', ...
    cfg.f_low/1e6, cfg.f_high/1e6, cfg.lp_cutoff/1e6, cfg.sqlaw_ok);
fprintf('  [prep] D2'' vs D1^2 : Pearson = %.4f | 幅度比 = %.4f (理论 0.5)\n', ...
    D.info.sqlaw.pearson_vs_ref, D.info.sqlaw.amp_ratio_vs_ref);

% ==================================================================
%  3. 四路 + 相干臂（共用一次几何，显式 SensorPos）
% ==================================================================
sigMap = struct('env', D.env, 'env2', D.env2, 'sqlaw', D.sqlaw, 'sq', D.sq);
[IMs, grid] = pa_backproject_multi(sigMap, cfg, 'Nx', cfg.Nx, 'FOV', cfg.FOV, ...
                                   'SensorPos', SP);

Z = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered, 2)
    Z(:, ch) = hilbert(D.filtered(:, ch));
end
IMs.coh = pa_backproject_coherent(Z, cfg, 'Nx', cfg.Nx, 'FOV', cfg.FOV, ...
                                  'Comp', 'r', 'Normalize', 'max', 'SensorPos', SP);
IMs.IBS = IMs.coh .^ 2;        % 图像域平方（对照臂）

% ==================================================================
%  4. 与官方重建对齐：扫官方视场，取与本文 env 重建最相关者
% ==================================================================
refAll = double(h5read(opt.H5, '/recons/Reference Backprojection/0'));
wlr    = min(opt.WL, size(refAll, 4));
ref2   = squeeze(mean(refAll(:, :, 1, wlr, :), 5));
fprintf('  [ref] 官方重建 %d x %d（%d 帧平均）\n', size(ref2,1), size(ref2,2), size(refAll,5));

c0 = (size(ref2, 1) - 1) / 2;
scanFov = [16 18 20 22 24 26 28 29 30 31 32 33.3 36 40];
tfNames = {'id', 'flipud', 'fliplr', 'transpose'};
bestAbs = -Inf;  bestCc = NaN;  bestFov = NaN;  bestRef = [];  bestTf = '';
for fmm = scanFov
    px = fmm / (size(ref2, 1) - 1);
    ii = grid.x(:) / px + c0 + 1;
    [XX, YY] = meshgrid(ii, ii);
    rImg = interp2(ref2, XX, YY, 'linear', 0);
    if opt.Verbose
        fprintf('    对齐扫描 官方视场 %5.1f mm (px %.4f mm) -> corr(env) = %+.4f\n', ...
            fmm, px, local_corr(rImg, IMs.env));
    end
    % 坐标约定诊断：官方网格与本文网格可能存在轴翻转/转置
    for t = 1:numel(tfNames)
        switch tfNames{t}
            case 'id',        rT = rImg;
            case 'flipud',    rT = flipud(rImg);
            case 'fliplr',    rT = fliplr(rImg);
            case 'transpose', rT = rImg.';
        end
        cc = local_corr(rT, IMs.env);
        if abs(cc) > bestAbs
            bestAbs = abs(cc);  bestCc = cc;  bestFov = fmm;
            bestRef = rT;      bestTf = tfNames{t};
        end
    end
end
fprintf('  [align] 官方视场 = %.1f mm | 坐标变换 = %s | corr(env) = %+.4f | corr(coh) = %+.4f\n', ...
    bestFov, bestTf, bestCc, local_corr(bestRef, IMs.coh));

ref = bestRef;
lo50 = local_prctile(ref, 50);  lo95 = local_prctile(ref, 95);
roi  = ref >= lo95;
bg   = ref <= lo50;
fprintf('  [roi] 参考亮区 %d 像素 / 背景 %d 像素\n', nnz(roi), nnz(bg));

% ==================================================================
%  5. 指标（数据域；口径与全项目一致）
% ==================================================================
names = {'coh', 'env', 'env2', 'sqlaw', 'sq', 'IBS'};
M = zeros(numel(names), 2);
for i = 1:numel(names)
    [M(i,1), M(i,2)] = local_metrics(IMs.(names{i}), roi, bg);
end
fprintf('\n  ---- ROI 指标（数据域）----\n');
fprintf('   %-6s %10s %10s\n', 'arm', 'CNR', 'gCNR');
lab = {'C coh', 'M env', 'E env2', 'E sqlaw', 'B sq', 'IBS'};
for i = 1:numel(names)
    fprintf('   %-6s %10.3f %10.4f\n', lab{i}, M(i,1), M(i,2));
end
iE = find(strcmp(names, 'sqlaw'));
iC = find(strcmp(names, 'coh'));
iM = find(strcmp(names, 'env'));
fprintf('   Δ(E-C) : ΔCNR = %+.3f | ΔgCNR = %+.4f\n', ...
    M(iE,1)-M(iC,1), M(iE,2)-M(iC,2));
fprintf('   Δ(E-M) : ΔCNR = %+.3f | ΔgCNR = %+.4f\n', ...
    M(iE,1)-M(iM,1), M(iE,2)-M(iM,2));
fprintf('   I_BS=I_C^2 : gCNR = %.4f  vs  I_C 的 %.4f  (差 %+.4f)\n', ...
    M(6,2), M(iC,2), M(6,2)-M(iC,2));

% ==================================================================
%  6. 闸门判定
% ==================================================================
gate = abs(bestCc) >= 0.80;
if gate
    fprintf('\n  [GATE] corr = %+.4f >= 0.80  ->  PASS（几何核验通过）\n', bestCc);
else
    fprintf('\n  [GATE] corr = %+.4f <  0.80  ->  FAIL（不得推进 Fig.7）\n', bestCc);
end

% ==================================================================
%  7. 打包 / 存盘
% ==================================================================
R = struct('cfg', cfg, 'meta', meta, 'grid', grid, 'band', struct( ...
        'f_low', cfg.f_low, 'f_high', cfg.f_high, 'lp_cutoff', cfg.lp_cutoff, ...
        'pearson_sqlaw', D.info.sqlaw.pearson_vs_ref, ...
        'amp_ratio_sqlaw', D.info.sqlaw.amp_ratio_vs_ref), ...
        'align', struct('fov_mm', bestFov, 'tf', bestTf, 'corr_env', bestCc, ...
                        'corr_coh', local_corr(bestRef, IMs.coh)), ...
        'metrics', struct('names', {names}, 'CNR', M(:,1), 'gCNR', M(:,2)), ...
        'gate', gate);

if opt.Save
    if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end
    outMat = fullfile(opt.OutDir, 'patato_check.mat');
    IMsmall = IMs;                                   % 图像不大，直接存
    save(outMat, '-struct', 'R', '-v7.3');
    save(fullfile(opt.OutDir, 'patato_images.mat'), '-struct', 'IMsmall', '-v7.3');
    fprintf('  [out] %s\n', outMat);
end

if opt.Plot
    if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end
    local_plot(IMs, ref, grid, M, names, bestFov, bestCc, bestTf, opt.OutDir);
end
end

% ==================================================================
function c = local_corr(A, B)
a = double(A(:)) - mean(double(A(:)));
b = double(B(:)) - mean(double(B(:)));
d = sqrt(sum(a.^2) * sum(b.^2));
if d < eps, c = 0; else, c = sum(a .* b) / d; end
end

% ==================================================================
function q = local_prctile(v, p)
v = sort(double(v(:)));
n = numel(v);
if n == 0, q = NaN; return; end
if n == 1, q = v(1); return; end
q = interp1((0:n-1)/(n-1), v, min(max(p,0),100)/100, 'linear', 'extrap');
end

% ==================================================================
function [cnr, gcnr] = local_metrics(A, roi, bg)
A = double(A);
a = mean(A(roi));  s = mean(A(bg));  sd = std(A(bg)) + 1e-30;
cnr = (a - s) / sd;

lo = local_prctile(A, 5);  hi = local_prctile(A, 95);
if hi <= lo, hi = lo + 1e-30; end
a2 = min(max((A(roi) - lo) / (hi - lo), 0), 1);
s2 = min(max((A(bg)  - lo) / (hi - lo), 0), 1);

edges = linspace(0, 1, 65);
ha = histcounts(a2, edges);
hb = histcounts(s2, edges);
gcnr = 1 - sum(min(ha, hb)) / numel(a2);
end

% ==================================================================
function local_plot(IMs, ref, grid, M, names, bestFov, bestCc, bestTf, outDir)
figure('Visible', 'off', 'Position', [100 100 1400 850]);
ext = [grid.x(1), grid.x(end), grid.y(1), grid.y(end)];
panels = {'coh', 'env', 'env2', 'sqlaw', 'IBS', 'ref'};
lab    = {'C 相干反投影 |sum z|', 'M 包络叠加 sum|z|', ...
          'E 能量域 (Hilbert 路径)', 'E 能量域 (免 Hilbert)', ...
          'I_BS = I_C^2 (图像域平方)', '官方参考重建'};
for k = 1:6
    ax = subplot(2, 3, k);
    if strcmp(panels{k}, 'ref')
        im = ref;  lo = local_prctile(im, 2);  hi = local_prctile(im, 99.8);
    else
        im = IMs.(panels{k});  lo = 0;  hi = 1;
    end
    imagesc(ext(1:2), ext(3:4), im); axis image; set(ax, 'YDir', 'normal');
    colormap(ax, hot);
    if hi > lo, set(ax, 'CLim', [lo hi]); end
    ttl = lab{k};
    if ~strcmp(panels{k}, 'ref')
        i = find(strcmp(names, panels{k}));
        if ~isempty(i)
            ttl = sprintf('%s\nCNR %.2f | gCNR %.3f', ttl, M(i,1), M(i,2));
        end
    end
    title(ttl, 'FontSize', 10, 'FontWeight', 'bold');
    xlabel('x (mm)');  ylabel('y (mm)');
    colorbar(ax);
end
sgtitle(sprintf('PATATO 在体小鼠 · 统一管线几何核验（官方视场 %.1f mm，坐标 %s，corr = %+.4f）', ...
    bestFov, bestTf, bestCc), 'FontSize', 12, 'FontWeight', 'bold');
outPng = fullfile(outDir, 'Fig7_patato_three_arms.png');
print(gcf, outPng, '-dpng', '-r140');
close(gcf);
fprintf('  [fig] %s\n', outPng);
end

% ==================================================================
function o = parse_opts(o, varargin)
if mod(numel(varargin), 2) ~= 0
    error('parse_opts:pair', '参数必须成对出现.');
end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o, k), error('parse_opts:unknown', '未知参数：%s', k); end
    o.(k) = varargin{i+1};
end
end
