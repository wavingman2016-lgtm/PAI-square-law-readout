function R = pa_wire_run(spec, varargin)
%PA_WIRE_RUN  单张钨丝点/线图的完整生产流程（加载→统一预处理→四路成像→指标→QC→出图）
%
%   R = pa_wire_run(spec, 'Name', Value, ...)
%
%   输入 spec：pa_wire_manifest 的一个元素（或含同名字段的结构体）
%
%   可选参数
%     'Nx'        图像像素数（默认 601）
%     'Preset'    pa_cfg 预设（默认 'unified'）
%     'BandMode'  'spec'       【默认】按标称 f0 构造合法窄带（beta<1，D2' 精确成立）
%                             这是"平方前必须先滤波"的落点
%                 'audit'      收紧到数据实测带（含噪声尾巴，D2' 常不合法，仅对照）
%                 'narrowband' 强制 [0.5*f0, 1.5*f0]（beta=1，临界）
%                 'analysis'   沿用 cfg 分析带（最宽，历史对照）
%     'Save'      是否存盘出图（默认 true）
%     'OutDir'    输出目录（默认 results/wire/<outSub>）
%     'Stride'    旋转扫描抽角步长（默认 1）
%     'MaxFrames' 最多读取的角数/帧数（默认 Inf）
%     'Verbose'   打印进度（默认 true）
%
%   输出 R（结构体）
%     R.spec, R.cfg, R.meta, R.D, R.band, R.IM, R.profRow, R.profCol,
%     R.M(row), R.M(col), R.Q, R.report, R.outDir
%
%   为什么必须"先审计带宽、再定 D2' 的低通截止"
%     平方律检波 LPF(x^2) = 1/2|z|^2 只在信号满足窄带条件时成立：
%          B < 2*f_low   <=>   f_high < 3*f_low   <=>   beta = B/f0 < 1
%     合法低通区间为 ( B , 2*f_low )。若把分析带设得远宽于换能器实际带宽，
%     区间会变成空集，D2' 就退化成"带 2f0 残留的裸平方"。故本函数先用
%     pa_band_audit 从数据量出真实带宽，再据此定低通截止。
%     —— 这正是"部分数据 D2 表现不理想"的直接成因。
%
%   版本：v2  2026-10-14（取消"强制合法"；载波改用带中心；新增 BandMode='audit'）

opt.Nx        = 601;
opt.FOV       = [];     % 成像视场边长(m)；[] = 沿用 cfg.FOV（用于 Q4 视场截断的复核）
opt.F0        = [];     % 覆盖标称中心频率(Hz)；[] = 沿用 cfg.f0
                        % 用于"标称探头频率与实际频谱不符"时的复核（data6 实测峰 1.06 MHz）
opt.Preset    = 'unified';
opt.BandMode  = 'spec';
opt.Save      = true;
opt.OutDir    = '';
opt.Stride    = 1;
opt.MaxFrames = Inf;
opt.H5Key     = '';     % HDF5 数据集键名（给定时走 HDF5 分支；PATATO 用 'raw_data'）
opt.H5WL      = 1;      % HDF5 4D 数据的波长索引（PATATO 有 10 个波长）
opt.ArmC      = true;   % 是否额外算 Arm C（相干解析信号反投影 = 教科书 DAS/FBP）
opt.Epath     = 'consist'; % 能量臂 I_E 的实现路径（**默认 = 论文正文口径**）
                          %   'consist' = **EI**（envelope 包络路，**正文默认**）：Comp='r' 配通道级平方（PostSquare）。
                          %             几何补偿与幅度臂共用**同一条** g_m=d_m/R —— 全链只有一条补偿规则，
                          %             这正是 Methods 的叙述口径（docs/09 §2.3.1 正文口径）。
                          %   'direct'  = **LP**（square-and-low-pass 平方—低通路，免 Hilbert）：Comp='r2' 配平方律信号（= data.^2 逐点）。
                          %             与 'consist' 逐点等价（差全局常数 ½，被归一化吸收；
                          %             差值为**总实现残差**——transition-band leakage、边界处理与
                          %             "插值—平方"先后三项共同承载、**未分离**——实测 ≤0.53 %（max-rel）、L2 ≤0.62 %、QC 判定不变），
                          %             因 $p^2\propto1/r^2$ 可**物理直读**，故放 Supplement 作等价证明
                          %             （docs/09 §2.3.2）。v3.2 之前归档结果为 direct，两者 QC 一致。
                          %   ⚠️ 命名口径（R6）：正文/图注一律用 **EI / LP**（§2.7）；`consist`/`direct` 只是本选项取值。
