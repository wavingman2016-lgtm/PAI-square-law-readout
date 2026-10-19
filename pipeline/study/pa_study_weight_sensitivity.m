function R = pa_study_weight_sensitivity(varargin)
%PA_STUDY_WEIGHT_SENSITIVITY  EL 的几何权重敏感性：g_m^2 / g_m / 无补偿
%
%   目的
%     外部评审（v0.43 轮，第 2 条）指出：五链对照中 EL 与 M 同时改变了
%     逐通道非线性与几何权重（g_m vs g_m^2），因此 EL 的差异不能全部归给
%     平方律。本脚本在**不改动任何采集、不覆盖既有归档**的前提下，把 EL
%     的几何权重单独拿来做三个设置：
%
%       EL2 : Comp='r2'   sum_m g_m^2 q_m     主方法（正文所用）
%       EL1 : Comp='r'    sum_m g_m   q_m     权重不随平方升幂
%       EL0 : Comp='none' sum_m       q_m     无几何补偿
%
%     对每个设置报告与 M、C 相同的指标（2D gCNR、表观 FWHM、PSLR），
%     用来看主要结论的**方向**是否随权重规则改变。
%
%   输出
%     results/fivechain/fivechain_weight_sensitivity.csv
%     results/fivechain/fivechain_weight_sensitivity.mat
%
%   用法
%     pa_study_weight_sensitivity()
%     pa_study_weight_sensitivity('IDs',{'W1','W2'})
%
%   版本：v1  2026-10-18（v0.43 轮补充分析）

opt.IDs       = {'W1','W2','W3','W4','W5','W6'};
opt.OutDir    = '';
opt.Save      = true;
opt.Verbose   = true;
opt = parse_opts(opt, varargin{:});

root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
if isempty(opt.OutDir), opt.OutDir = fullfile(root, 'results', 'fivechain'); end
if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end

addpath(fullfile(root, 'pipeline', 'config'));
addpath(fullfile(root, 'pipeline', 'preprocess'));
addpath(fullfile(root, 'pipeline', 'recon'));
addpath(fullfile(root, 'pipeline', 'wire'));

M = pa_wire_manifest('Root', root);

rows = struct('dataset', {}, 'arm', {}, 'metric', {}, 'value', {}, 'unit', {});
R = struct(); R.rows = rows; R.meta = struct();

