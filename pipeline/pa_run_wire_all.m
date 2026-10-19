function T = pa_run_wire_all(varargin)
%PA_RUN_WIRE_ALL  批量生产全部钨丝点/线图，并汇总指标与达标结论
%
%   T = pa_run_wire_all('Name', Value, ...)
%
%   可选参数
%     'Ids'       只跑指定 id，如 {'W1','W2','W3'}（默认全部）
%     'Nx'        图像像素数（默认 601；逐组 manifest 覆盖优先）
%     'BandMode'  'spec'（默认）| 'audit' | 'analysis' | 'narrowband'
%     'Stride'    旋转扫描抽角步长（默认 1）
%     'MaxFrames' 最多读取角数（默认 Inf）
%     'Save'      是否存盘（默认 true）
%
%   ⚠ 逐组"经验证配置"由 pa_wire_manifest 提供（F0 / FOV / Nx），本函数自动应用：
%     · W3（data4）FOV=60 mm、Nx=1501（40 mm 会截断目标）
%     · W4（data6）F0=1.16 MHz、W5（data5）F0=0.35 MHz、W6（data3）F0=2.00 MHz
%       （装置标称 f0=5 MHz 与实测带中心不符；按标称值跑会把真信号滤掉）
%
%   输出
%     T : 汇总表（table），列见下方 fprintf 表头
%     并在 results/wire/ 下写出
%       _SUMMARY.csv           机读版（批量汇总，含纳排 verdict）
%       _SUMMARY_ablation.csv  机读版（**纯预处理链消融表**：只留 D1/D1^2/D2'/D2
%                              的宽度与对比度，**不含 verdict/hardFail/softFail**）
%       _SUMMARY.md            人读版（含"哪些数据进论文 / 哪些丢弃"的结论）
%
%   用法（无界面）
%     matlab -batch "cd('<repo root>'); addpath(genpath('pipeline')); pa_run_wire_all"
%
%   版本：v2  2026-10-14（应用逐组经验证配置；新增 CNR/gCNR 的 D2p/D2 两列；
%                        新增纯消融表 _SUMMARY_ablation.csv）

opt.Ids       = {};
opt.Nx        = 601;
opt.BandMode  = 'spec';
opt.Stride    = 1;
opt.MaxFrames = Inf;
opt.Save      = true;
opt.WriteSummary = true;   % 是否写出 _SUMMARY* 汇总（部分重跑/冒烟时可置 false，避免覆盖主汇总）
opt = parse_opts(opt, varargin{:});

pipeRoot = fileparts(mfilename('fullpath'));
addpath(genpath(pipeRoot));
outRoot  = fullfile(fileparts(pipeRoot), 'results', 'wire');
if ~exist(outRoot, 'dir'), mkdir(outRoot); end

M = pa_wire_manifest('Root', fileparts(pipeRoot));
if ~isempty(opt.Ids)
    keep = false(size(M));
    for i = 1:numel(M)
        keep(i) = any(strcmp(M(i).id, opt.Ids));
    end
    M = M(keep);
end

n = numel(M);
id      = cell(n,1);  vd  = cell(n,1);  fp  = nan(n,1);  b6 = nan(n,1);
blo     = nan(n,1);   bhi = nan(n,1);   sOk = nan(n,1);   sSp = nan(n,1);
pear    = nan(n,1);   cnr1 = nan(n,1);  cnr2 = nan(n,1); gc1 = nan(n,1); gc2 = nan(n,1);
cnr3    = nan(n,1);   cnr4 = nan(n,1);  gc3 = nan(n,1);  gc4 = nan(n,1);
fw1     = nan(n,1);   fw2 = nan(n,1);   fwp = nan(n,1);  fwb = nan(n,1);
f0use   = nan(n,1);
q8spec  = nan(n,1);   q8eff = nan(n,1);  q8meas = nan(n,1);  q8ratio = nan(n,1);
hardFail = cell(n,1); softFail = cell(n,1); cfgNote = cell(n,1);
files   = cell(n,1);