opt.Verbose   = true;
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot   = fileparts(fileparts(mfilename('fullpath')));   % .../pipeline
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', 'wire', spec.outSub);
end

if opt.Verbose
    fprintf('\n################ %s : %s ################\n', spec.id, spec.desc);
end

% ==================================================================
%  1. 配置 / 加载 / 首次预处理（用 cfg 自带的分析带）
% ==================================================================
cfg   = pa_cfg(spec.cfgName, opt.Preset);
[sig, ldmeta] = pa_load_signals(spec.dataDir, cfg, 'Stride', opt.Stride, ...
                        'MaxFrames', opt.MaxFrames, 'Verbose', opt.Verbose, ...
                        'H5Key', opt.H5Key, 'H5WL', opt.H5WL);

% 阵元坐标：外部数据集（如 PATATO）阵列形状不规则，须由数据自带的 GEOMETRY 提供；
% 为空时下游一律沿用 cfg 推断的阵列几何（自有数据即走此路径）。
SensorPos = [];
if isfield(ldmeta, 'sensorPos'), SensorPos = ldmeta.sensorPos; end
if ~isempty(SensorPos) && opt.Verbose
    fprintf('  [geom] 使用数据集自带阵元坐标 SensorPos (2 x %d)\n', size(SensorPos, 2));
end

% 运行时校正采样点数（旋转扫描的 nSamples 随装置不同）
if isempty(cfg.nSamples), cfg.nSamples = size(sig, 1); end

D0 = pa_preprocess(sig, cfg);

% ==================================================================
%  2. 带宽审计 -> 定真实带 / f0 / 低通截止 / 合法性
%
%  修正要点（2026-10-14）
%   · 不再强制 sqlaw_ok=true。旧版把低通截止硬设为"实测峰位"并宣告恒合法，
%     等于绕过了物理判据；实测峰位还可能是单频毛刺（data1 曾落在 10.9 MHz）。
%   · 载波 f0 改用**实测带中心**而非峰位（峰位对毛刺敏感，带中心更稳）。
%   · BandMode='audit' 时，把带通**收紧到实测真实带**再平方：
%     这既是"平方前必须先滤波"的落点，也让 D2' 的窄带条件在真实带宽上成立。
% ==================================================================
cfg.f0_nominal = cfg.f0;                    % 探头标称中心频率（来自 cfg，工程给定）
if ~isempty(opt.F0)                         % 复核：以实测频谱中心覆盖标称值
    cfg.f0_nominal = opt.F0;
    if opt.Verbose
        fprintf('  [band] 标称 f0 被覆盖为实测值 %.3f MHz\n', opt.F0/1e6);
    end
end
B = pa_band_audit(D0.filtered, cfg);         % 数据实测带（仅供 QC 与对照）
cfg.f0_meas = 0.5 * (B.f_lo + B.f_hi);
cfg.bandMode = opt.BandMode;

