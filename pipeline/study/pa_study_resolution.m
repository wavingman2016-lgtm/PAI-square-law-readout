function R = pa_study_resolution(varargin)
%PA_STUDY_RESOLUTION  受控仿真：单点 PSF 与双点 Rayleigh 分辨（"主流 vs 本文"）
%
%   目的（回答一个具体问题）
%     "FWHM 缩小" 是否等于 "分辨率提升"？
%     把两个候选解释分开检验：
%       H1（数学必然/度量伪影）: I_E 的半高宽 == 探测域幅度包络的 -3dB 宽度，
%                                 而 I_M 的半高宽 == 同一条包络的 -6dB 宽度。
%                                 => 换个读数电平而已，信息不变。
%       H2（真实分辨增益）:       双点凹陷比在能量域更好。
%
%   方法
%     环形/半环阵列，合成窄带光声信号（Gabor 脉冲，beta<1）
%     双臂共用同一前处理与同一反投影核，仅"检波算子"不同：
%       Arm M（主流）: Hilbert -> |z|    -> 反投影，几何补偿 r
%       Arm E（本文）: x^2 -> 低通 -> 1/2|z|^2 -> 反投影，几何补偿 r^2
%     另加 Arm SQ（裸平方，反例）：x^2（无低通、无去直流）-> 反投影
%       （v0.22 改名：旧称 "Arm B" 与图像域平方 I_BS 的简称 B 冲突；稿内定为 SQ=裸平方、BS=图像域平方。）
%
%   实验
%     E1 单点 PSF：中心单个吸收点，量各电平宽度、CNR/gCNR/PSR
%     E2 双点扫描：间距 d 从 0.3mm 扫到 4mm，量 Rayleigh 凹陷比
%     E3 对比度阶梯：强点+弱点并排，量弱点是否被牺牲
%
%   可选参数
%     'Array'  'semicircle128'（默认，同 W1）| 'ring256'
%     'SNR'    弱信号通道相对噪声的幅度信噪比（默认 40 dB）
%     'Save'   是否存盘（默认 true）
%     'OutDir' 输出目录
%
%   版本：v1  2026-10-14

opt.Array       = 'semicircle128';
opt.SNR         = 40;          % dB，作用于目标回声幅度
opt.Regime      = 'noise';     % 'noise'  仅白噪声（独立噪声域）
                               % 'clutter' 叠加视场外强吸收体（通道间相关杂波域）
opt.SkipSweeps  = false;       % true 时只做 E1（用于几何 x 体制 的快速扫描）
opt.Nx          = 801;
opt.Nrep        = 4;           % 独立噪声实现数（MEMORY §5.2：单次实现不可用）
opt.Save        = true;
opt.OutDir      = '';
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot   = fileparts(fileparts(mfilename('fullpath')));
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', ...
                          sprintf('study_%s_%s', opt.Array, opt.Regime));
end

fprintf('\n==== pa_study_resolution : %s | regime=%s | Nx=%d | Nrep=%d ====\n', ...
        opt.Array, opt.Regime, opt.Nx, opt.Nrep);

% ==================================================================
%  1. 几何与信号参数（全部显式，便于论文复现）
% ==================================================================
P              = struct();
P.fs           = 40e6;        % 采样率
P.nSamples     = 4096;        % 同 data1
P.vs           = 1478;        % 同自有 128 阵元
P.f0           = 5e6;         % 换能器中心频率
P.beta_sig     = 0.60;        % 信号 -6dB 相对带宽 = 0.60（<1，窄带条件成立）
P.bw_law       = 0.80;        % 分析带构造律：f0(1 +- 0.4) -> B/f0 = 0.8 < 1
P.R            = 55e-3;
P.FOV          = 40e-3;
P.Nx           = opt.Nx;
P.Regime       = opt.Regime;

