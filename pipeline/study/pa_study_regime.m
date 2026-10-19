function R = pa_study_regime(varargin)
%PA_STUDY_REGIME  优势相图：三臂（C/M/E）在（相位像差 x 杂波强度）平面上的表现
%
%   问题（取代"能量成像靠杂波抑制取胜"这一未经验证的断言）
%     在什么体制下，"不用 Hilbert 的相位盲重建"（Arm M 包络叠加 / Arm E 能量）
%     才可能胜过"经典相干反投影"（Arm C，Hilbert + DAS/FBP）？
%
%   两个扫描轴
%     A. 相位像差 sigma_phi [rad]：相位屏模型。给每个通道的解析信号乘 e^{i phi_m}，
%        phi_m ~ N(0, sigma_phi^2)。物理对应"波前畸变"（声速不均、耦合层不均、
%        浅表组织异质）。相干求和依赖载波相位 -> C 应随 sigma_phi 崩溃；
%        相位盲（M/E）应不受影响。sigma_phi = 2*pi*f0*dtau，sigma_phi=1 rad
%        相当于 0.032 us 的时延抖动（约 lambda/6）。
%     B. 杂波强度 cratio：视场外强吸收体（同 radiual 24~34 mm，N=14）的幅值
%        相对目标的倍数。cratio=0 即"纯白噪声体制"。检验"强相干杂波"下三臂排序。
%
%   三个臂（同前处理、同反投影核、几何补偿各自匹配）
%     Arm C：hilbert -> 复数求和取模，comp = r      （经典 FBP 口径）
%     Arm M：hilbert -> |z| 叠加，   comp = r      （包络叠加，本项目历来基线）
%     Arm E：x^2 -> 低通 -> 1/2|z|^2，comp = r^2    （本文，内积平方）
%
%   指标（固定"病灶 ROI"口径，与真实数据实验一致）
%     2D 图：inROI = 半径 0.5 mm 圆盘；outROI = 3~6 mm 圆环
%       gCNR（单调映射不变 -> 唯一合法的跨域指标，主指标）
%       CNR = (mean_in - mean_out)/std_out（同域内可比；跨域不可比，仅辅报）
%       PSR = 峰值/背景最大值（各自原生域）
%     中心行剖面：幅度域 -6dB 半高宽
%       wC = W(I_C), wM = W(I_M), wE = W(sqrt(I_E))   （统一电平，公平口径）
%
%   可选参数
%     'Array'      'semicircle128'（默认）| 'ring256'
%     'Nx'         网格（默认 601）
%     'sigList'    相位像差扫描点（默认 [0 0.5 1 2 4] rad）
%     'crList'     杂波强度扫描点（默认 [0 0.5 1 2 5]）
%     'Save'       （默认 true）
%
%   版本：v1  2026-10-14

opt.Array  = 'semicircle128';
opt.SNR    = 40;
opt.Nx     = 601;
opt.FOV    = 40e-3;
opt.sigList = [0 0.5 1 2 4];
opt.crList  = [0 0.5 1 2 5];
opt.Ncl     = 14;
opt.Save   = true;
opt.OutDir = '';
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot   = fileparts(fileparts(mfilename('fullpath')));
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', sprintf('study_regime_%s', opt.Array));
end

P = struct();
P.fs = 40e6; P.nSamples = 4096; P.vs = 1478; P.f0 = 5e6;
P.beta_sig = 0.60; P.bw_law = 0.80; P.R = 55e-3; P.FOV = opt.FOV; P.Nx = opt.Nx;
P.SNR = opt.SNR; P.Ncl = opt.Ncl;
switch lower(opt.Array)
    case 'semicircle128', P.arrayType = 'semicircle128'; P.N = 128;
    case 'ring256',       P.arrayType = 'ring1024';      P.N = 256;
    otherwise, error('pa_study_regime:array', '未知阵列：%s', opt.Array);
end
P.f_low = P.f0*(1-P.bw_law/2); P.f_high = P.f0*(1+P.bw_law/2);
cfg = build_cfg(P);
[sx, sy] = sensor_positions(P);

% 杂波几何固定（同一次随机抽样），以便跨 (sigma_phi, cratio) 可控比较
rng(11);
rad = 24e-3 + 10e-3*rand(P.Ncl,1);
ang = 2*pi*rand(P.Ncl,1);
P.cpts = [rad.*cos(ang), rad.*sin(ang)];

fprintf('\n==== pa_study_regime : %s ====\n', opt.Array);
fprintf('  N=%d, R=%.0f mm, Nx=%d, SNR=%.0f dB, Ncl=%d\n', P.N, P.R*1e3, P.Nx, opt.SNR, P.Ncl);
fprintf('  sigma_phi = [%s] rad ; cratio = [%s]\n', num2str(opt.sigList), num2str(opt.crList));