tAll = tic;
for i = 1:n
    sp = M(i);

    % ---- 逐组"经验证配置"覆盖（单一事实源 = pa_wire_manifest）----
    runArgs = cell(1,14);
    runArgs(1:10) = {'Nx', opt.Nx, 'BandMode', opt.BandMode, ...
                     'Stride', opt.Stride, 'MaxFrames', opt.MaxFrames, ...
                     'Save', opt.Save};
    kArg = 10;
    note = cell(1,3);  kNote = 0;
    if ~isempty(sp.Nx)
        idx = find(strcmp(runArgs(1:kArg), 'Nx'), 1);
        runArgs{idx+1} = sp.Nx;
        kNote = kNote + 1;  note{kNote} = sprintf('Nx=%d', sp.Nx);
    end
    if ~isempty(sp.F0)
        kArg = kArg + 2;
        runArgs(kArg-1:kArg) = {'F0', sp.F0};
        kNote = kNote + 1;  note{kNote} = sprintf('F0=%.2f MHz', sp.F0/1e6);
    end
    if ~isempty(sp.FOV)
        kArg = kArg + 2;
        runArgs(kArg-1:kArg) = {'FOV', sp.FOV};
        kNote = kNote + 1;  note{kNote} = sprintf('FOV=%.0f mm', sp.FOV*1e3);
    end
    runArgs = runArgs(1:kArg);
    cfgNote{i} = strjoin(note(1:kNote), ', ');
    if isempty(cfgNote{i}), cfgNote{i} = '默认'; end

    fprintf('\n[%d/%d] %s   [配置：%s]\n', i, n, sp.id, cfgNote{i});
    try
        R = pa_wire_run(sp, runArgs{:});
        id{i}   = sp.id;
        vd{i}   = R.Q.verdict;
        f0use(i)= R.cfg.f0 / 1e6;
        fp(i)   = R.band.f_peak / 1e6;
        b6(i)   = R.band.beta_used;
        blo(i)  = R.band.f_lo / 1e6;   bhi(i) = R.band.f_hi / 1e6;
        sOk(i)  = double(R.cfg.sqlaw_ok);   sSp(i) = double(R.band.spurFlag);
        pear(i) = R.D.info.sqlaw.pearson_vs_ref;
        cnr1(i) = R.Mrow.env.CNR;      cnr2(i) = R.Mrow.env2.CNR;
        gc1(i)  = R.Mrow.env.gCNR;     gc2(i)  = R.Mrow.env2.gCNR;
        cnr3(i) = R.Mrow.sqlaw.CNR;    cnr4(i) = R.Mrow.sq.CNR;
        gc3(i)  = R.Mrow.sqlaw.gCNR;   gc4(i)  = R.Mrow.sq.gCNR;
        fw1(i)  = R.Mrow.env.aFWHM;    fw2(i)  = R.Mrow.env2.aFWHM;
        fwp(i)  = R.Mrow.sqlaw.aFWHM;  fwb(i)  = R.Mrow.sq.aFWHM;
        % Q8 标称-实测频率一致性（配置完整性）
        q8spec(i)  = R.cfg.f0Spec / 1e6;
        q8eff(i)   = R.cfg.f0_eff  / 1e6;
        q8meas(i)  = R.cfg.f0_meas / 1e6;
        q8ratio(i) = R.cfg.q8_ratio;
        hardFail{i} = strjoin(R.Q.hardFail, '; ');
        softFail{i} = strjoin(R.Q.softFail, '; ');
        files{i}    = R.outDir;
    catch e
        id{i}       = sp.id;
        vd{i}       = 'ERROR';
        hardFail{i} = e.message;
        fprintf('  !!! 失败：%s\n', e.message);
    end
end

T = table(id, vd, cfgNote, f0use, fp, b6, blo, bhi, sOk, sSp, pear, ...
    q8spec, q8eff, q8meas, q8ratio, ...
    fw1, fw2, fwp, fwb, ...
    cnr1, cnr2, cnr3, cnr4, gc1, gc2, gc3, gc4, ...
    (gc3 - gc2), (gc3 - gc4), hardFail, softFail, ...
    'VariableNames', ...
    {'id','verdict','cfg_used','f0_used_MHz','fpeak_MHz','beta','band_lo_MHz','band_hi_MHz', ...
     'D2p_exact','spurFlag','pearson_sqlaw', ...
     'f0_spec_MHz','f0_eff_MHz','f0_meas_MHz','Q8_ratio', ...
     'aFWHM_D1','aFWHM_D1sq','aFWHM_D2p','aFWHM_D2', ...
     'CNR_D1','CNR_D1sq','CNR_D2p','CNR_D2', ...
     'gCNR_D1','gCNR_D1sq','gCNR_D2p','gCNR_D2', ...
     'dgCNR_D2p_vs_D1sq','dgCNR_D2p_vs_D2', ...
     'hardFail','softFail'});