switch lower(opt.Array)
    case 'semicircle128'
        P.arrayType = 'semicircle128';  P.N = 128;
    case 'ring256'
        P.arrayType = 'ring1024';       P.N = 256;   % 全圆
    otherwise
        error('pa_study_resolution:array', '未知阵列：%s', opt.Array);
end

% 分析带：按 bw_law 构造合法窄带（beta = 0.8 < 1）
P.f_low  = P.f0 * (1 - P.bw_law/2);
P.f_high = P.f0 * (1 + P.bw_law/2);

cfg = build_cfg(P);

% 阵元坐标（与 pa_backproject 内部约定一致）
[sx, sy] = local_sensor_positions(P);

fprintf('  几何 %s, N=%d, R=%.1f mm, vs=%d m/s\n', P.arrayType, P.N, P.R*1e3, P.vs);
fprintf('  信号 f0=%.2f MHz, -6dB beta=%.2f ; 分析带 [%.2f %.2f] MHz, beta_band=%.2f\n', ...
        P.f0/1e6, P.beta_sig, P.f_low/1e6, P.f_high/1e6, (P.f_high-P.f_low)/P.f0);
fprintf('  视场 %.0f mm, Nx=%d, dx=%.3f mm\n', P.FOV*1e3, P.Nx, P.FOV/(P.Nx-1)*1e3);

% ==================================================================
%  2-4. E1 单点 PSF / E2 双点 Rayleigh / E3 对比度阶梯（**Nrep 次独立实现**）
%
%  重复化理由（MEMORY §5.2）：单次随机实现不可用——噪声/相位轴方差大，
%  宽度与凹陷比的单次值不能作为论文数字。图像（IC/IM/IE/IB）体积大，
%  **只保留第 1 次实现**用于出图；所有标量宽度/指标保留全部 Nrep 次，
%  报 均值±SD（E2/E3 逐点先算后平均，阈值判定用均值曲线）。
% ==================================================================
dList   = [0.3 0.4 0.5 0.6 0.8 1.0 1.3 1.6 2.0 2.5 3.0 4.0] * 1e-3;
epsList = [1 0.5 0.2 0.1 0.05];
nD = numel(dList); nEp = numel(epsList); Nr = opt.Nrep;

% 逐次实现的标量累积（图像体积大，只留第 1 次实现用于出图）
W.fwhmC= nan(Nr,1); W.fwhmM= nan(Nr,1); W.fwhmE= nan(Nr,1);
W.w3env= nan(Nr,1); W.fwhmSqrtE= nan(Nr,1); W.fwhmB= nan(Nr,1);
MC= nan(Nr,4); MM= nan(Nr,4); ME= nan(Nr,4); MB= nan(Nr,4);   % [CNR gCNR PSR DR]
DIP = nan(Nr,3,nD); SEP = nan(Nr,3,nD);                        % 臂序 C,M,E
RAT = nan(Nr,3,nEp);
R1  = [];

fprintf('\n---- E1 单点 PSF（%d 次实现）----\n', Nr);
for ir = 1:Nr
    rng(7 + 1000*ir);
    sig1 = local_synth(P, [0 0], 1, sx, sy, opt.SNR);
    r1   = local_dual_arm(sig1, cfg, P);
    if ir == 1, R1 = r1; local_print_single(r1); end
    w = r1.widths;
    W.fwhmC(ir)= w.fwhmC;   W.fwhmM(ir)  = w.fwhmM;  W.fwhmE(ir)   = w.fwhmE;
    W.w3env(ir) = w.w3_env; W.fwhmSqrtE(ir)= w.fwhmSqrtE; W.fwhmB(ir)= w.fwhmB;
    MC(ir,:) = [r1.mC.CNR r1.mC.gCNR r1.mC.PSR r1.mC.DR];
    MM(ir,:) = [r1.mM.CNR r1.mM.gCNR r1.mM.PSR r1.mM.DR];
    ME(ir,:) = [r1.mE.CNR r1.mE.gCNR r1.mE.PSR r1.mE.DR];
    MB(ir,:) = [r1.mB.CNR r1.mB.gCNR r1.mB.PSR r1.mB.DR];
    fprintf('  rep %d/%d: FWHM C=%.4f M=%.4f E=%.4f | w-3dB(env)=%.4f | gCNR C=%.4f M=%.4f E=%.4f\n', ...
            ir, Nr, w.fwhmC, w.fwhmM, w.fwhmE, w.w3_env, r1.mC.gCNR, r1.mM.gCNR, r1.mE.gCNR);