switch lower(opt.BandMode)
    case 'spec'
        % 【默认】按**标称 f0** 构造合法窄带：f_low = f0(1-bw/2), f_high = f0(1+bw/2)
        % 取 bw < 1 保证 beta = B/f0 < 1，平方律条件按构造成立。
        % 这是"平方前必须先滤波"的落点：把宽带数据先收窄到换能器标称带。
        cfg.f0     = cfg.f0_nominal;
        bw         = min(cfg.bw_law, 0.95);
        cfg.f_low  = max(1e3,               cfg.f0 * (1 - bw/2));
        cfg.f_high = min(cfg.nyquist*0.98,  cfg.f0 * (1 + bw/2));
    case 'audit'
        % 收紧到**数据实测带**（外扩 10%）：滤掉带外噪声，但实测带常含噪声尾巴，
        % 会宽于换能器真实带 -> D2' 通常**不合法**，仅作对照。
        cfg.f0     = cfg.f0_meas;
        cfg.f_low  = max(1e3,               B.f_lo * 0.90);
        cfg.f_high = min(cfg.nyquist*0.98,  B.f_hi * 1.10);
    case 'narrowband'
        % 强制窄带化到 [0.5*f0, 1.5*f0]（beta = 1.0，临界）
        cfg.f0     = cfg.f0_meas;
        cfg.f_low  = max(1e3,               0.5 * cfg.f0);
        cfg.f_high = min(cfg.nyquist*0.98,  1.5 * cfg.f0);
    otherwise
        % 'analysis'：沿用 cfg 自带分析带（最宽），仅作历史对照
        cfg.f0     = cfg.f0_meas;
end

% ---- Q8 标称–实测频率一致性（配置完整性；判据与出处见 docs/06 §4）----
%   cfg.f0Spec  = 数据手册标称中心（pa_cfg 给定，不随 F0 覆盖改变）
%   cfg.f0_eff  = 本次实际用于构造分析带的中心（F0 覆盖后的值）
%   cfg.f0_meas = 数据实测带中心（pa_band_audit）
%   q8_ratio    = f0_meas / f0_eff  —— 运行时闸门（须 ∈ [0.5, 2.0]）
%   q8_nominal  = f0_meas / f0Spec  —— 审计量：暴露"标称 f0 设错"的历史配置
cfg.f0_eff     = cfg.f0;
cfg.q8_ratio   = cfg.f0_meas / max(cfg.f0_eff, eps);
cfg.q8_nominal = cfg.f0_meas / max(cfg.f0Spec, eps);
cfg.q8_pass    = (cfg.q8_ratio >= 0.5) && (cfg.q8_ratio <= 2.0);

% 按**最终分析带**重算平方律合法性（正确形式：合法区间 = (B, 2*f_low)）
B_rf             = cfg.f_high - cfg.f_low;
cfg.beta_rf      = B_rf / max(cfg.f0, eps);
cfg.sqlaw_lo_cut = B_rf;
cfg.sqlaw_hi_cut = 2 * cfg.f_low;
cfg.sqlaw_ok     = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;
cfg.lp_range     = [cfg.sqlaw_lo_cut, cfg.sqlaw_hi_cut];
if cfg.sqlaw_ok
    cfg.lp_cutoff = 0.5 * (cfg.sqlaw_lo_cut + cfg.sqlaw_hi_cut);
else
    cfg.lp_cutoff = cfg.f0;
    cfg.sqlaw_narrowband = [max(1e3, 0.5*cfg.f0), min(cfg.nyquist*0.98, 1.5*cfg.f0)];
end

if opt.Verbose
    fprintf('  [band] 模式 %s | 标称 f0 %.2f MHz | 实测带 [%.2f %.2f] MHz (峰 %.2f, %s, 尖峰=%d)\n', ...
        opt.BandMode, cfg.f0_nominal/1e6, B.f_lo/1e6, B.f_hi/1e6, ...
        B.f_peak/1e6, B.bandSrc, B.spurFlag);
    fprintf('  [band] 最终分析带 [%.2f %.2f] MHz | B=%.2f MHz | beta=%.2f\n', ...
        cfg.f_low/1e6, cfg.f_high/1e6, (cfg.f_high-cfg.f_low)/1e6, ...
        (cfg.f_high-cfg.f_low)/max(cfg.f0,eps));
    fprintf('  [band] 低通 %.2f MHz | 合法区间 (%.2f, %.2f) MHz | D2p 精确成立=%d\n', ...
        cfg.lp_cutoff/1e6, cfg.lp_range(1)/1e6, cfg.lp_range(2)/1e6, cfg.sqlaw_ok);
