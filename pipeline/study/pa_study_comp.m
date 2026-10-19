function T = pa_study_comp(specId, varargin)
%PA_STUDY_COMP  几何补偿"口径一致性"验证
%
%   T = pa_study_comp('W1')
%
%   要证明的事（一条规则 vs 两条规则）
%     全链只有一条几何补偿规则：  g_m = d_m / R
%     · 幅度臂（I_M = Σ g_m |z_m|）                        直接用它
%     · 能量臂 I_E 有两种等价实现（命名见正文 §2.7，统一为 EI / LP）：
%         LP = 直接法（**代码别名 direct**）  I_E^LP = Σ g_m^2 |z_m|^2   （Comp='r2' + 平方律信号）
%         EI = 一致法（**代码别名 consist**） I_E^EI = Σ ( g_m |z_m| )^2 （Comp='r'  + 通道级平方）
%     二者在样本点逐点恒等；样本点之间的差值为**总实现残差**——由 transition-band leakage、
%     边界处理与"插值—平方"先后三项共同承载，**未分离**，实测 ≤0.53 %（max-rel）、L2 ≤0.62 %。
%     => 论文只需写一条补偿律；r^2 不是自由参数，而是同一 g_m 作用在平方量上。
%
%   版本：v1  2026-10-14

opt.Nx       = 601;
opt.Preset   = 'unified';
opt.OutDir   = '';
opt = local_parse(opt, varargin{:});

pipeRoot = fileparts(fileparts(mfilename('fullpath')));
if isempty(opt.OutDir)
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', 'study_comp', specId);
end
if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end

% ---- 载入与预处理（口径与 pa_wire_run 的 BandMode='spec' 一致）----
M = pa_wire_manifest();
i = find(strcmp({M.id}, specId), 1);
assert(~isempty(i), 'pa_study_comp:spec', '未找到 spec %s', specId);
spec = M(i);

cfg = pa_cfg(spec.cfgName, opt.Preset);
sig = pa_load_signals(spec.dataDir, cfg);
if isempty(cfg.nSamples), cfg.nSamples = size(sig, 1); end
D0 = pa_preprocess(sig, cfg);
B  = pa_band_audit(D0.filtered, cfg);

bw = min(cfg.bw_law, 0.95);
cfg.f_low  = max(1e3,              cfg.f0 * (1 - bw/2));
cfg.f_high = min(cfg.nyquist*0.98, cfg.f0 * (1 + bw/2));
B_rf = cfg.f_high - cfg.f_low;
cfg.lp_cutoff = 0.5 * (B_rf + 2*cfg.f_low);
cfg.sqlaw_ok  = (2*cfg.f_low) > B_rf;
D = pa_preprocess(sig, cfg);

fprintf('\n===== %s  补偿口径一致性 =====\n', specId);
fprintf('  [band] f0=%.2f MHz | band [%.2f %.2f] MHz | B=%.2f MHz beta=%.2f | lp=%.2f MHz | ok=%d\n', ...
    cfg.f0/1e6, cfg.f_low/1e6, cfg.f_high/1e6, B_rf/1e6, B_rf/cfg.f0, cfg.lp_cutoff/1e6, cfg.sqlaw_ok);

% ---- 三条路径（同一几何、同一网格、同一插值）----
IM        = pa_backproject(D.env,   cfg, 'Nx',opt.Nx, 'Comp','r',  'Normalize','max');
IE_dir    = pa_backproject(D.sqlaw, cfg, 'Nx',opt.Nx, 'Comp','r2', 'Normalize','max');
IE_cons   = pa_backproject(D.env,   cfg, 'Nx',opt.Nx, 'Comp','r',  'Normalize','max', 'PostSquare',true);

% ---- 比较（在 max 归一化之后；尺度已被归一化消去）----
a = IE_dir(:);  b = IE_cons(:);
relmax = max(abs(a-b)) / (max(a) + eps);
relL2  = norm(a-b) / (norm(a) + eps);
am = a - mean(a);  bm = b - mean(b);
pear   = (am' * bm) / (norm(am) * norm(bm) + eps);
relSE  = norm(a/max(a) - b/max(b))^2 / (norm(a/max(a))^2 + eps);

% —— 关键：直接法与一致法在"能量域"是否同一张图。
%        同时给"包络臂平方（图像域）"作对照，说明通道级平方 ≠ 图像域平方。
IM2 = IM.^2;
im2 = IM2(:);
relSE_img = norm(im2/max(im2) - b/max(b))^2 / (norm(im2/max(im2))^2 + eps);

T = struct('spec', specId, 'relmax', relmax, 'relL2', relL2, ...
           'pearson', pear, 'relSE', relSE, 'relSE_vs_img2', relSE_img);

fprintf('  max|I_E^LP - I_E^EI| / max                  = %.3e\n', relmax);
fprintf('  ||I_E^LP - I_E^EI|| / ||I_E^LP||            = %.3e\n', relL2);
fprintf('  Pearson(I_E^LP , I_E^EI)                    = %.8f\n', pear);
fprintf('  (1 - 相对平方误差) LP vs EI                  = %.8f\n', 1-relSE);
fprintf('  —— 对照：(1 - 相对平方误差) I_M^2 vs I_E^EI = %.6f  (通道级平方 ≠ 图像域平方)\n', 1-relSE_img);

% ---- 出图 ----
fig = figure('Visible','off','Position',[80 80 1180 380]);
subplot(1,3,1); imagesc(IM);        axis image off; colormap(gca, hot); colorbar;
title('I_M = sum (d/R)*|z|','Interpreter','none');
subplot(1,3,2); imagesc(IE_dir);    axis image off; colormap(gca, hot); colorbar;
title('I_E^LP = sum (d/R)^2*|z|^2   (code: direct)','Interpreter','none');
subplot(1,3,3); imagesc(IE_cons);   axis image off; colormap(gca, hot); colorbar;
title('I_E^EI = sum [(d/R)*|z|]^2   (code: consist)','Interpreter','none');
print(fig, fullfile(opt.OutDir, 'study_comp.png'), '-dpng', '-r150');
close(fig);
fprintf('  [out] %s\n', fullfile(opt.OutDir, 'study_comp.png'));

save(fullfile(opt.OutDir, 'study_comp.mat'), '-struct', 'T', '-v7.3');
end

% ==================================================================
function o = local_parse(o, varargin)
if mod(numel(varargin), 2) ~= 0, error('local_parse:pair', '参数必须成对出现。'); end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o, k), error('local_parse:unknown', '未知参数：%s', k); end
    o.(k) = varargin{i+1};
end
end
