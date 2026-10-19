function T = pa_supp_equiv(specIds, varargin)
%PA_SUPP_EQUIV  Supplement 图 S1：I_E 两条实现路径 EI 与 LP 的等价性
%
%   T = pa_supp_equiv({'W1','W2','W3'})
%
%   要证明的事（供 Supplement）：
%     正文只写一条补偿律 g_m = d_m / R；I_E 的两种实现逐点等价（命名口径见正文 §2.7）——
%       EI（envelope 包络路，生产默认；**代码别名 consist**）
%              I_E^EI = sum_m ( g_m |z_m| )^2      （Comp='r'  + PostSquare）
%       LP（square-and-low-pass 平方—低通路，免 Hilbert；**代码别名 direct**）
%              I_E^LP = sum_m g_m^2 |z_m|^2        （Comp='r2' + 平方律信号）
%     r^2 不是独立参数，是 g_m 作用在平方量上的自动结果；
%     两者在样本点逐点恒等；样本点之间是**总实现残差**——由 transition-band leakage、
%     边界处理与"插值—平方"先后三项共同承载，**未分离**，实测 ≤0.53 %（max-rel）、L2 ≤0.62 %（QC 不变）。
%     ⚠️ 禁止再用"插值残差"单独指代该差值（归因过窄，见 §2.1/§2.2/§2.7）。
%     ⚠️ 命名口径（R6）：正文一律用 EI / LP（§2.7）。`consist`/`direct` 仅为 pa_wire_run 的
%        `Epath` 取值（**代码别名**），不得再作为图的标签或正文用词。
%
%   产出： results/supp/S1_equiv_<id>.png（4 面板）+ S1_equiv_table.csv（汇总）
%   版本：v1  2026-10-14 ｜ v1.1 2026-10-16（R6：图内标签 EI/LP 对齐 §2.7）

opt.Nx     = 601;
opt.Preset = 'unified';
opt.OutDir = '';
opt = local_parse(opt, varargin{:});

pipeRoot = fileparts(fileparts(mfilename('fullpath')));
if isempty(opt.OutDir)
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', 'supp');
end
if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end

if ischar(specIds), specIds = {specIds}; end
M = pa_wire_manifest();

