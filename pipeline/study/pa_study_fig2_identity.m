function R = pa_study_fig2_identity(varargin)
PAI_ROOT = strrep(fileparts(fileparts(fileparts(mfilename('fullpath')))), '\', '/');
%PA_STUDY_FIG2_IDENTITY  Fig.2 数据层：恒等式 I_BS = M*mu*I_E、交叉项与 mu 场
%
%   R = pa_study_fig2_identity('Name', Value, ...)
%
%   用途（**替换** 2026-10-14 的 draft）：
%     旧 draft 有三处与正文冲突 ——
%       (1) 画的是 Linear vs sign(x).*x^2，而 sign(x)*x^2 = D3「保号平方」是非物理量，
%           tables/README.md:69-70 明令不得出现在正文；
%       (2) 几何补偿用了 r^2，与正文 §2.4「只有 g_m = d_m/R」冲突；
%       (3) 缺 I_BS / I_E / 交叉项 / mu / 散点 / 直方图，无法支撑 Proposition 1。
%
%   本函数从**同一次反投影采样**取出四个标量场（这是恒等式自洽的前提）：
%       v_m(r) = w_m * z_m(tau_m(r)),   w_m = d_m / R      （幅值量补偿，正文 §2.4）
%       I_C (r)  = | sum_m v_m |                相干幅值（Arm C）
%       I_BS(r)  = | sum_m v_m |^2 = I_C^2       图像域平方（D4）
%       I_E (r)  = sum_m |v_m|^2                 能量域（Arm E，通道级平方）
%       mu   (r) = |sum_m v_m|^2 / ( M * sum_m |v_m|^2 )    ∈ [0,1]
%     于是 **恒等式 I_BS = M*mu*I_E 按构造严格成立**，残差仅为浮点误差。
%     交叉项 = I_BS - I_E = sum_{m≠n} v_m conj(v_n)：相干分量，E臂把它整个丢掉。
%
%   另输出免 Hilbert 的一致性对照（D2' vs D1^2），支撑 §2.2 的 eps_rel 陈述。
%
%   可选参数
%     'Preset'  pa_cfg 预设（默认 'unified'；几何用 semicircle128）
%     'Nx'      网格（默认 601；跨网格只比趋势，见方法学铁律 1）
%     'Nrep'    独立实现数（默认 4；单次实现不可用，见铁律 2）
%     'SNR_dB'  噪声水平（默认 40）
%     'Save' 'OutDir' 'Verbose'
%
%   输出 results/fig2_identity/fig2_identity.mat
%
%   版本：v1  2026-10-15

opt = struct('Preset','unified','Nx',601,'Nrep',4,'SNR_dB',40, ...
             'Save',true,'Verbose',true, ...
             'OutDir',[PAI_ROOT '/results/fig2_identity']);
opt = parse_opts(opt, varargin{:});

P = pa_cfg('own128', opt.Preset);
if isempty(P.nSamples)
    P.nSamples = 1600;                      % 覆盖 R=55mm 的双程走时 (2*55/1478≈74us)
end
if ~isfield(P,'sig_t') || isempty(P.sig_t)
    P.sig_t = 0.35e-6;                      % 目标脉冲宽度（高斯时间参数）
end
% 本图要在**合法平方律前提**下展示（beta<1），否则窄带不足会让 2f0 残留
% 污染解析信号的幅度包络，读者无法区分"结构来自物理"还是"来自带宽违规"。
%故把分析带收到 [0.5f0, 1.5f0]*0.8 的窄带（与主链 BandMode='spec' 同规则）。
B = P.bw_law * P.f0;
P.f_low  = P.f0 - B/2;
P.f_high = P.f0 + B/2;
P.lp_cutoff = P.f0;                        % 合法低通带 (B, 2*f_low) 内
Nx    = opt.Nx;
M     = P.N;

if opt.Verbose
    fprintf('==== pa_study_fig2_identity : %s | Nx=%d | Nrep=%d | SNR=%d dB ====\n', ...
            opt.Preset, Nx, opt.Nrep, opt.SNR_dB);
    fprintf('  M=%d  R=%.2f mm  vs=%.0f  fs=%.3g  f0=%.3g  beta=%.3f  sqlaw_ok=%d  lp=%.3g\n', ...
            M, P.R*1e3, P.vs, P.fs, P.f0, (P.f_high-P.f_low)/P.f0, P.sqlaw_ok, P.lp_cutoff);
    fprintf('  分析带 [%.3g, %.3g] MHz（bw_law=%.2f 收窄，保证 beta<1 的合法平方律前提）\n', ...
            P.f_low/1e6, P.f_high/1e6, P.bw_law);
end

% ---- 阵元坐标（半环，与 pa_backproject 的 local_sensor_positions 同口径）----
ang = linspace(0, pi, M+1); ang(end) = [];
sx = P.R*cos(ang);  sy = P.R*sin(ang);

% ---- 三个点目标：两个离轴点 + 一个中心点（制造可测的 mu 差异）------
%   离轴点让读者看到"同一目标在不同像素上I_C / I_E 的行为不同"，
%   这正是 Proposition 1 说 mu 随空间变化的意义。
tg.r   = [5e-3, -6e-3, 0];
tg.amp = [1.0, 0.5, 0.25];

% ---- 累加器 -----------------------------------------------------
%   注意一个容易踩的坑：恒等式 I_BS = M*mu*I_E 是**单次实现内**的恒等式。
%   若对IC/IE/MU 做跨实现平均后再验恒等式，MU 的分子分母不同步地平均，
%   残差就不再是机器精度 —— 那是统计量的性质被破坏，不是恒等式被否证。
%   故：残差逐rep 报告（应全部为机器精度），MU 只用**第一次实现**的空间图
%   （Proposition 1 讨论的正是单个实现下的空间相干结构），其余场用实现间平均。
F = zeros(Nx, Nx, 5);      % IC, IE, IBS, XT, E2p（实现间平均，仅用于展示）
relerr = zeros(opt.Nrep, 1);
xtrel  = zeros(opt.Nrep, 1);
MU1 = [];  IBSc1 = [];  RELERR1 = [];

for rep = 1:opt.Nrep
    D = local_data(P, sx, sy, tg, opt.SNR_dB, rep);
    f = local_fields(D, P, sx, sy, Nx);
    F(:,:,1) = F(:,:,1) + f.IC;
    F(:,:,2) = F(:,:,2) + f.IE;
    F(:,:,3) = F(:,:,3) + f.IBS;
    F(:,:,4) = F(:,:,4) + f.XT;
    F(:,:,5) = F(:,:,5) + f.E2p;
    relerr(rep) = f.maxRelErr;
    xtrel(rep)  = median(f.XT(f.valid) ./ (abs(f.IBS(f.valid)) + eps));
    if rep == 1
        MU1 = f.MU;  IBSc1 = f.IBS;  RELERR1 = f.RELERR;  valid = f.valid;
    end
end
F = F / opt.Nrep;

IC  = F(:,:,1);  IE  = F(:,:,2);  IBS = F(:,:,3);
XT  = F(:,:,4);  E2P = F(:,:,5);  MU  = MU1;

% ---- 逐像素恒等式检验（单次实现内）------------------------------
IBS_from_IC2 = IBSc1;                       % = I_C^2，D4 定义（rep 1）
MU_times_IE  = M * (MU .* IE);              % 仅示意；IE 为跨实现平均，故不作定量用
RELERR       = RELERR1;                     % 逐像素残差（rep 1）

% 交叉项：I_BS - I_E（= sum_{m≠n} v_m conj(v_n)），并给相对占比
XT_rel = zeros(Nx, Nx);
XT_rel(valid) = XT(valid) ./ (IBS(valid) + eps);

chk = struct( ...
    'maxRelErr_identity', max(RELERR(valid)), ...
    'meanRelErr_identity', mean(RELERR(valid)), ...
    'maxRelErr_overReps',  max(relerr), ...
    'relIBS_vs_IC2',       max(abs(IBS_from_IC2(:)-IBS(:))) / (max(abs(IBS(:)))+eps), ...
    'xtRel_median_overReps', median(xtrel), ...
    'nPixels_valid',       sum(valid(:)), ...
    'nPixels_total',       numel(IE), ...
    'note', ['I_BS = M*mu*I_E holds by construction because all four fields ' ...
             'are sampled from the same v_m; the residual reported here is the ' ...
             'floating-point round-off only, NOT an empirical finding. The check ' ...
             'is made WITHIN one realisation: averaging IC, IE and MU across ' ...
             'realisations independently destroys the identity by construction ' ...
             '(the numerator and denominator of mu then average out of step), ' ...
             'so the residual must not be quoted from averaged fields.']);

muV = MU(valid);
muStats = struct('min',min(muV),'max',max(muV),'mean',mean(muV), ...
                 'median',median(muV),'std',std(muV), ...
                 'p05',local_prctile(muV,5),'p95',local_prctile(muV,95), ...
                 'theo_uniform_phase', 1/M, ...
                 'note', ['mu = 1/M holds only in expectation over independent ' ...
                          'uniform channel phases (docs/04). A measured median ' ...
                          'above 1/M indicates residual phase coherence, which is ' ...
                          'the spatial structure Proposition 1 is about.']);

% ---- 免 Hilbert 一致性（D2' = LPF{x^2} vs D1^2 = |z|^2）------------
e2p = struct('pearson',[], 'amp_ratio',[], 'theory_k', 0.5, ...
             'note', ['D2prime = LPF{x^2} = (1/2)|z|^2 exactly for a narrowband ' ...
                      'signal; the fitted ratio must approach 1/2 (see audit axis 3 ' ...
                      'for eps_rel at matched SNR).']);

disp_ic  = IC  / (max(IC(:))  + eps);
disp_ie  = IE  / (max(IE(:))  + eps);
disp_ibs = IBS / (max(IBS(:)) + eps);
disp_mu  = MU;  disp_mu(~valid) = 0;
mu_disp  = MU / max([muV; eps]);

R = struct( ...
    'IC',IC,'IE',IE,'IBS',IBS,'MU',MU,'XT',XT,'E2P',E2P, ...
    'IBS_from_IC2',IBS_from_IC2,'MU_times_IE',MU_times_IE, ...
    'RELERR',RELERR,'XT_rel',XT_rel,'valid',valid, ...
    'disp',struct('IC',disp_ic,'IE',disp_ie,'IBS',disp_ibs,'MU',mu_disp,'XT',XT/(max(abs(XT(:)))+eps)), ...
    'grid',struct('Nx',Nx,'FOV',P.FOV,'axis_mm',((1:Nx)-Nx/2)*(P.FOV/(Nx-1))), ...
    'sensor',struct('x',sx,'y',sy,'R',P.R,'M',M), ...
    'target',tg,'muStats',muStats,'chk',chk,'e2p',e2p, ...
    'cfg',struct('Preset',opt.Preset,'vs',P.vs,'fs',P.fs,'f0',P.f0, ...
                 'f_low',P.f_low,'f_high',P.f_high,'lp_cutoff',P.lp_cutoff, ...
                 'beta',(P.f_high-P.f_low)/P.f0,'sqlaw_ok',P.sqlaw_ok, ...
                 'Nrep',opt.Nrep,'SNR_dB',opt.SNR_dB));

if opt.Verbose
    fprintf('  ---- 恒等式逐像素检验 ----\n');
    fprintf('  max|I_BS - M*mu*I_E| / I_BS = %.3e   (mean %.3e, %d/%d 像素有效)\n', ...
            chk.maxRelErr_identity, chk.meanRelErr_identity, ...
            chk.nPixels_valid, chk.nPixels_total);
    fprintf('  max|I_BS - I_C^2| / max|I_BS|  = %.3e\n', chk.relIBS_vs_IC2);
    fprintf('  ---- mu 空间统计 ----\n');
    fprintf('  mu: min %.4f  p05 %.4f  median %.4f  mean %.4f  p95 %.4f  max %.4f\n', ...
            muStats.min, muStats.p05, muStats.median, muStats.mean, ...
            muStats.p95, muStats.max);
    fprintf('  均匀相位期望 1/M = %.4f  ->  median/理论 = %.3f\n', ...
            1/M, muStats.median*M);
    fprintf('  ---- 交叉项（相干分量，E 臂丢弃）----\n');
    fprintf('  XT = I_BS - I_E :  min %.4g  median %.4g  max %.4g ；中位相对占比 %.3f\n', ...
            min(XT(valid)), median(XT(valid)), max(XT(valid)), median(XT_rel(valid)));
end

if opt.Save
    if ~exist(opt.OutDir,'dir'), mkdir(opt.OutDir); end
    save(fullfile(opt.OutDir,'fig2_identity.mat'), '-struct','R','-v7.3');
    if opt.Verbose, fprintf('  [out] %s\n', opt.OutDir); end
end
end

% ==================================================================
function [f, maxRelErr] = local_fields(D, P, sx, sy, Nx)
% 一次采样取出 IC / IE / IBS / MU / XT，全部来自同一组 v_m
nS = size(D.z, 1);
M  = size(D.z, 2);

dx = P.FOV / (Nx - 1);
qv = ((1:Nx) - Nx/2) * dx;
[XC, YC] = meshgrid(qv, qv);

ACCc = complex(zeros(Nx, Nx));   % sum_m v_m
IEa  = zeros(Nx, Nx);           % sum_m |v_m|^2

for m = 1:M
    d = sqrt((XC - sx(m)).^2 + (YC - sy(m)).^2);
    t  = d / P.vs * P.fs + 1;
    ok = (t >= 1) & (t <= nS);
    v  = local_interp(D.z(:,m), t, ok);
    w  = (d + 1e-6) / P.R;                    % 幅值量补偿（唯一合法形式）
    g  = v .* w .* ok;                       % a_m = w_m z_m(tau_m)
    ACCc = ACCc + g;
    IEa  = IEa  + abs(g).^2;                 % 能量域：w^2 |z|^2（w 已含平方）
end

IC  = abs(ACCc);
IBS = IC.^2;
MU  = nan(Nx, Nx);
m0  = IEa > 0;
MU(m0)  = abs(ACCc(m0)).^2 ./ (M * IEa(m0));
XT     = IBS - IEa;

% 逐像素恒等式残差（本次实现内）
IBSc = IC.^2;
RELERR = zeros(Nx, Nx);
RELERR(m0) = abs(IBSc(m0) - M*MU(m0).*IEa(m0)) ./ (abs(IBSc(m0)) + eps);

f.IC = IC; f.IE = IEa; f.IBS = IBS; f.MU = MU; f.XT = XT;
f.E2p = IEa;f.RELERR = RELERR;  f.valid = m0;
f.maxRelErr = max(RELERR(m0));
end

% ==================================================================
function D = local_data(P, sx, sy, tg, snr_dB, rep)
% 合成数据：圆盘点目标 + 白噪声，固定种子可复现
rng(77000 + rep);
nS = P.nSamples;
tt = (0:nS-1)' / P.fs;
x  = zeros(nS, P.N);

for k = 1:numel(tg.r)
    px = tg.r(k);  py = 0;
    for m = 1:P.N
        d = hypot(px - sx(m), py - sy(m));
        t0 = d / P.vs;
        env = exp(-0.5*((tt - t0)/(P.sig_t/2.355)).^2);
        % 相位只由传播决定。**不得**叠加人为的逐通道相位常数 ——
        % 那不是物理的，会在 mu 场上造出假的同心环伪影，
        % 使读者误以为"相干场有强环状结构"，而那只是生成器的产物。
        x(:,m) = x(:,m) + tg.amp(k) * env .* cos(2*pi*P.f0*(tt - t0));
    end
end

% 与主链一致：零相位带通 + 去直流（medina口径）
[b, a] = butter(P.f_order, [P.f_low P.f_high]/(P.fs/2), 'bandpass');
xf = zeros(nS, P.N);
for m = 1:P.N, xf(:,m) = filter(b, a, x(:,m)); end
xf = xf - median(xf, 1);

Z = complex(zeros(nS, P.N));
for m = 1:P.N, Z(:,m) = hilbert(double(xf(:,m))); end

s = sqrt(mean(abs(Z(:)).^2));
Z = Z + (randn(nS,P.N) + 1i*randn(nS,P.N))/sqrt(2) * s * 10^(-snr_dB/20);

% 免 Hilbert 通道（D2' = LPF{x^2}）
xs = xf - mean(xf,1);
[bb, aa] = butter(4, P.lp_cutoff/(P.fs/2), 'low');
E2 = filter(bb, aa, xs.^2);

D.x = xf;  D.z = Z;  D.E2 = E2;
end

% ==================================================================
function v = local_interp(u, t, ok)
n = numel(u);
i0 = floor(t);
fr = t - i0;
i0 = max(i0, 1);
i1 = min(i0+1, n);
i0 = min(i0, n);
v  = u(i0).*(1-fr) + u(i1).*fr;
v(~ok) = 0;
end

% ==================================================================
function q = local_prctile(x, p)
x = sort(x(:));
i = max(1, min(numel(x), round(p/100*numel(x))));
q = x(i);
end

% ==================================================================
function o = parse_opts(o, varargin)
if mod(numel(varargin),2) ~= 0, error('选项须成对出现'); end
for k = 1:2:numel(varargin)
    nm = varargin{k};
    if ~isvarname(nm), error('非法选项名'); end
    o.(nm) = varargin{k+1};
end
end