end

fprintf('\n---- E1 汇总（均值±SD, Nrep=%d）----\n', Nr);
fprintf('  %-18s %10s %10s\n', 'quantity', 'mean', 'SD');
Wsum = struct();
wn = {'fwhmC','fwhmM','fwhmE','w3env','fwhmSqrtE','fwhmB'};
wl = {'FWHM(I_C)','FWHM(I_M)','FWHM(I_E)','w-3dB(env)','FWHM(sqrt I_E)','FWHM(I_B)'};
for i = 1:numel(wn)
    v = W.(wn{i});
    fprintf('  %-18s %10.4f %10.4f\n', wl{i}, mean(v), std(v,0));
end
% 注意：不能用 mn{a}(:,:) —— mn 是**字符串元胞数组**，切片只会得到字符片段。
% 直接用 switch 取矩阵，避免元胞/字符串歧义。
ml = {'C','M','E','SQ'};
mx = {MC, MM, ME, MB};
fprintf('  指标（三臂，均值±SD）\n');
for a = 1:4
    x = mx{a};
    fprintf('    %s: CNR %.3f±%.3f  gCNR %.4f±%.4f  PSR %.3f±%.3f  DR %.3f±%.3f\n', ...
        ml{a}, mean(x(:,1)), std(x(:,1),0), mean(x(:,2)), std(x(:,2),0), ...
        mean(x(:,3)), std(x(:,3),0), mean(x(:,4)), std(x(:,4),0));
end

% ---------- E2 ----------
if ~opt.SkipSweeps
    fprintf('\n---- E2 双点分离扫描（三臂 C/M/E，%d 次实现）----\n', Nr);
    for ir = 1:Nr
        for i = 1:nD
            d = dList(i);
            pts = [-d/2 0; d/2 0];
            rng(20000 + 1000*ir + i);
            sig = local_synth(P, pts, [1 1], sx, sy, opt.SNR);
            r   = local_dual_arm(sig, cfg, P);
            [DIP(ir,1,i), SEP(ir,1,i)] = local_rayleigh(r.profC, r.ax);
            [DIP(ir,2,i), SEP(ir,2,i)] = local_rayleigh(r.profM, r.ax);
            [DIP(ir,3,i), SEP(ir,3,i)] = local_rayleigh(r.profE, r.ax);
        end
        fprintf('  rep %d/%d 完成\n', ir, Nr);
    end
    fprintf('  d(mm) | dip C / M / E（均值±SD）\n');
    for i = 1:nD
        fprintf('  %5.2f | %.3f±%.3f  %.3f±%.3f  %.3f±%.3f\n', dList(i)*1e3, ...
            mean(DIP(:,1,i)), std(DIP(:,1,i),0), ...
            mean(DIP(:,2,i)), std(DIP(:,2,i),0), ...
            mean(DIP(:,3,i)), std(DIP(:,3,i),0));
    end
end
E2 = struct('d_mm', dList*1e3, 'dip', DIP, 'sep', SEP, 'Nrep', Nr);