end

% ==================================================================
%  3. 正式预处理（四路解调）
% ==================================================================
D = pa_preprocess(sig, cfg);
if opt.Verbose
    fprintf('  [prep] D2'' vs D1^2  Pearson = %.4f ; 幅度比 = %.4f\n', ...
        D.info.sqlaw.pearson_vs_ref, D.info.sqlaw.amp_ratio_vs_ref);
end

sigMap = struct('env',   D.env,   ...    % D1  线性包络（基线 I_C）
                'env2',  D.env2,  ...    % D1^2 包络平方（既有主方法）
                'sqlaw', D.sqlaw, ...    % D2'  平方律（免 Hilbert）
                'sq',    D.sq);          % D2   裸平方（缺陷对照）

% ==================================================================
%  4. 四路反投影（一次几何计算）
% ==================================================================
if isempty(opt.FOV)
    bpFOV = cfg.FOV;
else
    bpFOV = opt.FOV;
end
[IMs, grid] = pa_backproject_multi(sigMap, cfg, 'Nx', opt.Nx, 'FOV', bpFOV, ...
                                   'SensorPos', SensorPos);

% ---- Arm C：相干（解析信号）反投影 = 教科书 DAS/FBP（2026-10-14 新增）----
% 与上面四路**共用同一前处理、同一几何、同一网格与插值**；
% 唯一差别是"复数相干求和后取模"而非"非相干叠加"。
%   · 加入 IMs 后，下面第 5 节的循环会自动为它算 profRow.coh / Mrow.coh 等；
%   · pa_wire_figs 与 pa_qc 都**不**遍历 fieldnames(IMs)（前者硬编码白名单
%     env/env2/sqlaw/sq，后者只用 A.base/A.sqlaw），故不会改变既有出图与 QC 结论。
%   · 为什么必须有它：包络叠加丢掉了载波相位，分辨率差约 5 倍，不是教科书主流；
%     详见 docs/09 §1.5、§2.1。
if opt.ArmC
    Z = complex(zeros(size(D.filtered)));
    for ch = 1:size(D.filtered, 2)
        Z(:, ch) = hilbert(D.filtered(:, ch));
    end
    IMs.coh = pa_backproject_coherent(Z, cfg, 'Nx', opt.Nx, ...
                    'FOV', bpFOV, 'Comp', 'r', 'Normalize', 'max', ...
                    'SensorPos', SensorPos);
    if opt.Verbose
        fprintf('  [armC] 相干反投影已加入 IMs.coh（comp=r，教科书写法）\n');
    end
end

% ---- 能量臂 I_E 的实现路径选择：EI（envelope 包络路，**默认/正文口径**；代码值 consist）
%                                    vs LP（square-and-low-pass，免 Hilbert；代码值 direct）----
% 两者逐点等价（差全局常数 ½，被归一化吸收；差值为**总实现残差**——transition-band leakage、
% 边界处理与"插值—平方"先后三项共同承载、**未分离**——实测 ≤0.53 %（max-rel）、L2 ≤0.62 %、QC 不变），
% 但 'consist' 把几何补偿写成与幅度臂**同一个** g_m=d/R，
% 使全链只有一条补偿规则，便于 Methods 只陈述一条。见 pa_study_comp 的数值验证与 docs/09 §2.3.1/§2.3.2。
if strcmpi(opt.Epath, 'consist')
    IMs.sqlaw = pa_backproject(D.env, cfg, 'Nx', opt.Nx, 'FOV', bpFOV, ...
                    'Comp', 'r', 'PostSquare', true, ...
                    'Filt', cfg.filt, 'TakeAbs', cfg.takeAbs, 'Normalize', 'max', ...
                    'SensorPos', SensorPos);
    if opt.Verbose
        fprintf('  [armE] 能量臂=EI（envelope 包络路，正文口径；代码值 consist）：Comp=r + PostSquare，与幅度臂共用同一条 g_m=d/R\n');
    end
