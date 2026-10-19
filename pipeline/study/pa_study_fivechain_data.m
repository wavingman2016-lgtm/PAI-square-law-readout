function R = pa_study_fivechain_data(varargin)
%PA_STUDY_FIVECHAIN_DATA  自有六数据集的五链（C/M/EH/EL/SQ）重分析
%
%   目的
%     按 docs/15_五链冻结与后续实验规划_v0.33.md 第 4 节，在**不改动任何采集**
%     的前提下，把六组自有数据统一重建成五条链，并输出形态/检测指标。
%
%   五链（见 docs/15 §2.1）
%     C  : |sum_m g_m z_m|                解析信号相干反投影           Comp='r'
%     M  : sum_m g_m A_m                  包络堆叠                     Comp='r'
%     EH : sum_m g_m^2 A_m^2              Hilbert 平方包络             Comp='r2'
%     EL : sum_m g_m^2 q_m, q=2LPF{x^2}   平方—低通（主方法）          Comp='r2'
%     SQ : sum_m g_m^2 x_m^2              裸平方（消融）               Comp='r2'
%
%   ⚠️ 与 pa_wire_run 默认路径的差别
%     pa_wire_run 在 Epath='consist' 时把 IMs.sqlaw 覆盖成 g^2 A^2（= EH），
%     归档结果中**没有真正的 EL**。本脚本显式用 D.sqlaw 算 EL，不做覆盖。
%
%   输出
%     results/fivechain/fivechain_data.csv   长表：dataset,arm,metric,value,unit
%     results/fivechain/fivechain_data.mat   指标 + 裁剪图（供出图）
%
%   用法
%     pa_study_fivechain_data()
%     pa_study_fivechain_data('IDs',{'W1','W2'})
%
%   版本：v1  2026-10-18

opt.IDs        = {'W1','W2','W3','W4','W5','W6'};
opt.OutDir     = '';
opt.Save       = true;
opt.PatchHalf  = 100;      % 裁剪半径（像素）
opt.NxOverride = [];       % 非空则强制覆盖所有数据集的网格（网格局限性核查用）
opt.Verbose    = true;
opt = parse_opts(opt, varargin{:});

root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
if isempty(opt.OutDir), opt.OutDir = fullfile(root, 'results', 'fivechain'); end
if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end

addpath(fullfile(root, 'pipeline', 'config'));
addpath(fullfile(root, 'pipeline', 'preprocess'));
addpath(fullfile(root, 'pipeline', 'recon'));
addpath(fullfile(root, 'pipeline', 'wire'));

M = pa_wire_manifest('Root', root);

% ---- 长表缓冲 ----
rows = struct('dataset', {}, 'arm', {}, 'metric', {}, 'value', {}, 'unit', {});

R = struct();
R.rows   = rows;
R.patches = struct();
R.profiles = struct();
R.meta   = struct();