% ---------- E3 ----------
if ~opt.SkipSweeps
    fprintf('\n---- E3 对比度阶梯（强点 A=1 与弱点 A=eps，三臂，%d 次实现）----\n', Nr);
    for ir = 1:Nr
        for i = 1:nEp
            e = epsList(i);
            pts = [-1.5e-3 0; 1.5e-3 0];
            rng(30000 + 1000*ir + i);
            sig = local_synth(P, pts, [1 e], sx, sy, opt.SNR);
            r   = local_dual_arm(sig, cfg, P);
            pk = local_two_peak_heights(r.profC, r.ax); RAT(ir,1,i) = pk(2)/pk(1);
            pk = local_two_peak_heights(r.profM, r.ax); RAT(ir,2,i) = pk(2)/pk(1);
            pk = local_two_peak_heights(r.profE, r.ax); RAT(ir,3,i) = pk(2)/pk(1);
        end
        fprintf('  rep %d/%d 完成\n', ir, Nr);
    end
    fprintf('  eps | read-out ratio C / M / E（均值±SD）\n');
    for i = 1:nEp
        fprintf('  %5.2f | %.4f±%.4f  %.4f±%.4f  %.4f±%.4f  (identity=%.2f)\n', epsList(i), ...
            mean(RAT(:,1,i)), std(RAT(:,1,i),0), ...
            mean(RAT(:,2,i)), std(RAT(:,2,i),0), ...
            mean(RAT(:,3,i)), std(RAT(:,3,i),0), epsList(i));
    end
end
E3 = struct('eps', epsList, 'ratio', RAT, 'Nrep', Nr);

W.MC = MC; W.MM = MM; W.ME = ME; W.MB = MB; W.Nrep = Nr;

% ==================================================================
%  5. 结论判定（全部用 Nrep 均值，不用第 1 次实现）
% ==================================================================
fprintf('\n---- 判定 ----\n');
mE_fwhm = mean(W.fwhmE); m3_env = mean(W.w3env);
fprintf('  H1（度量伪影）: FWHM(I_E)=%.4f±%.4f mm, env 的 -3dB 宽=%.4f±%.4f mm -> 相对差 %.2f%%\n', ...
        mE_fwhm, std(W.fwhmE,0), m3_env, std(W.w3env,0), ...
        100*abs(mE_fwhm-m3_env)/max(m3_env,eps));
mS = mean(W.fwhmSqrtE); mM = mean(W.fwhmM);
fprintf('                 FWHM(sqrt(I_E))=%.4f±%.4f mm vs FWHM(I_M)=%.4f±%.4f mm -> 相对差 %.2f%%\n', ...
        mS, std(W.fwhmSqrtE,0), mM, std(W.fwhmM,0), ...
        100*abs(mS-mM)/max(mM,eps));
fprintf('  H2（真实分辨）: 最小可分辨间距（双点凹陷 > 0.05，均值曲线）\n');
dipMean = squeeze(mean(DIP, 1));      % 3 x nD
fprintf('                 C: %.2f mm   M: %.2f mm   E: %.2f mm\n', ...
        local_min_sep(E2.d_mm, dipMean(1,:)), local_min_sep(E2.d_mm, dipMean(2,:)), ...
        local_min_sep(E2.d_mm, dipMean(3,:)));
gC = mean(W.MC(:,2)); gM = mean(W.MM(:,2)); gE = mean(W.ME(:,2));
fprintf('  单点gCNR      : C=%.4f±%.4f  M=%.4f±%.4f  E=%.4f±%.4f\n', ...
        gC, std(W.MC(:,2),0), gM, std(W.MM(:,2),0), gE, std(W.ME(:,2),0));
fprintf('                  d(E-C) = %+.4f   d(E-M) = %+.4f\n', gE-gC, gE-gM);
ratMean = squeeze(mean(RAT, 1));      % 3 x nEp
fprintf('  对比度阶梯保真: E臂 读出比/理想 = %.3f~%.3f（1.0 为完全保真）\n', ...
        min(ratMean(3,:) ./ epsList), max(ratMean(3,:) ./ epsList));

R = struct('P', P, 'cfg', cfg, 'R1', R1, 'E2', E2, 'E3', E3, 'W', W);

% ==================================================================
%  6. 存盘与出图
% ==================================================================
if opt.Save
    if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end
    local_plot(R, opt.OutDir);
    save(fullfile(opt.OutDir, 'study_resolution.mat'), '-struct', 'R', '-v7.3');
    fprintf('\n  [out] %s\n', opt.OutDir);