elseif ~strcmpi(opt.Epath, 'direct')
    error('pa_wire_run:Epath', 'opt.Epath 只能是 ''direct'' 或 ''consist''（当前：%s）', opt.Epath);
end

% ==================================================================
%  5. 剖面与指标（横向 = 行；纵向 = 列）
% ==================================================================
meths = fieldnames(IMs);
Mrow = struct();  Mcol = struct();
Prow = struct();  Pcol = struct();  ROIrow = struct();  ROIcol = struct();

for i = 1:numel(meths)
    m = meths{i};
    [pr, axr, rr] = pa_profile(IMs.(m), grid, 'point', 'Dir', 'row');
    [pc, axc, rc] = pa_profile(IMs.(m), grid, 'line',  'Dir', 'col');
    Prow.(m) = pr;  Pcol.(m) = pc;
    ROIrow.(m) = rr;  ROIcol.(m) = rc;
    Mrow.(m) = pa_metrics(pr, axr, rr);
    Mcol.(m) = pa_metrics(pc, axc, rc);
end

% ==================================================================
%  6. 达标筛检（决定该数据是否可进论文结果集）
% ==================================================================
A = struct('raw', sig, 'filtered', D.filtered, 'IM', IMs, 'M', Mrow, ...
           'grid', grid, 'cfg', cfg, 'base', 'env', 'test', 'env2', ...
           'sqlaw', 'sqlaw', 'bare', 'sq');
[Q, qcReport] = pa_qc(A);

if opt.Verbose
    fprintf('  [QC]  %s\n', Q.verdict);
    for i = 1:numel(Q.hardFail), fprintf('        - %s\n', Q.hardFail{i}); end
    for i = 1:numel(Q.softFail), fprintf('        - %s\n', Q.softFail{i}); end
end

% ==================================================================
%  7. 打包
% ==================================================================
R = struct('spec', spec, 'cfg', cfg, 'meta', struct('nSamples', size(sig,1), ...
        'nChannels', size(sig,2)), 'D', D, 'band', B, 'IM', IMs, ...
        'grid', grid, 'profRow', Prow, 'profCol', Pcol, ...
        'Mrow', Mrow, 'Mcol', Mcol, 'Q', Q, 'qcReport', qcReport, ...
        'axRow', ((1:numel(Prow.env)) - numel(Prow.env)/2) * grid.dx, ...
        'axCol', ((1:numel(Pcol.env)) - numel(Pcol.env)/2) * grid.dx, ...
        'outDir', opt.OutDir);

% ==================================================================
%  8. 存盘与出图
% ==================================================================
if opt.Save
    if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end
    pa_wire_figs(R, opt.OutDir);
    % 存盘前剥离大矩阵（原始信号与四路解调结果可数百 MB），只保留可复算的中间量：
    % 图像、剖面、指标、配置、带宽审计与 QC。信号如需复算，重跑本函数即可。
    Rs = R;
    if isfield(Rs, 'D') && isstruct(Rs.D)
        keepInfo = struct();
        if isfield(Rs.D, 'info'), keepInfo = Rs.D.info; end
        Rs.D = struct('info', keepInfo, 'note', ...
            '信号矩阵已剥离（体积原因）；重跑 pa_wire_run 可复算');
    end
    save(fullfile(opt.OutDir, sprintf('%s_results.mat', spec.id)), '-struct', 'Rs', '-v7.3');
    if opt.Verbose
        fprintf('  [out]  %s\n', opt.OutDir);
    end
end
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