t0 = tic;
for k = 1:numel(M)
    spec = M(k);
    if ~any(strcmpi(opt.IDs, spec.id)), continue; end

    if opt.Verbose
        fprintf('\n######## %s : %s ########\n', spec.id, spec.desc);
    end

    % ---- 配置：与 pa_study_fivechain_data 完全一致 ----
    cfg = pa_cfg(spec.cfgName, 'unified');
    if ~isempty(spec.F0), cfg.f0_nominal = spec.F0; else, cfg.f0_nominal = cfg.f0; end
    cfg.f0 = cfg.f0_nominal;
    bw = min(cfg.bw_law, 0.95);
    cfg.f_low  = max(1e3,           cfg.f0 * (1 - bw/2));
    cfg.f_high = min(cfg.fs/2*0.98, cfg.f0 * (1 + bw/2));
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
    FOV = cfg.FOV; if ~isempty(spec.FOV), FOV = spec.FOV; end

    % ---- 加载 + 预处理 ----
    [sig, ldmeta] = pa_load_signals(spec.dataDir, cfg, 'Verbose', false);
    if isempty(cfg.nSamples), cfg.nSamples = size(sig,1); end
    SensorPos = [];
    if isfield(ldmeta,'sensorPos'), SensorPos = ldmeta.sensorPos; end

    D = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw'});

    Z = complex(zeros(size(D.filtered)));
    for ch = 1:size(D.filtered,2)
        Z(:,ch) = hilbert(D.filtered(:,ch));
    end

    I = struct();
    [I.C, grid] = pa_backproject_coherent(Z, cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r','Normalize','max','SensorPos',SensorPos);
    I.M   = pa_backproject(D.env,   cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r',   'Normalize','max','SensorPos',SensorPos);
    I.EL2 = pa_backproject(D.sqlaw, cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r2',  'Normalize','max','SensorPos',SensorPos);
    I.EL1 = pa_backproject(D.sqlaw, cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','r',   'Normalize','max','SensorPos',SensorPos);
    I.EL0 = pa_backproject(D.sqlaw, cfg, 'Nx',Nx,'FOV',FOV, ...
                        'Comp','none','Normalize','max','SensorPos',SensorPos);

    % ---- 参考位置与 ROI 均由 C 定义（与正文同一条规则）----
    [~, imax] = max(I.C(:));
    [iy0, ix0] = ind2sub(size(I.C), imax);
    axx = grid.x;  axy = grid.y;
    x0 = axx(ix0); y0 = axy(iy0);

    arms = {'C','M','EL2','EL1','EL0'};
    for a = 1:numel(arms)
        A = arms{a}; img = I.(A);
        pLat = img(iy0, :).';
        pAxi = img(:, ix0);

        [pkLat, iLat] = local_peak_near(pLat, axx, x0, 2.0);
        [pkAxi, iAxi] = local_peak_near(pAxi, axy, y0, 2.0);

        add('dataset',spec.id,'arm',A,'metric','peak_lat','value',pkLat,'unit','a.u.');
        add('dataset',spec.id,'arm',A,'metric','peak_axi','value',pkAxi,'unit','a.u.');
        add('dataset',spec.id,'arm',A,'metric','pos_lat','value',axx(iLat)-x0,'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','pos_axi','value',axy(iAxi)-y0,'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','fwhm_lat','value',local_width(axx,pLat,0.5),'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','fwhm_axi','value',local_width(axy,pAxi,0.5),'unit','mm');
        add('dataset',spec.id,'arm',A,'metric','pslr_lat','value',local_pslr(pLat),'unit','dB');

        [g2, cnr2] = local_gcnr_2d(img, axx, axy, x0, y0);
        add('dataset',spec.id,'arm',A,'metric','gcnr2d','value',g2,'unit','1');
        add('dataset',spec.id,'arm',A,'metric','cnr2d','value',cnr2,'unit','1');
    end

    % ---- 图像级相似度：权重改动到底改了多少 ----
    for pair = {{'EL2','EL1'}, {'EL2','EL0'}}
        P = pair{1};
        a1 = I.(P{1})(:); a2 = I.(P{2})(:);
        c = corrcoef(a1, a2);
        add('dataset',spec.id,'arm',[P{1} '_vs_' P{2}],'metric','pearson','value',c(1,2),'unit','1');
        add('dataset',spec.id,'arm',[P{1} '_vs_' P{2}],'metric','relmax', ...
            'value',max(abs(a1-a2))/(max(a1)+eps),'unit','1');
    end

    R.meta.(spec.id) = struct('Nx',Nx,'FOV',FOV,'lp_cutoff',cfg.lp_cutoff, ...
        'beta',cfg.beta_rf,'f0',cfg.f0,'R',cfg.R);

    fprintf('  %s  gCNR  C=%.4f M=%.4f EL2=%.4f EL1=%.4f EL0=%.4f\n', spec.id, ...
        get_metric('gcnr2d','C'), get_metric('gcnr2d','M'), get_metric('gcnr2d','EL2'), ...
        get_metric('gcnr2d','EL1'), get_metric('gcnr2d','EL0'));
    fprintf('  %s  FWHM_lat  M=%.3f EL2=%.3f EL1=%.3f EL0=%.3f mm\n', spec.id, ...
        get_metric('fwhm_lat','M'), get_metric('fwhm_lat','EL2'), ...
        get_metric('fwhm_lat','EL1'), get_metric('fwhm_lat','EL0'));
end

R.rows = rows;
if opt.Save
    fid = fopen(fullfile(opt.OutDir,'fivechain_weight_sensitivity.csv'),'w');
    fprintf(fid,'dataset,arm,metric,value,unit\n');
    for i = 1:numel(rows)
        fprintf(fid,'%s,%s,%s,%.6g,%s\n', rows(i).dataset, rows(i).arm, ...
                rows(i).metric, rows(i).value, rows(i).unit);
    end
    fclose(fid);
    save(fullfile(opt.OutDir,'fivechain_weight_sensitivity.mat'), '-struct','R','-v7.3');
    fprintf('\n  [out] %s  (%.1f s)\n', opt.OutDir, toc(t0));
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

function v = local_pslr(p)
p = p(:).'; n = numel(p);
[~, i0] = max(p);
L = i0; while L > 1 && p(L) > 0.5*p(i0), L = L-1; end
Rr = i0; while Rr < n && p(Rr) > 0.5*p(i0), Rr = Rr+1; end
while L > 1 && p(L-1) < p(L), L = L-1; end
while Rr < n && p(Rr+1) < p(Rr), Rr = Rr+1; end
side = [p(1:max(L-1,1)), p(min(Rr+1,n):n)];
if isempty(side), v = NaN; return; end
v = 20*log10((max(side)+eps)/(p(i0)+eps));
end

function [g, cnr] = local_gcnr_2d(img, axx, axy, x0, y0)
[XC, YC] = meshgrid(axx, axy);
rr = hypot(XC-x0, YC-y0);
inMask  = rr <= 0.5;
outMask = (rr >= 3.0) & (rr <= 6.0);
a = img(inMask);  b = img(outMask);
if numel(a) < 5 || numel(b) < 500, g = NaN; cnr = NaN; return; end
lo = min([a(:); b(:)]); hi = max([a(:); b(:)]);
if hi <= lo, g = 1; cnr = NaN; return; end
edges = linspace(lo, hi, 65);
pa = histcounts(a, edges); pa = pa/sum(pa);
pb = histcounts(b, edges); pb = pb/sum(pb);
g = 1 - sum(min(pa,pb));
cnr = (mean(a)-mean(b))/(std(b)+eps);
end

function o = parse_opts(o, varargin)
if mod(numel(varargin),2) ~= 0, error('parse_opts:pair','参数必须成对。'); end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o,k), error('parse_opts:unknown','未知参数：%s',k); end
    o.(k) = varargin{i+1};
end
end