ns = numel(opt.sigList);  nc = numel(opt.crList);
T = struct();
T.gCNR = nan(ns, nc, 3);   % 3 = C,M,E
T.CNR  = nan(ns, nc, 3);
T.PSR  = nan(ns, nc, 3);
T.wC = nan(ns,nc); T.wM = nan(ns,nc); T.wE = nan(ns,nc);
T.pkN = nan(ns,nc,2);      % 归一化峰值（C / M 相对 E）

R1 = local_roi_masks(P);

for i = 1:ns
    for j = 1:nc
        sp = opt.sigList(i);  cr = opt.crList(j);
        sig = local_synth(P, [0 0], 1, sx, sy, sp, cr);
        [prof, img, ~] = local_dual_arm(sig, cfg, P);

        % ---- 中心行剖面：幅度域 -6dB 宽度（统一电平，公平口径）----
        wC = local_width(prof.ax, prof.C, 0.5);
        wM = local_width(prof.ax, prof.M, 0.5);
        wE = local_width(prof.ax, prof.Ea, 0.5);
        T.wC(i,j) = wC; T.wM(i,j) = wM; T.wE(i,j) = wE;

        % ---- 2D 指标：病灶 ROI（0.5 mm 圆盘）vs 背景环（3~6 mm）----
        mC = local_img_metrics(img.C,  R1);
        mM = local_img_metrics(img.M,  R1);
        mE = local_img_metrics(img.E,  R1);
        T.gCNR(i,j,:) = [mC.gCNR, mM.gCNR, mE.gCNR];
        T.CNR (i,j,:) = [mC.CNR,  mM.CNR,  mE.CNR];
        T.PSR (i,j,:) = [mC.PSR,  mM.PSR,  mE.PSR];
        T.pkN(i,j,:)  = [ prof.Cmax/prof.Emax, prof.Mmax/prof.Emax ];

        fprintf(['  sp=%4.2f cr=%4.1f | wC=%.4f wM=%.4f wE=%.4f | ' ...
                 'gCNR C=%.4f M=%.4f E=%.4f | PSR C=%8.2f M=%7.2f E=%7.2f\n'], ...
            sp, cr, wC, wM, wE, mC.gCNR, mM.gCNR, mE.gCNR, mC.PSR, mM.PSR, mE.PSR);
    end
end

R = struct('P', P, 'cfg', cfg, 'sigList', opt.sigList, 'crList', opt.crList, 'T', T);

fprintf('\n---- 判读 ----\n');
fprintf('  相位像差轴 cratio=0（纯白噪声，只留相位屏）:\n');
for i = 1:ns
    fprintf('    sp=%4.2f rad | wM=%.3f wE=%.3f | PSR C=%7.2f M=%6.2f E=%6.2f | gCNR C=%.3f M=%.3f E=%.3f\n', ...
        T.wC(i,1)*0 + opt.sigList(i), T.wM(i,1), T.wE(i,1), ...
        T.PSR(i,1,1), T.PSR(i,1,2), T.PSR(i,1,3), ...
        T.gCNR(i,1,1), T.gCNR(i,1,2), T.gCNR(i,1,3));
end
fprintf('  杂波轴 sigma_phi=0（无相位误差，只留杂波）:\n');
for j = 1:nc
    fprintf('    cratio=%4.1f | wM=%.3f wE=%.3f | PSR C=%7.2f M=%6.2f E=%6.2f | gCNR C=%.3f M=%.3f E=%.3f\n', ...
        opt.crList(j), T.wM(1,j), T.wE(1,j), ...
        T.PSR(1,j,1), T.PSR(1,j,2), T.PSR(1,j,3), ...
        T.gCNR(1,j,1), T.gCNR(1,j,2), T.gCNR(1,j,3));
end

if opt.Save
    if ~exist(opt.OutDir,'dir'), mkdir(opt.OutDir); end
    local_plot(R, opt.OutDir);
    save(fullfile(opt.OutDir,'study_regime.mat'), '-struct','R','-v7.3');
    fprintf('\n  [out] %s\n', opt.OutDir);
end
end

% ==================================================================
function [prof, img, IC] = local_dual_arm(sig, cfg, P)
D = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','sq','filtered'});

Z = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
IC = backproject_complex(Z, cfg, P, 'r', 1);

IM = pa_backproject(D.env,   cfg,'Comp','r',  'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IE = pa_backproject(D.sqlaw, cfg,'Comp','r2', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');