for k = 1:numel(M)
    spec = M(k);
    if ~any(strcmpi(opt.IDs, spec.id)), continue; end

    if opt.Verbose
        fprintf('\n######## %s : %s ########\n', spec.id, spec.desc);
    end

    % ---- 1. 配置（复刻 pa_wire_run 的 BandMode='spec' 逻辑）----
    cfg = pa_cfg(spec.cfgName, 'unified');
    if ~isempty(spec.F0), cfg.f0_nominal = spec.F0; else, cfg.f0_nominal = cfg.f0; end
    cfg.f0 = cfg.f0_nominal;
    bw = min(cfg.bw_law, 0.95);
    cfg.f_low  = max(1e3,              cfg.f0 * (1 - bw/2));
    cfg.f_high = min(cfg.fs/2*0.98,    cfg.f0 * (1 + bw/2));
    B_rf = cfg.f_high - cfg.f_low;
    cfg.beta_rf      = B_rf / max(cfg.f0, eps);
    cfg.sqlaw_lo_cut = B_rf;
    cfg.sqlaw_hi_cut = 2 * cfg.f_low;
    cfg.sqlaw_ok     = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;
    if cfg.sqlaw_ok
        cfg.lp_cutoff = 0.5 * (cfg.sqlaw_lo_cut + cfg.sqlaw_hi_cut);
    else
        cfg.lp_cutoff = cfg.f0;
    end
    cfg.sqlaw_narrowband = [cfg.f_low, cfg.f_high];

    Nx  = 601;  if ~isempty(spec.Nx),  Nx  = spec.Nx;  end
    if ~isempty(opt.NxOverride), Nx = opt.NxOverride; end   % 网格敏感性核查
    FOV = cfg.FOV; if ~isempty(spec.FOV), FOV = spec.FOV; end

    % ---- 2. 加载 + 预处理 ----
    [sig, ldmeta] = pa_load_signals(spec.dataDir, cfg, 'Verbose', false);
    if isempty(cfg.nSamples), cfg.nSamples = size(sig,1); end
    SensorPos = [];
    if isfield(ldmeta,'sensorPos'), SensorPos = ldmeta.sensorPos; end

    D = pa_preprocess(sig, cfg, 'Methods', {'env','env2','sqlaw','sq'});
    if numel(unique(sig(:))) < 10
        warning('%s: 数据疑似为空', spec.id);
    end

    % ---- 3. 五链反投影（共享几何/网格/插值）----
    Z = complex(zeros(size(D.filtered)));
    for ch = 1:size(D.filtered,2)
        Z(:,ch) = hilbert(D.filtered(:,ch));
    end

    I = struct();
    [IC, grid] = pa_backproject_coherent(Z, cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r','Normalize','max','SensorPos',SensorPos);
    I.C = IC;
    I.M  = pa_backproject(D.env,   cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r', 'Normalize','max','SensorPos',SensorPos);
    I.EH = pa_backproject(D.env2,  cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r2','Normalize','max','SensorPos',SensorPos);
    I.EL = pa_backproject(D.sqlaw, cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r2','Normalize','max','SensorPos',SensorPos);
    I.SQ = pa_backproject(D.sq,    cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r2','Normalize','max','SensorPos',SensorPos);

    % ---- 4. 参考位置：由 C 定义（ROI 不随方法调整）----
    [~, imax] = max(I.C(:));
    [iy0, ix0] = ind2sub(size(I.C), imax);
    axx = grid.x;  axy = grid.y;
    x0 = axx(ix0);  y0 = axy(iy0);

    % ---- 5. 逐链指标 ----
    arms = {'C','M','EH','EL','SQ'};
    profLat = struct(); profAxi = struct();
    for a = 1:numel(arms)
        A = arms{a};  img = I.(A);

        % 剖面：过参考位置的行/列（所有链同一条线）
        pLat = img(iy0, :).';          % 横向（沿 x）
        pAxi = img(:, ix0);            % 轴向（沿 y）
        profLat.(A) = pLat;  profAxi.(A) = pAxi;

        % 峰（在参考位置 ±2 mm 内搜索，避免远处伪影）
        [pkLat, iLat] = local_peak_near(pLat, axx, x0, 2.0);
        [pkAxi, iAxi] = local_peak_near(pAxi, axy, y0, 2.0);

        % 表观 FWHM（各自峰值的半高）
        wLat = local_width(axx, pLat, 0.5);
        wAxi = local_width(axy, pAxi, 0.5);
        % 一阶矩宽度（稳健补充）
        mLat = local_moment_width(axx, pLat);
        mAxi = local_moment_width(axy, pAxi);

        % 10-90% 上升宽度（左翼；仅形态描述，不称 edge-spread）
        fLat = local_flank_10_90(axx, pLat);

        % 旁瓣比与双峰
        pslrLat = local_pslr(pLat);
        [nPk, dipDepth] = local_multi_peak(pLat);

        % 2D gCNR / CNR / PSR
        [g2, cnr2, psr2, nb] = local_gcnr_2d(img, axx, axy, x0, y0);

        add('dataset',spec.id,'arm',A,'metric','peak_lat',      'value',pkLat,   'unit','a.u.');
        add('dataset',spec.id,'arm',A,'metric','peak_axi',      'value',pkAxi,   'unit','a.u.');
        add('dataset',spec.id,'arm',A,'metric','pos_lat',       'value',axx(iLat)-x0,'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','pos_axi',       'value',axy(iAxi)-y0,'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','fwhm_lat',      'value',wLat,    'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','fwhm_axi',      'value',wAxi,    'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','mom_lat',       'value',mLat,    'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','mom_axi',       'value',mAxi,    'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','flank10_90_lat','value',fLat,    'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','pslr_lat',      'value',pslrLat, 'unit','dB');
        add('dataset',spec.id,'arm',A,'metric','n_peaks',       'value',nPk,     'unit','count');
        add('dataset',spec.id,'arm',A,'metric','dip_depth',     'value',dipDepth,'unit','ratio');
        add('dataset',spec.id,'arm',A,'metric','gcnr2d',        'value',g2,      'unit','1');
        add('dataset',spec.id,'arm',A,'metric','cnr2d',         'value',cnr2,    'unit','1');
        add('dataset',spec.id,'arm',A,'metric','psr2d',         'value',psr2,    'unit','1');
        add('dataset',spec.id,'arm',A,'metric','n_bg',          'value',nb,      'unit','px');

        % 幅度域还原（H-形态-2）
        if strcmp(A,'EL')
            pSqrt = sqrt(max(pLat,0));
            add('dataset',spec.id,'arm','EL','metric','fwhm_sqrt_lat', ...
                'value',local_width(axx,pSqrt,0.5),'unit','mm');
        end
        if strcmp(A,'M')
            add('dataset',spec.id,'arm','M','metric','w3db_lat', ...
                'value',local_width(axx,pLat,1/sqrt(2)),'unit','mm');
        end
    end

    % ---- 6. EL vs EH 等价性（逐像素，归一化后）----
    a1 = I.EL(:); a2 = I.EH(:);
    if std(a1) > 0 && std(a2) > 0
        c = corrcoef(a1, a2);
        relMax = max(abs(a1-a2)) / (max(a2) + eps);
        relRMS = sqrt(mean((a1-a2).^2)) / (sqrt(mean(a2.^2)) + eps);
    else
        c = [1 0; 0 1]; relMax = NaN; relRMS = NaN;
    end
    add('dataset',spec.id,'arm','EL_vs_EH','metric','pearson','value',c(1,2),'unit','1');
    add('dataset',spec.id,'arm','EL_vs_EH','metric','relmax', 'value',relMax,'unit','1');
    add('dataset',spec.id,'arm','EL_vs_EH','metric','relrms', 'value',relRMS,'unit','1');

    % ---- 7. 保存裁剪图与剖面 ----
    ph = opt.PatchHalf;
    iy1 = max(1,iy0-ph); iy2 = min(Nx,iy0+ph);
    ix1 = max(1,ix0-ph); ix2 = min(Nx,ix0+ph);
    pa = struct();
    for a = 1:numel(arms)
        A = arms{a};
        pa.(A) = single(I.(A)(iy1:iy2, ix1:ix2));
    end
    R.patches.(spec.id) = pa;
    R.profiles.(spec.id) = struct('x',axx,'y',axy,'lat',profLat,'axi',profAxi, ...
                                  'x0',x0,'y0',y0);
    R.meta.(spec.id) = struct('cfg',cfg,'Nx',Nx,'FOV',FOV, ...
        'f_low',cfg.f_low,'f_high',cfg.f_high,'lp_cutoff',cfg.lp_cutoff, ...
        'beta',cfg.beta_rf,'sqlaw_ok',cfg.sqlaw_ok, ...
        'pearson_sqlaw_vs_env2', getfield_safe(D.info,'sqlaw','pearson_vs_ref'));

    fprintf('  完成：%s  FWHM_lat C/M/EH/EL/SQ = %.3f / %.3f / %.3f / %.3f / %.3f mm\n', ...
        spec.id, get_metric('fwhm_lat','C'), get_metric('fwhm_lat','M'), ...
        get_metric('fwhm_lat','EH'), get_metric('fwhm_lat','EL'), get_metric('fwhm_lat','SQ'));
end

% ---- 写 CSV ----
R.rows = rows;
if opt.Save
    fid = fopen(fullfile(opt.OutDir,'fivechain_data.csv'),'w');
    fprintf(fid,'dataset,arm,metric,value,unit\n');
    for i = 1:numel(rows)
        fprintf(fid,'%s,%s,%s,%.6g,%s\n', rows(i).dataset, rows(i).arm, ...
                rows(i).metric, rows(i).value, rows(i).unit);
    end
    fclose(fid);
    save(fullfile(opt.OutDir,'fivechain_data.mat'), '-struct','R','-v7.3');
    fprintf('\n  [out] %s\n', opt.OutDir);
end

% ==================================================================
    function add(varargin)
        s = struct(varargin{:});
        rows(end+1) = s;
    end

    function v = get_metric(metric, arm)
        v = NaN;
        for ii = 1:numel(rows)
            if strcmp(rows(ii).dataset,spec.id) && strcmp(rows(ii).arm,arm) && ...
               strcmp(rows(ii).metric,metric)
                v = rows(ii).value; return;
            end
        end
    end
end

% ==================================================================
%  指标工具
% ==================================================================
function [pk, idx] = local_peak_near(p, ax, x0, halfWin)
mask = abs(ax(:) - x0) <= halfWin;
idxAll = find(mask);
if isempty(idxAll), [pk, idx] = max(p); return; end
[pk, j] = max(p(idxAll));
idx = idxAll(j);
end

function w = local_width(ax, y, lvl)
ax = ax(:).'; y = y(:).';
pk = max(y); if pk <= 0, w = NaN; return; end
thr = lvl*pk; n = numel(y);
[~, i0] = max(y);
L = i0;  while L > 1 && y(L) > thr, L = L-1; end
Rr = i0; while Rr < n && y(Rr) > thr, Rr = Rr+1; end
if y(L) > thr
    xl = ax(1);
else
    xl = ax(L) + (thr-y(L))*(ax(L+1)-ax(L))/(y(L+1)-y(L)+eps);
end
if y(Rr) > thr
    xr = ax(n);
else
    xr = ax(Rr-1) + (thr-y(Rr-1))*(ax(Rr)-ax(Rr-1))/(y(Rr)-y(Rr-1)+eps);
end
w = abs(xr-xl);
end

function w = local_moment_width(ax, y)
ax = ax(:); y = y(:);
y = max(y,0);
m0 = sum(y); if m0 <= 0, w = NaN; return; end
c = sum(ax.*y)/m0;
v = sum(((ax-c).^2).*y)/m0;
w = 2*sqrt(v);   % 与高斯 FWHM 同量纲的 2 sigma
end

function w = local_flank_10_90(ax, y)
ax = ax(:).'; y = y(:).';
pk = max(y); if pk <= 0, w = NaN; return; end
[~, i0] = max(y);
% 向左找 90% 与 10%
i90 = i0; while i90 > 1 && y(i90) > 0.9*pk, i90 = i90-1; end
i10 = i0; while i10 > 1 && y(i10) > 0.1*pk, i10 = i10-1; end
if i10 >= i0, w = NaN; return; end
x90 = interp_cross(ax, y, i90, 0.9*pk);
x10 = interp_cross(ax, y, i10, 0.1*pk);
w = abs(x90 - x10);
end

function x = interp_cross(ax, y, i, thr)
if i <= 1, x = ax(1); return; end
y1 = y(i); y2 = y(i+1);
if y2 == y1, x = ax(i); return; end
x = ax(i) + (thr-y1)*(ax(i+1)-ax(i))/(y2-y1);
end

function v = local_pslr(p)
p = p(:).'; n = numel(p);
[~, i0] = max(p);
% 主瓣边界：两侧第一次降到 50% 以下再回升处
L = i0; while L > 1 && p(L) > 0.5*p(i0), L = L-1; end
Rr = i0; while Rr < n && p(Rr) > 0.5*p(i0), Rr = Rr+1; end
% 向外扩到局部极小
while L > 1 && p(L-1) < p(L), L = L-1; end
while Rr < n && p(Rr+1) < p(Rr), Rr = Rr+1; end
side = [p(1:max(L-1,1)), p(min(Rr+1,n):n)];
if isempty(side), v = NaN; return; end
v = 20*log10((max(side)+eps)/(p(i0)+eps));
end

function [nPk, dip] = local_multi_peak(p)
p = p(:).'; n = numel(p);
[~, i0] = max(p);
lo = max(1, i0-60); hi = min(n, i0+60);
[pks, locs] = findpeaks(p(lo:hi));
if isempty(pks), nPk = 0; dip = 0; return; end
keep = pks > 0.1*max(p);
pks = pks(keep); locs = locs(keep);
nPk = numel(pks);
dip = 0;
if nPk >= 2
    a = sort(locs);
    for j = 1:numel(a)-1
        valley = min(p(lo+a(j):lo+a(j+1)));
        pkmin  = min(p(lo+a(j)), p(lo+a(j+1)));
        d = (pkmin - valley)/(pkmin + eps);
        if d > dip, dip = d; end
    end
end
end

function [g, cnr, psr, nb] = local_gcnr_2d(img, axx, axy, x0, y0)
[XC, YC] = meshgrid(axx, axy);
rr = hypot(XC-x0, YC-y0);
inMask  = rr <= 0.5;
outMask = (rr >= 3.0) & (rr <= 6.0);
a = img(inMask);  b = img(outMask);
nb = numel(b);
if numel(a) < 5 || nb < 500
    g = NaN; cnr = NaN; psr = NaN; return;
end
lo = min([a(:); b(:)]); hi = max([a(:); b(:)]);
if hi <= lo
    g = 1; cnr = NaN; psr = NaN; return;
end
edges = linspace(lo, hi, 65);
pa = histcounts(a, edges); pa = pa/sum(pa);
pb = histcounts(b, edges); pb = pb/sum(pb);
g = 1 - sum(min(pa,pb));
cnr = (mean(a)-mean(b))/(std(b)+eps);
psr = max(a)/(max(b)+eps);
end

% ==================================================================
function v = getfield_safe(s, f1, f2)
v = NaN;
if isfield(s,f1) && isfield(s.(f1),f2), v = s.(f1).(f2); end
end

function o = parse_opts(o, varargin)
if mod(numel(varargin),2) ~= 0, error('parse_opts:pair','参数必须成对。'); end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o,k), error('parse_opts:unknown','未知参数：%s',k); end
    o.(k) = varargin{i+1};
end
end