end
end

% ==================================================================
%  双臂：同一前处理 + 同一反投影核，仅检波算子不同
% ==================================================================
function r = local_dual_arm(sig, cfg, P)
D = pa_preprocess(sig, cfg, 'Methods', {'env','env2','sqlaw','sq'});

% Arm C（经典相干反投影，FBP 口径）：复数解析信号求和后取模，comp = r
Z  = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2)
    Z(:,ch) = hilbert(D.filtered(:,ch));
end
IC = local_backproject_complex(Z, cfg, P, 'r');

% Arm M（本项目基线口径）：通道级线性包络叠加 + r 补偿
IM = pa_backproject(D.env,   cfg, 'Comp', 'r',  'Nx', P.Nx, 'FOV', P.FOV, 'Normalize', 'none');
% Arm E（本文）：平方律检波（含低通、去直流）+ 同一 r 补偿
% 补偿口径（docs/09 §3.8.3 / MEMORY §1）：**只有 g_m = d_m/R**。曾用 r^2，
% 但 E_r 消融证明 E(r)/E(r^2) 宽度比 = 1.000（差 0.05 %），r^2 非独立参数，
% 且"宽度来自 r^2 收缩孔径"的机制解释已被否证 => 全文统一用 r。
IE = pa_backproject(D.sqlaw, cfg, 'Comp', 'r',  'Nx', P.Nx, 'FOV', P.FOV, 'Normalize', 'none');
% Arm SQ（反例）：裸平方（无低通 / 无去直流）
IB = pa_backproject(D.sq,    cfg, 'Comp', 'r',  'Nx', P.Nx, 'FOV', P.FOV, 'Normalize', 'none');

ax = ((1:P.Nx) - P.Nx/2) * (P.FOV/(P.Nx-1)) * 1e3;   % mm
[~, i0] = min(abs(ax));

profC = IC(i0, :).';   % 相干（复数求和取模）
profM = IM(i0, :).';   % 包络叠加
profE = IE(i0, :).';
profB = IB(i0, :).';

% 幅度域归一（便于与 M 同尺度比较）
profEa = sqrt(max(profE, 0));

% 指标（在幅度域算，背景取两侧 25%~45% 的位置；ROI 固定，不随方法变化）
roi = local_roi(ax, 0.9, [0.25 0.45]);
mC = local_metrics(profC, ax, roi);
mM = local_metrics(profM, ax, roi);
mE = local_metrics(profEa, ax, roi);
mB = local_metrics(sqrt(max(profB,0)), ax, roi);

% 各电平宽度（对"幅度量"）
w = struct();
w.fwhmC    = local_width(ax, profC,   0.5);
w.fwhmM    = local_width(ax, profM,    0.5);
w.fwhmE    = local_width(ax, profE,    0.5);              % I_E 的半高宽（原口径）
w.w3_env   = local_width(ax, profM,    1/sqrt(2));        % env 的 -3dB 宽度
w.fwhmSqrtE= local_width(ax, profEa,   0.5);              % sqrt(I_E) 的半高宽
w.fwhmB    = local_width(ax, profB,    0.5);
w.peakC = max(profC); w.peakM = max(profM); w.peakE = max(profE); w.peakB = max(profB);

r = struct('IC', IC, 'IM', IM, 'IE', IE, 'IB', IB, 'ax', ax, ...
           'profC', profC, 'profM', profM, 'profE', profE, 'profB', profB, 'profEa', profEa, ...
           'mC', mC, 'mM', mM, 'mE', mE, 'mB', mB, 'widths', w);
end