ax = ((1:P.Nx) - P.Nx/2) * (P.FOV/(P.Nx-1)) * 1e3;
[~, i0] = min(abs(ax));
img.C = IC; img.M = IM; img.E = IE;
prof.ax = ax;
prof.C  = IC(i0,:).';  prof.Cmax = max(prof.C);
prof.M  = IM(i0,:).';  prof.Mmax = max(prof.M);
prof.E  = IE(i0,:).';  prof.Emax = max(prof.E);
prof.Ea = sqrt(max(prof.E,0));
end

function IC = backproject_complex(Z, cfg, P, comp, keepSign)
Nx = P.Nx; FOV = P.FOV; dx = FOV/(Nx-1);
qv = ((1:Nx)-Nx/2)*dx; [XC,YC] = meshgrid(qv,qv);
[SX,SY] = sensor_positions(P);
nS = size(Z,1); nCh = size(Z,2);
ACC = zeros(Nx,Nx);
for ch = 1:nCh
    d = hypot(XC-SX(ch), YC-SY(ch));
    tidx = d/cfg.vs*cfg.fs + 1;
    valid = (tidx>=1) & (tidx<=nS);
    vr = interp1(1:nS, real(Z(:,ch)), tidx(:), 'linear', 0);
    vi = interp1(1:nS, imag(Z(:,ch)), tidx(:), 'linear', 0);
    v  = reshape(vr + 1i*vi, Nx, Nx);
    switch lower(comp)
        case 'r',  wgt = (d+1e-6)/cfg.R;
        case 'r2', wgt = ((d+1e-6)/cfg.R).^2;
        otherwise, wgt = ones(size(d));
    end
    ACC = ACC + v.*wgt.*valid;
end
if keepSign, IC = abs(ACC); else, IC = ACC; end
end

% ==================================================================
function sig = local_synth(P, pts, amps, sx, sy, sigma_phi, cratio)
nCh = numel(sx);
t = (0:P.nSamples-1).'/P.fs;
sigF = P.beta_sig*P.f0/2.355;  sigT = 1/(2*pi*sigF);
sig = zeros(P.nSamples, nCh);
sig = add_points(sig, P, t, pts, amps, sx, sy);
if cratio > 0
    sig = add_points(sig, P, t, P.cpts, cratio*ones(P.Ncl,1), sx, sy);
end

% ---- 相位屏（波前畸变）：给每个通道的解析信号乘 e^{i phi_m} ----
if sigma_phi > 0
    phi = sigma_phi * randn(nCh,1);
    for m = 1:nCh
        z = hilbert(sig(:,m)) .* exp(1i*phi(m));
        sig(:,m) = real(z);
    end
end

refAmp = max(vecnorm(sig, inf, 1));
sig = sig + refAmp * 10^(-P.SNR/20) * randn(size(sig));
end

function sig = add_points(sig, P, t, pts, amps, sx, sy)
nCh = numel(sx);
sigF = P.beta_sig*P.f0/2.355;  sigT = 1/(2*pi*sigF);
for k = 1:size(pts,1)
    for m = 1:nCh
        rr  = hypot(pts(k,1)-sx(m), pts(k,2)-sy(m));
        tau = rr/P.vs;  a = amps(k)/rr;
        g = exp(-((t-tau)/sigT).^2) .* cos(2*pi*P.f0*(t-tau));
        sig(:,m) = sig(:,m) + a*g;
    end
end
end

function [sx, sy] = sensor_positions(P)
switch lower(P.arrayType)
    case 'semicircle128'
        ang = (0:P.N-1)*(pi/(P.N-1)) - pi;
    otherwise
        ang = (0:P.N-1)*(2*pi/P.N);
end
sx = P.R*cos(ang); sy = P.R*sin(ang);
end

function cfg = build_cfg(P)
cfg = struct();
cfg.name='study'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
cfg.vs=P.vs; cfg.fs=P.fs; cfg.nSamples=P.nSamples; cfg.FOV=P.FOV; cfg.Nx=P.Nx;
cfg.f0=P.f0; cfg.f_low=P.f_low; cfg.f_high=P.f_high; cfg.f_order=3;
cfg.smooth=1; cfg.dcMethod='median'; cfg.dcFirstN=100; cfg.padLen=[];
cfg.filt='none'; cfg.takeAbs=false; cfg.comp='r'; cfg.bw_law=P.bw_law;
cfg.WL=0.15; cfg.WW=0.70; cfg.nyquist=cfg.fs/2;
B_rf = cfg.f_high-cfg.f_low; cfg.beta_rf = B_rf/cfg.f0;
cfg.sqlaw_lo_cut=B_rf; cfg.sqlaw_hi_cut=2*cfg.f_low;
cfg.sqlaw_ok = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;
if cfg.sqlaw_ok, cfg.lp_cutoff=0.5*(cfg.sqlaw_lo_cut+cfg.sqlaw_hi_cut);
else, cfg.lp_cutoff=cfg.f0; end
cfg.sqlaw_narrowband=[cfg.f_low,cfg.f_high];
end