fprintf('\n================= 汇总 =================\n');
disp(T(:, {'id','verdict','cfg_used','f0_used_MHz','fpeak_MHz','band_lo_MHz','band_hi_MHz', ...
           'beta','D2p_exact','spurFlag','pearson_sqlaw', ...
           'f0_spec_MHz','f0_eff_MHz','f0_meas_MHz','Q8_ratio', ...
           'aFWHM_D1','aFWHM_D1sq','aFWHM_D2p','aFWHM_D2', ...
           'gCNR_D1','gCNR_D1sq','gCNR_D2p','gCNR_D2'}));
fprintf('总耗时 %.1f s\n', toc(tAll));

% ---- 落盘 --------------------------------------------------------
if ~opt.WriteSummary
    fprintf('（WriteSummary=false：跳过 _SUMMARY* 落盘，避免覆盖主汇总）\n');
    return;
end
writetable(T, fullfile(outRoot, '_SUMMARY.csv'), 'Encoding', 'UTF-8');

% 纯消融表：只留"预处理链各定义"的宽度与对比度，**不含纳排列**
% （纳排结论属 Table S1 的职责，见 docs/06 / docs/08）
Tabl = T(:, {'id','cfg_used','f0_used_MHz','beta','band_lo_MHz','band_hi_MHz', ...
             'D2p_exact','spurFlag','pearson_sqlaw', ...
             'aFWHM_D1','aFWHM_D1sq','aFWHM_D2p','aFWHM_D2', ...
             'CNR_D1','CNR_D1sq','CNR_D2p','CNR_D2', ...
             'gCNR_D1','gCNR_D1sq','gCNR_D2p','gCNR_D2', ...
             'dgCNR_D2p_vs_D1sq','dgCNR_D2p_vs_D2'});
writetable(Tabl, fullfile(outRoot, '_SUMMARY_ablation.csv'), 'Encoding', 'UTF-8');
fprintf('消融表已写出：%s\n', fullfile(outRoot, '_SUMMARY_ablation.csv'));

L = cell(1, 54 + 5*n);  kL = 0;
kL = kL + 1;  L{kL} = '# 钨丝点/线图批量结果汇总';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = sprintf('生成时间：%s', char(datetime('now','Format','yyyy-MM-dd HH:mm:ss')));
kL = kL + 1;  L{kL} = sprintf('预设：Nx=%d（逐组覆盖优先），BandMode=%s，Stride=%d', opt.Nx, opt.BandMode, opt.Stride);
kL = kL + 1;  L{kL} = sprintf('判据：D2p 精确成立 = (B < 2*f_low) <=> (f_high < 3*f_low)');
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '> ⚠ 逐组"经验证配置"（来源 `pa_wire_manifest`）已自动应用；`cfg_used` 列给出每组实际配置。';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '## 四路定义（消融对象）';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '| 记号 | 通道域信号 | 几何补偿 | 说明 |';
kL = kL + 1;  L{kL} = '|---|---|---|---|';
kL = kL + 1;  L{kL} = '| **D1** (`env`) | `abs(hilbert(x))` | `r` | 线性包络叠加 = 基线 I_M |';
kL = kL + 1;  L{kL} = '| **D1²** (`env2`) | `abs(hilbert(x))^2` | `r2` | 通道级平方（Hilbert 路） |';
kL = kL + 1;  L{kL} = '| **D2′** (`sqlaw`) | `LPF(x^2)` | `r`+PostSquare | 通道级平方（**免-Hilbert** 路，正文主方法） |';
kL = kL + 1;  L{kL} = '| **D2** (`sq`) | `x^2` | `r2` | 裸平方（缺低通/去 DC → 反例） |';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '> 两条消融的读法：`dgCNR_D2p_vs_D1sq`（免-Hilbert 等价性，期望 ≈ 0）与 `dgCNR_D2p_vs_D2`（低通必要性，期望 > 0）。';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '## 纳排结论（**决定哪些数据进论文**）';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '| id | 配置 | 结论 | 硬失败 | 软失败 |';
kL = kL + 1;  L{kL} = '|---|---|---|---|---|';
for i = 1:n
    kL = kL + 1;
    L{kL} = sprintf('| %s | %s | %s | %s | %s |', id{i}, cfgNote{i}, vd{i}, ...
        hardFail{i}, softFail{i});