function IC = local_backproject_complex(Z, cfg, P, comp)
% 复数反投影：I(r) = sum_m w_m Z_m(tau_m(r))，最后取模
Nx = P.Nx; FOV = P.FOV;
dx = FOV/(Nx-1);
qv = ((1:Nx) - Nx/2) * dx;
[XC, YC] = meshgrid(qv, qv);
[SX, SY] = local_sensor_positions(P);
nS = size(Z,1); nCh = size(Z,2);
ACC = zeros(Nx, Nx);
for ch = 1:nCh
    d = hypot(XC - SX(ch), YC - SY(ch));
    tidx  = d / cfg.vs * cfg.fs + 1;
    valid = (tidx >= 1) & (tidx <= nS);
    vr = interp1(1:nS, real(Z(:,ch)), tidx(:), 'linear', 0);
    vi = interp1(1:nS, imag(Z(:,ch)), tidx(:), 'linear', 0);
    v  = reshape(vr + 1i*vi, Nx, Nx);
    switch lower(comp)
        case 'r',  wgt = (d + 1e-6)/cfg.R;
        case 'r2', wgt = ((d + 1e-6)/cfg.R).^2;
        otherwise, wgt = ones(size(d));
    end
    ACC = ACC + v .* wgt .* valid;
end
IC = abs(ACC);
end

function local_print_single(r)
w = r.widths;
fprintf('  峰形宽度（幅度域，mm）:\n');
fprintf('    FWHM(I_C) 相干反投影 = %.4f   <- 经典 FBP\n', w.fwhmC);
fprintf('    FWHM(I_M) 包络叠加   = %.4f   <- 本项目基线\n', w.fwhmM);
fprintf('    FWHM(I_E)            = %.4f   <- 本文（= -3dB 读数）\n', w.fwhmE);
fprintf('    envM 的 -3dB 宽度     = %.4f   <- 独立算出的同一电平\n', w.w3_env);
fprintf('    FWHM(sqrt(I_E))      = %.4f   <- 把 I_E 还原到幅度域的半高宽\n', w.fwhmSqrtE);
fprintf('    FWHM(裸平方 I_B)     = %.4f   <- 反例\n', w.fwhmB);
fprintf('  指标（幅度域）:\n');
fprintf('    %-8s %8s %8s %8s\n', 'arm', 'CNR', 'gCNR', 'PSR');
fprintf('    %-8s %8.3f %8.4f %8.3f\n', 'C', r.mC.CNR, r.mC.gCNR, r.mC.PSR);
fprintf('    %-8s %8.3f %8.4f %8.3f\n', 'M', r.mM.CNR, r.mM.gCNR, r.mM.PSR);
fprintf('    %-8s %8.3f %8.4f %8.3f\n', 'E', r.mE.CNR, r.mE.gCNR, r.mE.PSR);
fprintf('    %-8s %8.3f %8.4f %8.3f\n', 'SQ', r.mB.CNR, r.mB.gCNR, r.mB.PSR);
end

% ==================================================================
%  仿真：合成通道数据
% ==================================================================
function sig = local_synth(P, pts, amps, sx, sy, snr_dB)
nCh = numel(sx);
t   = (0:P.nSamples-1).'/P.fs;

% Gabor 脉冲：-6dB 带宽 = beta_sig * f0
sigF  = P.beta_sig * P.f0 / 2.355;      % 高斯谱标准差
sigT  = 1/(2*pi*sigF);

sig = zeros(P.nSamples, nCh);

% ---- 目标 ----
sig = add_points(sig, P, t, pts, amps, sx, sy);

% ---- 体制:clutter = 视场外强吸收体（"离面强吸收体"），制造通道间相关杂波 ----
if isfield(P, 'Regime') && strcmpi(P.Regime, 'clutter')
    nCl   = 14;
    rad   = 24e-3 + 10e-3 * rand(nCl, 1);          % 24~34 mm，在 40mm 视场之外
    ang   = 2*pi * rand(nCl, 1);
    cpts  = [rad.*cos(ang), rad.*sin(ang)];
    camps = 2.0 + 3.0 * rand(nCl, 1);              % 比目标强 2~5 倍
    sig   = add_points(sig, P, t, cpts, camps, sx, sy);