% ==================================================================
function R1 = local_roi_masks(P)
dx = P.FOV/(P.Nx-1); qv = ((1:P.Nx)-P.Nx/2)*dx;
[X,Y] = meshgrid(qv,qv); r2 = X.^2+Y.^2;
R1.in  = r2 <= (0.5e-3)^2;
R1.out = (r2 >= (3e-3)^2) & (r2 <= (6e-3)^2);
end

function m = local_img_metrics(img, R1)
a = img(R1.in); b = img(R1.out);
m.CNR  = (mean(a)-mean(b))/(std(b)+eps);
m.PSR  = max(img(:))/(max(b)+eps);
m.gCNR = gcnr(a,b);
m.peak = max(img(:));
end

function g = gcnr(a,b)
if isempty(a) || isempty(b), g = NaN; return; end
lo = min([a(:);b(:)]); hi = max([a(:);b(:)]);
if hi <= lo, g = 1; return; end
e = linspace(lo,hi,65);
pa = histcounts(a,e); pa = pa/sum(pa);
pb = histcounts(b,e); pb = pb/sum(pb);
g = 1 - sum(min(pa,pb));
end

function w = local_width(ax, y, lvl)
% 半高全宽（线性插值）：用"跨越阈值的相邻两点"插值。
% 不要用"两侧都不跨阈就回退到 i-1..i+1"的写法：那会跳过下降沿改取旁瓣上升沿，
% 对强旁瓣剖面（相干 PSF）给出错误宽度。
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

function local_plot(R, outDir)
T = R.T; sp = R.sigList; cr = R.crList;
f = figure('Position',[60 60 1240 760],'Color','w');
lbl = {'C: coherent FBP','M: envelope sum','E: energy (this work)'};
subplot(2,3,1);
plot(sp, squeeze(T.gCNR(:,1,1)),'k-o','LineWidth',1.4); hold on;
plot(sp, squeeze(T.gCNR(:,1,2)),'b-s','LineWidth',1.4);
plot(sp, squeeze(T.gCNR(:,1,3)),'r-^','LineWidth',1.4);
grid on; xlabel('\sigma_\phi (rad)'); ylabel('gCNR');
title('Aberration axis (cratio=0)'); legend(lbl,'Location','southwest');
subplot(2,3,2);
semilogy(sp, squeeze(T.PSR(:,1,1)),'k-o','LineWidth',1.4); hold on;
semilogy(sp, squeeze(T.PSR(:,1,2)),'b-s','LineWidth',1.4);
semilogy(sp, squeeze(T.PSR(:,1,3)),'r-^','LineWidth',1.4);
grid on; xlabel('\sigma_\phi (rad)'); ylabel('PSR'); title('Sidelobe purity vs aberration');
subplot(2,3,3);
plot(cr, squeeze(T.gCNR(1,:,1)),'k-o','LineWidth',1.4); hold on;
plot(cr, squeeze(T.gCNR(1,:,2)),'b-s','LineWidth',1.4);
plot(cr, squeeze(T.gCNR(1,:,3)),'r-^','LineWidth',1.4);
grid on; xlabel('clutter/target amplitude'); ylabel('gCNR'); title('Clutter axis (\sigma_\phi=0)');
subplot(2,3,4);
plot(cr, T.wM(1,:),'b-s','LineWidth',1.4); hold on;
plot(cr, T.wE(1,:),'r-^','LineWidth',1.4);
grid on; xlabel('clutter/target amplitude'); ylabel('fair width (mm)'); title('Width vs clutter');
subplot(2,3,5); axis off;
txt = {'PSR (native domain)'; '  sigma_phi  C        M        E'};
for i = 1:numel(sp)
    txt{end+1} = sprintf('  %5.2f   %8.2f %8.2f %8.2f', sp(i), T.PSR(i,1,1), T.PSR(i,1,2), T.PSR(i,1,3));
end
txt{end+1} = ''; txt{end+1} = 'gCNR'; txt{end+1} = '  sigma_phi  C        M        E';
for i = 1:numel(sp)
    txt{end+1} = sprintf('  %5.2f   %8.4f %8.4f %8.4f', sp(i), T.gCNR(i,1,1), T.gCNR(i,1,2), T.gCNR(i,1,3));
end
text(0.02,0.98,txt,'VerticalAlignment','top','FontSize',9,'FontName','FixedWidth');
print(f, fullfile(outDir,'study_regime.png'),'-dpng','-r140'); close(f);
end

function o = parse_opts(o, varargin)
if mod(numel(varargin),2) ~= 0, error('parse_opts:pair','参数必须成对。'); end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o,k), error('parse_opts:unknown','未知参数：%s',k); end
    o.(k) = varargin{i+1};
end
end
