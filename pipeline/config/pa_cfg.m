function cfg = pa_cfg(name, preset)
%PA_CFG  光声成像统一配置入口（单一真源 Single Source of Truth）
%
%   cfg = pa_cfg(name)
%   cfg = pa_cfg(name, preset)
%
%   目的：终结"同一批实验被不同脚本赋予不同几何/滤波/声速参数"的混乱.
%   所有下游脚本（预处理 / 成像 / 指标 / 出图）一律从本函数取参数，
%   不得再在脚本内硬编码 vs / fs / R / f_low / f_high.
%
%   输入
%     name   : 数据源标识（可在 cfg.dataDir 覆盖实际路径）
%              'own1'     自有 128 阵元半环阵  data1  单根细钨丝（点状）
%              'own2'     自有 128 阵元半环阵  data2  两根细钨丝（并排）
%              'own4'     自有 128 阵元半环阵  data4  两根交叉细钨丝（X 形）
%              'own3'     自有旋转探测器 200 步  data3
%              'own5'     自有旋转探测器 1440 步 data5  环形/管状仿体
%              'own6'     自有旋转探测器 1440 步 data6  两根不同深度钨丝
%              'oadat_sc'  OADAT 半环阵 256 元  SWFD_semicircle
%              'oadat_ms'  OADAT 多段阵列        SWFD/MSFD multisegment
%              'oadat_scd' OADAT 仿真            SCD（含 ground_truth）
%     preset : 'unified' 默认，滤波类型/阶数/是否平滑一律对齐 OADAT 官方口径
%              'legacy'  逐项还原原脚本的链（阶数4/补边/abs/转置），
%                        用于验证新管线与 image*/ 归档结果可复现
%              'oadat'   强制 0.1-6 MHz + vs 1510 m/s + 逐通道去均值
%              'own'     完全沿用各设备条目自带参数，不做覆盖
%              'legacy' 逐项还原原脚本的链（滤波器阶数/补边/abs/转置，
%                       用于验证新管线与 image*/ 归档结果可复现）
%              'oadat'  对齐 OADAT 官方口径（0.1-6 MHz,order 3,去均值）
%
%   ! 本次核实的重要更正值（2026-10-14 二次核实，来自原脚本参数区）
%     (1) data5 与 data6 的探测半径差 3.1 倍 **不是笔误**：
%        data5 -> dtcr = 17.49 mm（PAI_FBP_5.m L38 / fei_rec.m L11）
%        data6 -> dtcr = 54.28 mm（DAS_Squared_6/7,PAI_FBP_6_DAS）
%        两者是**两套不同的旋转扫描装置**，故拆成 own5 / own6 两个条目.
%     (2) **所有旋转扫描数据的成像区一律为 18 mm x 18 mm**，以旋转中心为
%        中心（原脚本 realAB = 18）.此前误按 1.6R 推断视场，必须更正.
%     (3) 128 阵元半环阵：X = Y = 1000 像素，dx = 0.04 mm -> 视场 40 mm.
%
%   字段说明
%     ---- 几何 / 采集 ----
%     N          换能器阵元数（旋转扫描为角度步数）
%     R          探测半径 (m)（旋转扫描为旋转半径）
%     vs         声速 (m/s)
%     fs         采样率 (Hz)
%     nSamples   每通道采样点数（[] = 运行时推断）
%     FOV        成像视场边长 (m)
%     Nx         图像像素数（方形）
%
%     ---- 预处理 ----
%     dcMethod   去直流方式：'median'（默认，抗脉冲）| 'mean'（OADAT 口径）
%                'firstN'   仅前 N 点中位数（原 128 阵元脚本的旧做法）
%     f_low      带通下限 (Hz)
%     f_high     带通上限 (Hz)
%     f_order    Butterworth 阶数
%     padLen     filtfilt 补边（[] = 自动；0 = OADAT 原样）
%     smooth     解调后平滑窗长（样本数；1 = 关闭）
%     f0         探头中心频率 (Hz)，用于平方律检波(D2')的低通截止
%
%     ---- 解调 / 成像 ----
%     demod      'env'   D1  = |hilbert(x)|        线性包络（基线 I_C）
%                'env2'  D1^2                      包络平方（现有主方法）
%                'sqlaw' D2' = LPF(x.^2)           平方律检波（免 Hilbert，推荐）
%                'sq'    D2  = x.^2                裸平方（仅作缺陷对照）
%     filt       'none' | 'ramp'     时域滤波（ramp = 斜坡xHamming，FBP）
%     takeAbs    反投影后是否取绝对值
%     comp       'r'  | 'r2'  | 'none'   反投影距离权重
%
%     ---- 显示 ----
%     WL, WW     CT 式窗位/窗宽（归一化 [0,1] 域）
%
%   版本：v2  2026-10-14（更正视场与探测半径）

if nargin < 2 || isempty(preset), preset = 'unified'; end

cfg = struct();
cfg.name   = lower(name);
cfg.preset = preset;

% 默认值（各条目可覆盖）
cfg.dcMethod  = 'median';
cfg.dcFirstN  = 100;
cfg.padLen    = [];
cfg.filt      = 'none';
cfg.takeAbs   = false;
cfg.bandwidth = NaN;

switch cfg.name

    % ================================================================
    %  自有 128 阵元半环阵  data1 / data2 / data4
    %  几何来源：PAI_FBP_1_V2.m L40-45,Fhb_code.m L41-43
    % ================================================================
    case {'own1', 'own2', 'own4', 'own128', 'data1', 'data2', 'data4'}
        cfg.name      = 'own128';
        cfg.arrayType = 'semicircle128';
        cfg.N         = 128;
        cfg.R         = 55e-3;
        cfg.vs        = 1478;        % 原脚本统一使用
        cfg.fs        = 40e6;
        cfg.nSamples  = [];
        cfg.FOV       = 40e-3;       % X=1000 px x dx=0.04 mm
        cfg.Nx        = 1000;
        cfg.f0        = 5e6;
        cfg.bandwidth = 0.60;

        cfg.f_low     = 0.5e6;
        cfg.f_high    = 15e6;
        cfg.f_order   = 4;

        cfg.comp      = 'r';
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    % ================================================================
    %  自有旋转探测器 200 步  data3
    %  几何来源：rec_code_fu.m L11-18,PAI_FBP_3.m L33-39
    % ================================================================
    case {'own3', 'ownrot200', 'data3'}
        cfg.name      = 'ownrot200';
        cfg.arrayType = 'rotational';
        cfg.N         = 200;
        cfg.R         = 16.02e-3;
        cfg.vs        = 1500;        % 原脚本以 1.5 mm/us 记
        cfg.fs        = 100e6;
        cfg.nSamples  = 3200;
        cfg.FOV       = 18e-3;       % realAB = 18 mm（固定）
        cfg.Nx        = 601;
        cfg.f0        = 5e6;
        cfg.bandwidth = 0.60;

        cfg.f_low     = 0.5e6;
        cfg.f_high    = 15e6;
        cfg.f_order   = 4;

        cfg.comp      = 'r2';        % 旋转单通道 -> 能量域须 r^2 补偿
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    % ================================================================
    %  自有旋转探测器 1440 步  data5（r = 17.49 mm）
    %  几何来源：PAI_FBP_5.m L38-44,fei_rec.m L11-17
    % ================================================================
    case {'own5', 'ownrot5', 'data5'}
        cfg.name      = 'ownrot5';
        cfg.arrayType = 'rotational';
        cfg.N         = 1440;
        cfg.R         = 17.49e-3;
        cfg.vs        = 1500;
        cfg.fs        = 100e6;
        cfg.nSamples  = 3200;
        cfg.FOV       = 18e-3;
        cfg.Nx        = 601;
        cfg.f0        = 5e6;
        cfg.bandwidth = 0.60;

        cfg.f_low     = 0.5e6;
        cfg.f_high    = 15e6;
        cfg.f_order   = 4;

        cfg.comp      = 'r2';
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    % ================================================================
    %  自有旋转探测器 1440 步  data6（r = 54.28 mm）
    %  几何来源：DAS_Squared_7_..._WITH_WINDOWING.m L51-57,PAI_FBP_6_DAS.m L45-51
    % ================================================================
    case {'own6', 'ownrot6', 'data6'}
        cfg.name      = 'ownrot6';
        cfg.arrayType = 'rotational';
        cfg.N         = 1440;
        cfg.R         = 54.28e-3;
        cfg.vs        = 1500;
        cfg.fs        = 100e6;
        cfg.nSamples  = 6400;
        cfg.FOV       = 18e-3;
        cfg.Nx        = 601;
        cfg.f0        = 5e6;
        cfg.bandwidth = 0.60;

        cfg.f_low     = 0.5e6;
        cfg.f_high    = 15e6;
        cfg.f_order   = 4;

        cfg.comp      = 'r2';
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    % ================================================================
    %  OADAT：半环阵 256 元（SWFD_semicircle）
    % ================================================================
    case {'oadat_sc', 'oadat_semicircle'}
        cfg.name      = 'oadat_sc';
        cfg.arrayType = 'semicircle256';
        cfg.N         = 256;
        % 2026-10-15 实读 oadat/oadat/arrays/ringCup.mat（v7.3，用 h5py 读）：
        %   512 阵元、半径恒为 **40.730 mm**、角度 -176.16..+176.16 deg（span 352.32）、
        %   步长 0.6758 deg，在 index 255 处有一个 **7.676 deg 的缺口**（正上方）。
        %   ⇒ 旧的 0.055 是错的（疑与自有半环阵 data1/2 的 R=55 mm 混记）。
        %   注意：本配置取**下半环 256 元子集**（几何子集，见 docs/08 §4.3）。
        cfg.R         = 0.040730;    % 实读 ringCup.mat
        cfg.vs        = 1510;        % OADAT 官方声明值
        cfg.fs        = 40e6;        % ! 待与官方 fSampling 对齐（docs/05 阻塞项）
        cfg.nSamples  = 2030;
        cfg.FOV       = 22e-3;       % 官方重建网格（待核；见 docs/05）
        cfg.Nx        = 256;
        cfg.f0        = 5e6;
        cfg.bandwidth = 0.60;

        cfg.f_low     = 0.1e6;
        cfg.f_high    = 6e6;
        cfg.f_order   = 3;
        cfg.smooth    = 1;

        cfg.comp      = 'r';
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    % ================================================================
    %  OADAT：多段阵列（SWFD/MSFD multisegment，含 128 元线阵）
    % ================================================================
    case {'oadat_ms', 'oadat_multisegment'}
        cfg.name      = 'oadat_ms';
        cfg.arrayType = 'multisegment';
        cfg.N         = 256;
        % 实读 multisegmentCup.mat：256 阵元、半径**不恒定** 35.477..40.510 mm
        % （均值 38.596，std 2.057）、角度 5.36..174.64 deg（span 169.28）、
        % 步长 0.3401 deg，在 index 63 处有 6.189 deg 缺口。
        % ⇒ 旧的 0.055 是错的；且本阵列**非等半径**，单一 cfg.R 只是等效近似。
        cfg.R         = 0.038596;    % 实测均值（等效半径）
        cfg.vs        = 1510;
        cfg.fs        = 40e6;
        cfg.nSamples  = 2030;
        cfg.FOV       = 22e-3;
        cfg.Nx        = 256;
        cfg.f0        = 7.5e6;
        cfg.bandwidth = 0.70;

        cfg.f_low     = 0.1e6;
        cfg.f_high    = 6e6;
        cfg.f_order   = 3;
        cfg.smooth    = 1;

        cfg.comp      = 'r';
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    % ================================================================
    %  OADAT：临床仿真（SCD，含 ground_truth）
    % ================================================================
    case {'oadat_scd', 'scd'}
        cfg.name      = 'oadat_scd';
        cfg.arrayType = 'ring1024';
        cfg.N         = 1024;
        % 实读 virtualRingCup.mat：1024 阵元、半径恒 **40.600 mm**、
        % 角度 -179.82..+179.82 deg（span 359.65）、步长 0.3516 deg（近 360 度全覆盖）。
        cfg.R         = 0.040600;    % 实读 virtualRingCup.mat
        cfg.vs        = 1510;
        cfg.fs        = 40e6;
        cfg.nSamples  = 2030;
        cfg.FOV       = 22e-3;
        cfg.Nx        = 256;
        cfg.f0        = 7.5e6;
        cfg.bandwidth = 0.70;

        cfg.f_low     = 0.1e6;
        cfg.f_high    = 6e6;
        cfg.f_order   = 3;
        cfg.smooth    = 1;

        cfg.comp      = 'r';
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    % ================================================================
    %  PATATO：在体小鼠（iThera MSOT inVision）
    %  几何来源：data_ext/invivo_oe.hdf5 的 GEOMETRY 数据集（256 x 3）
    %  实测（2026-10-14，逐阵元核实）：
    %    半径恒 40.500 mm；256 元**均匀间隔 1.0547 deg**；
    %    占据弧长 **267.9 deg**，在 **-135.53 deg .. -44.47 deg**
    %    （即正下方 ±45.5 deg 扇形）留 **91.0 deg 缺口** -> 有限视角阵列
    %  ! 必须用 GEOMETRY 实测坐标（经 SensorPos 透传），
    %    不可按"均匀半圆/整圆"用 R 与角度生成，否则几何错位。
    %  采集：fs = 40 MHz、vs = 1469 m/s（文件 attrs）、2030 采样；
    %        10 个波长 700/730/750/760/770/800/820/840/850/880 nm
    %  注意：官方重建网格为 333 x 333（视场约 30 mm，px 0.0904 mm）
    % ================================================================
    case {'patato_mouse', 'patato'}
        cfg.name      = 'patato_mouse';
        cfg.arrayType = 'arc267';    % 自定义：阵元坐标由 SensorPos 显式给定
        cfg.N         = 256;
        cfg.R         = 40.5e-3;
        cfg.vs        = 1469;        % 文件 attrs['speedofsound']
        cfg.fs        = 40e6;        % 文件 attrs['fs']
        cfg.nSamples  = 2030;
        cfg.FOV       = 32e-3;       % 核验时与官方 30 mm 网格对齐
        cfg.Nx        = 321;
        cfg.f0        = 3.2e6;       % 实测带中心（去慢漂移后 -6 dB 带 [0.43, 5.97] MHz）
        cfg.bandwidth = 0.80;

        cfg.f_low     = 3.2e6 * (1 - 0.80/2);   % 1.92 MHz
        cfg.f_high    = 3.2e6 * (1 + 0.80/2);   % 4.48 MHz
        cfg.f_order   = 3;

        cfg.comp      = 'r';
        cfg.WL        = 0.15;  cfg.WW = 0.70;

    otherwise
        error('pa_cfg:unknownName', '未知数据源标识：%s', name);
end

% 缺省填充
if ~isfield(cfg, 'smooth'), cfg.smooth = 5; end
if ~isfield(cfg, 'owndir'),  cfg.owndir = '';  end

% ------------------------------------------------------------------
%  Q8 标称–实测频率一致性（配置完整性闸门）
%
%  判据：**实测带中心 / 探头数据手册标称中心 ∈ [0.5, 2.0]**。
%  不满足说明配置设错（绝大多数情形是标称 f0 与换能器实际不符），
%  而非方法失效 —— 这正是 docs/06 §4 记录的那件事：
%  自有 6 组里有 3 组（data3/data5/data6）在"标称 5 MHz"下不成立，
%  按实测带中心回填后全部通过。
%
%  · cfg.f0Spec  —— 换能器**数据手册标称**中心频率（本函数给定，不随运行时覆盖改变）
%  · cfg.f0_meas —— 由 pa_band_audit 从数据实测的带中心（pa_wire_run 计算）
%  两者之比即 Q8 比值；闸门在配置阶段施加（见 docs/06 §4 与 Methods）。
% ------------------------------------------------------------------
cfg.f0Spec = cfg.f0;

% 平方律（D2'）合法带宽上限：beta_law = B/f0 < 1 才允许"平方+低通"免 Hilbert。
% 取 0.80 留 20% 余量（应对滤波器过渡带）；BandMode='spec' 用它构造窄带。
if ~isfield(cfg, 'bw_law'), cfg.bw_law = 0.80; end

% ------------------------------------------------------------------
%  preset 覆盖
% ------------------------------------------------------------------
switch lower(preset)

    case 'oadat'
        cfg.f_low    = 0.1e6;
        cfg.f_high   = 6e6;
        cfg.f_order  = 3;
        cfg.dcMethod = 'mean';
        cfg.smooth   = 1;
        cfg.vs       = 1510;      % ! 仅当介质确为水/组织时成立
        cfg.padLen   = [];        % 用 MATLAB 自动补边（比 OADAT 的 0 更稳）

    case 'legacy'
        % 逐项还原各原脚本的行为，用于验证复现
        if cfg.R == 55e-3                       % 128 阵元族
            cfg.dcMethod = 'firstN';            % 原：减前 100 点中位数
            cfg.dcFirstN = 100;
            cfg.f_order  = 4;
            cfg.smooth   = 5;
            cfg.filt     = 'ramp';
            cfg.takeAbs  = true;
            cfg.comp     = 'r';
        else                                    % 旋转扫描族
            cfg.dcMethod = 'median';
            cfg.f_order  = 4;
            cfg.smooth   = 5;
            cfg.filt     = 'none';
            cfg.takeAbs  = false;
            cfg.comp     = 'r2';                % DAS_Squared_7 的 xr^2
        end

    case 'unified'
        % ------------------------------------------------------------
        %  统一流程（默认）：滤波类型与阶数、解调后是否平滑，
        %  一律对齐 OADAT 官方口径，跨数据集可比。
        %  · 带通：零相位 Butterworth，order 3（OADAT 官方值）
        %  · 解调后不平滑（OADAT 不做）；平滑会掩盖 D2' 的 2f0 残留，
        %    使"免 Hilbert 一致性"被高估，故关闭
        %  · 去直流：中位数（比 OADAT 的均值更抗脉冲），差异在 docs/06 声明
        %  · filt/takeAbs 关闭：斜坡滤波与 abs 属 FBP 变体，不进统一主链
        % ------------------------------------------------------------
        cfg.f_order  = 3;
        cfg.smooth   = 1;
        cfg.dcMethod = 'median';
        cfg.padLen   = [];
        cfg.filt     = 'none';
        cfg.takeAbs  = false;
        % comp 保持各阵列条目自身的设置（半环 'r'，旋转 'r2'）

    case 'own'
        % 不改动

end

% ------------------------------------------------------------------
%  派生量
% ------------------------------------------------------------------
cfg.nyquist   = cfg.fs / 2;
cfg.dx        = cfg.FOV / (cfg.Nx - 1);
cfg.beta_wide = (cfg.f_high - cfg.f_low) / cfg.f0;

% ------------------------------------------------------------------
%  平方律检波（D2'）的合法性判据 ---- 2026-10-14 二次修正（因子 2 错误）
%
%  设 x(t) = Re{ z(t) * exp(j*2*pi*f0*t) }，z 为复包络，单边带宽 W = B/2，
%  B = f_high - f_low 为射频带宽。则
%        x^2 = (1/2)|z|^2 + (1/4)( z^2 * exp(j*4*pi*f0*t) + c.c. )
%  · 基带项 (1/2)|z|^2 : |z|^2 的单边带宽为 2W = B，占据 [0, B]
%  · 二倍频项          : 占据 [2f0-2W, 2f0+2W] = [2*f_low, 2*f_high]
%
%  两者不重叠  <=>  B < 2*f_low  <=>  f_high < 3*f_low  <=>  beta = B/f0 < 1
%  合法低通截止区间 = ( B , 2*f_low )
%
%  ! 旧版本把下限误写成 B/2、上限误写成 2f0-B/2，等于把判据放松了整整一倍
%    （允许 B 一直大到 2*f0）。本次修正为 B 与 2*f_low.
%  ! 该判据约束的是"用 LPF(x^2) 免去 Hilbert"这一**实现捷径**；
%    能量成像本身 I_E = sum_m |z_m|^2 对任意带宽都成立，二者不可混淆.
% ------------------------------------------------------------------
B_rf = cfg.f_high - cfg.f_low;
cfg.beta_rf      = B_rf / cfg.f0;
cfg.sqlaw_lo_cut = B_rf;                 % 合法截止下限 = 射频带宽 B
cfg.sqlaw_hi_cut = 2 * cfg.f_low;        % 合法截止上限 = 2*f_low
cfg.sqlaw_ok     = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;

% D2' 低通截止：优先取合法区间中点；不合法时退回 f0 并交由窄带化处理
if cfg.sqlaw_ok
    cfg.lp_cutoff = 0.5 * (cfg.sqlaw_lo_cut + cfg.sqlaw_hi_cut);
else
    cfg.lp_cutoff = cfg.f0;
end

% 分析带过宽（区间为空）时给出的窄带化建议：以 f0 为中心,+-50% f0
if ~cfg.sqlaw_ok
    cfg.sqlaw_narrowband = [0.5*cfg.f0, 1.5*cfg.f0];
else
    cfg.sqlaw_narrowband = [cfg.f_low, cfg.f_high];
end

end