end

% ---- 噪声：以最强通道的峰值回波为基准 ----
refAmp = max(vecnorm(sig, inf, 1));
sig = sig + refAmp * 10^(-snr_dB/20) * randn(size(sig));
end

function sig = add_points(sig, P, t, pts, amps, sx, sy)
nCh = numel(sx);
for k = 1:size(pts,1)
    for m = 1:nCh
        rr  = hypot(pts(k,1)-sx(m), pts(k,2)-sy(m));
        tau = rr / P.vs;
        a   = amps(k) / rr;                                  % 球面扩散 1/r
        g   = exp(-((t-tau)/(1/(2*pi*(P.beta_sig*P.f0/2.355)))).^2) .* cos(2*pi*P.f0*(t-tau));
        sig(:,m) = sig(:,m) + a * g;
    end
end
end

function [sx, sy] = local_sensor_positions(P)
N = P.N;
switch lower(P.arrayType)
    case 'semicircle128'
        ang = (0:N-1) * (pi/(N-1)) - pi;      % -pi..0（下半圆，同 pa_backproject）
    otherwise
        ang = (0:N-1) * (2*pi/N);
end
sx = P.R * cos(ang);
sy = P.R * sin(ang);
end

function cfg = build_cfg(P)
cfg = struct();
cfg.name = 'study'; cfg.arrayType = P.arrayType; cfg.N = P.N;
cfg.R = P.R; cfg.vs = P.vs; cfg.fs = P.fs; cfg.nSamples = P.nSamples;
cfg.FOV = P.FOV; cfg.Nx = P.Nx; cfg.f0 = P.f0;
cfg.f_low = P.f_low; cfg.f_high = P.f_high; cfg.f_order = 3;
cfg.smooth = 1; cfg.dcMethod = 'median'; cfg.dcFirstN = 100;
cfg.padLen = []; cfg.filt = 'none'; cfg.takeAbs = false;
cfg.comp = 'r'; cfg.bw_law = P.bw_law; cfg.WL = 0.15; cfg.WW = 0.70;
cfg.nyquist = cfg.fs/2;
B_rf = cfg.f_high - cfg.f_low;
cfg.beta_rf = B_rf/cfg.f0;
cfg.sqlaw_lo_cut = B_rf;
cfg.sqlaw_hi_cut = 2*cfg.f_low;
cfg.sqlaw_ok = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;
if cfg.sqlaw_ok
    cfg.lp_cutoff = 0.5*(cfg.sqlaw_lo_cut + cfg.sqlaw_hi_cut);
else
    cfg.lp_cutoff = cfg.f0;
end
cfg.sqlaw_narrowband = [cfg.f_low, cfg.f_high];
end

% ==================================================================
%  指标与几何工具
% ==================================================================
function roi = local_roi(ax, halfTargetMm, bgBand)
ax = ax(:).';
c  = local_peak_x(ax, 1);
roi.inMask  = abs(ax - c) <= halfTargetMm;
span        = max(abs(ax));
bgAbs       = bgBand * span;
roi.outMask = (abs(ax - c) >= bgAbs(1)) & (abs(ax - c) <= bgAbs(2));
roi.inIdx   = find(roi.inMask);
roi.outIdx  = find(roi.outMask);
end

function m = local_metrics(p, ax, roi)
p = p(:).';
if numel(p) ~= numel(ax), p = interp1(linspace(ax(1),ax(end),numel(p)), p, ax); end
pin  = p(roi.inMask);
pout = p(roi.outMask);
m.CNR  = (mean(pin) - mean(pout)) / (std(pout) + eps);
m.PSR  = max(p) / (max([pout, eps]) + eps);
m.gCNR = local_gcnr(pin, pout);
m.DR   = 20*log10((max(p)+eps)/(median(p)+eps));
m.peak = max(p);
end