rows = {};
for s = 1:numel(specIds)
    specId = specIds{s};
    i = find(strcmp({M.id}, specId), 1);
    assert(~isempty(i), 'pa_supp_equiv:spec', '未找到 spec %s', specId);
    spec = M(i);

    % ---- 载入与预处理（与 pa_wire_run 的 BandMode='spec' 同口径）----
    cfg = pa_cfg(spec.cfgName, opt.Preset);
    sig = pa_load_signals(spec.dataDir, cfg);
    if isempty(cfg.nSamples), cfg.nSamples = size(sig, 1); end
    bw = min(cfg.bw_law, 0.95);
    cfg.f_low  = max(1e3,              cfg.f0 * (1 - bw/2));
    cfg.f_high = min(cfg.nyquist*0.98, cfg.f0 * (1 + bw/2));
    B_rf = cfg.f_high - cfg.f_low;
    cfg.lp_cutoff = 0.5 * (B_rf + 2*cfg.f_low);
    cfg.sqlaw_ok  = (2*cfg.f_low) > B_rf;
    D = pa_preprocess(sig, cfg);

    % ---- 三条路径（同一几何 / 网格 / 插值）----
    IM      = pa_backproject(D.env,   cfg, 'Nx',opt.Nx, 'Comp','r',  'Normalize','max');
    IE_dir  = pa_backproject(D.sqlaw, cfg, 'Nx',opt.Nx, 'Comp','r2', 'Normalize','max');
    IE_cons = pa_backproject(D.env,   cfg, 'Nx',opt.Nx, 'Comp','r',  'Normalize','max', 'PostSquare',true);

    % ---- 标量等价指标 ----
    a = IE_dir(:);  b = IE_cons(:);
    relmax = max(abs(a-b)) / (max(a) + eps);
    relL2  = norm(a-b) / (norm(a) + eps);
    am = a - mean(a);  bm = b - mean(b);
    pear = (am' * bm) / (norm(am) * norm(bm) + eps);
    IM2 = IM.^2;  im2 = IM2(:);
    relSE_img = norm(im2/max(im2) - b/max(b))^2 / (norm(im2/max(im2))^2 + eps);

    fprintf('%s: max-rel=%.3e  relL2=%.3e  Pearson=%.8f  1-relSE(img2)=%.6f\n', ...
        specId, relmax, relL2, pear, 1-relSE_img);

    % ---- 剖面：过 EI 峰值中心的一行 ----
    [~, idx] = max(IE_cons(:));
    [r0, c0] = ind2sub(size(IE_cons), idx);
    pd = IE_dir(r0, :);  pc = IE_cons(r0, :);
    pd = pd / max(pd);   pc = pc / max(pc);
    xax = (1:numel(pd)) - c0;

    res = abs(IE_dir - IE_cons) / max(IE_cons(:));

    % ------------------------------------------------------------------
    % v0.22 · C3 取证补充：把「插值顺序」「低通负值」「截断」「归一化」四项
    % 各自量化。此前正文只报 relL2/relmax/Pearson，**没有**负值比例与截断影响，
    % 而 §2.7 的截断条款需要这两个数才不是空话。
    % ------------------------------------------------------------------
    negFrac = mean(D.sqlaw(:) < 0);                        % 有限低通**不保证非负**
    if negFrac > 0
        IE_dir_t = pa_backproject(max(D.sqlaw,0), cfg, 'Nx',opt.Nx, 'Comp','r2', 'Normalize','max');
    else
        IE_dir_t = IE_dir;
    end
    ct = IE_dir_t(:);
    relL2_trunc   = norm(ct - a) / (norm(a) + eps);
    relMax_trunc  = max(abs(ct - a)) / (max(a) + eps);
    % 归一化：平方—低通路的原始记录相对包络平方的比例，理论值 0.5（LPF{x^2}=1/2|z|^2）
    scaleRatio    = mean(D.sqlaw(:)) / (mean(D.env(:).^2) + eps);
    minRec        = min(D.sqlaw(:));

    fprintf(['  [C3] 负值比例=%.4f%%  最小记录值=%.3e  截断后 relL2=%.3e (relmax=%.3e)  ' ...
             '原始幅度比=%.4f (理论 0.5)\n'], ...
            100*negFrac, minRec, relL2_trunc, relMax_trunc, scaleRatio);

    % ---- 4 面板图 ----
    fig = figure('Visible','off','Position',[60 60 1120 820]);
    ax1 = subplot(2,2,1); imagesc(IE_cons); axis image off; colormap(ax1, hot); colorbar(ax1);
    title(ax1, 'I_E^{EI} = \Sigma_m [ g_m |z_m| ]^2   (envelope route)', 'Interpreter','tex');
    ax2 = subplot(2,2,2); imagesc(IE_dir);  axis image off; colormap(ax2, hot); colorbar(ax2);
    title(ax2, 'I_E^{LP} = \Sigma_m g_m^2 |z_m|^2   (square-and-low-pass)', 'Interpreter','tex');
    ax3 = subplot(2,2,3); imagesc(res);     axis image off; colormap(ax3, hot); colorbar(ax3);
    title(ax3, sprintf('|I_E^{LP} - I_E^{EI}| / max   (max = %.2e)', relmax), 'Interpreter','tex');
    ax4 = subplot(2,2,4);
    plot(xax, pc, '-', 'LineWidth', 1.8, 'Color', [0.85 0.15 0.15]); hold(ax4,'on');
    plot(xax, pd, '--', 'LineWidth', 1.6, 'Color', [0.10 0.35 0.80]);
    grid(ax4,'on'); xlabel(ax4,'lateral offset (px)'); ylabel(ax4,'normalized amplitude');
    legend(ax4, {'EI: envelope','LP: square-and-low-pass'}, 'Location','northeast');
    title(ax4, sprintf('profile through peak:  Pearson = %.8f   relL2 = %.1e', pear, relL2), 'Interpreter','tex');

    annotation('textbox', [0.02 0.972 0.96 0.026], 'String', ...
        ['S1 \cdot EI (envelope) \equiv LP (square-and-low-pass): geometric compensation is ONE rule,   ' ...
         '\Sigma_m (g_m|z_m|)^2 \equiv \Sigma_m g_m^2|z_m|^2,   g_m = d_m/R.'], ...
        'Interpreter','tex', 'EdgeColor','none', 'FontSize',10, 'FontWeight','bold', 'HorizontalAlignment','center');
    annotation('textbox', [0.02 0.946 0.96 0.026], 'String', ...
        ['Residual = total implementation residual: transition-band leakage + boundary handling + ' ...
         'interpolation order; one number, NOT separated (Sec. 2.7).'], ...
        'Interpreter','tex', 'EdgeColor','none', 'FontSize',10, 'FontWeight','bold', 'HorizontalAlignment','center');

    outpng = fullfile(opt.OutDir, sprintf('S1_equiv_%s.png', specId));
    print(fig, outpng, '-dpng', '-r150'); close(fig);
    fprintf('  [out] %s\n', outpng);

    rows(end+1,:) = {specId, relmax, relL2, pear, 1-relSE_img, ...
                     negFrac, relL2_trunc, relMax_trunc, scaleRatio}; %#ok<AGROW>
end

% ---- 汇总表 ----
Tt = cell2table(rows, 'VariableNames', {'spec','relmax','relL2','pearson', ...
    'oneMinusRelSE_vs_img2', 'negFrac_sqlaw', 'relL2_after_trunc', ...
    'relMax_after_trunc', 'scale_ratio_sqlaw_over_env2'});
writetable(Tt, fullfile(opt.OutDir, 'S1_equiv_table.csv'));
fprintf('  [out] %s\n', fullfile(opt.OutDir, 'S1_equiv_table.csv'));
T = Tt;
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