end
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '## 指标明细（预处理链消融）';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '| id | f0用/MHz | 谱峰/MHz | 真实带/MHz | B/MHz | beta | D2p精确 | 尖峰 | Pearson(D2p,D1^2) | aFWHM D1 | aFWHM D1^2 | aFWHM D2p | aFWHM D2 | CNR D1 | CNR D1^2 | CNR D2p | CNR D2 | gCNR D1 | gCNR D1^2 | gCNR D2p | gCNR D2 |';
kL = kL + 1;  L{kL} = '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|';
for i = 1:n
    kL = kL + 1;
    L{kL} = sprintf(['| %s | %.2f | %.2f | [%.2f %.2f] | %.2f | %.2f | %d | %d | %.4f | ' ...
        '%.4g | %.4g | %.4g | %.4g | %.4g | %.4g | %.4g | %.4g | %.4g | %.4g | %.4g | %.4g |'], ...
        id{i}, f0use(i), fp(i), blo(i), bhi(i), (bhi(i)-blo(i)), b6(i), sOk(i), sSp(i), pear(i), ...
        fw1(i), fw2(i), fwp(i), fwb(i), cnr1(i), cnr2(i), cnr3(i), cnr4(i), ...
        gc1(i), gc2(i), gc3(i), gc4(i));
end
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '## Q8 标称–实测频率一致性（配置完整性）';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '| id | 标称 f0/MHz | 实际 f0/MHz | 实测带中心/MHz | 实测/实际 | 说明 |';
kL = kL + 1;  L{kL} = '|---|---|---|---|---|---|';
for i = 1:n
    kL = kL + 1;
    if q8ratio(i) >= 0.5 && q8ratio(i) <= 2.0
        q8note = 'PASS';
    else
        q8note = '**FAIL → 首要怀疑配置**';
    end
    L{kL} = sprintf('| %s | %.2f | %.2f | %.2f | %.3f | %s |', ...
        id{i}, q8spec(i), q8eff(i), q8meas(i), q8ratio(i), q8note);
end
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '> 「实测/实际」= 实测带中心 ÷ 本次实际使用的中心；判据 ∈[0.5, 2.0]。';
kL = kL + 1;  L{kL} = '> 「标称」列是换能器数据手册值（`pa_cfg` 的 `f0Spec`），不随运行时覆盖改变。';
kL = kL + 1;  L{kL} = '> docs/06 §4 记录的是**回填前**的情形：标称恒为 5 MHz 时 data3/data5/data6 三组不成立。';
kL = kL + 1;  L{kL} = '';
kL = kL + 1;  L{kL} = '## 输出目录';
kL = kL + 1;  L{kL} = '';
for i = 1:n
    if ~isempty(files{i})
        kL = kL + 1;
        L{kL} = sprintf('- %s : `%s`', id{i}, files{i});
    end
end
md = strjoin(L(1:kL), newline);
fid = fopen(fullfile(outRoot, '_SUMMARY.md'), 'w', 'n', 'UTF-8');
fwrite(fid, md, 'char');  fclose(fid);
fprintf('汇总已写出：%s\n', fullfile(outRoot, '_SUMMARY.md'));
end

% ==================================================================
function o = parse_opts(o, varargin)
if mod(numel(varargin), 2) ~= 0
    error('parse_opts:pair', '参数必须成对出现。');
end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o, k), error('parse_opts:unknown', '未知参数：%s', k); end
    o.(k) = varargin{i+1};
end
end