function g = local_gcnr(a, b)
if isempty(a) || isempty(b), g = NaN; return; end
lo = min([a(:); b(:)]); hi = max([a(:); b(:)]);
if hi <= lo, g = 1; return; end
edges = linspace(lo, hi, 65);
pa = histcounts(a, edges); pa = pa/sum(pa);
pb = histcounts(b, edges); pb = pb/sum(pb);
g = 1 - sum(min(pa, pb));
end

function w = local_width(ax, y, lvl)
% 半高全宽（线性插值）。
% 关键：必须用"跨越阈值的相邻两点"插值。旧版 interp_cross 在两侧都不跨阈时
% 回退到 i-1..i+1，会跳过真实的下降沿、改取旁瓣上升沿 -> 强烈旁瓣的剖面
% （如 Arm C 相干 PSF）会得到错误宽度。
ax = ax(:).'; y = y(:).';
pk = max(y); if pk <= 0, w = NaN; return; end
thr = lvl*pk; n = numel(y);
[~, i0] = max(y);
L = i0;  while L > 1 && y(L) > thr,  L  = L  - 1; end
Rr = i0; while Rr < n && y(Rr) > thr, Rr = Rr + 1; end
if y(L) > thr
    xl = ax(1);
else
    xl = ax(L) + (thr - y(L)) * (ax(L+1) - ax(L)) / (y(L+1) - y(L));
end
if y(Rr) > thr
    xr = ax(n);
else
    xr = ax(Rr-1) + (thr - y(Rr-1)) * (ax(Rr) - ax(Rr-1)) / (y(Rr) - y(Rr-1));
end
w = abs(xr - xl);
end

function [dip, sep] = local_rayleigh(p, ax)
% 两峰之间的凹陷比 dip = (min(peak1,peak2) - valley)/min(peak1,peak2)
p = p(:).'; ax = ax(:).';
[pk, loc] = findpeaks(p, 'SortStr', 'descend', 'NPeaks', 2);
if numel(pk) < 2
    dip = NaN; sep = NaN; return;
end
lo = min(loc); hi = max(loc);
valley = min(p(lo:hi));
dip = (min(pk) - valley) / min(pk);
sep = abs(ax(hi) - ax(lo));
end

function pk = local_two_peak_heights(p, ax)
p = p(:).'; ax = ax(:).';
c = local_peak_x(ax, 1);
if c >= 0, sgn = [-1 1]; else sgn = [1 -1]; end
pk = [0 0];
for k = 1:2
    m = (ax - c)*sgn(k) > 0.5 & (ax - c)*sgn(k) < 3.0;   % 0.5~3 mm 侧带
    idx = find(m);
    if isempty(idx), continue; end
    pk(k) = max(p(idx));
end
end

function x = local_peak_x(ax, ~)
% 峰值位置（本研究中目标均置于中心或对称于中心，取最接近 0 的极大）
[~, i] = max(abs(ax) - 1e3);  % 占位避免未用告警
x = 0;
end

function v = local_min_sep(d_mm, dip)
v = NaN;
for i = 1:numel(dip)
    if ~isnan(dip(i)) && dip(i) > 0.05
        v = d_mm(i); return;
    end
end
% 若全程都 >0.05，取最小
if all(~isnan(dip)) && any(dip > 0.05), v = d_mm(1); end
end

function local_plot(R, outDir)
% 出图已迁移到 paper/figures/_plot_fig3_resolution.py（Python + h5py）。
% 理由（MEMORY §10）：MATLAB -batch 下headless 绘图可能挂死，且样式难统一。
% 这里只保留一个占位提示，不再生成 PNG，避免两套图并存。
fprintf('  [plot] 出图由 paper/figures/_plot_fig3_resolution.py 完成（MATLAB 侧不再出图）\n');
end

function o = parse_opts(o, varargin)
if mod(numel(varargin), 2) ~= 0, error('parse_opts:pair', '参数必须成对。'); end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o, k), error('parse_opts:unknown', '未知参数：%s', k); end
    o.(k) = varargin{i+1};
end
end
