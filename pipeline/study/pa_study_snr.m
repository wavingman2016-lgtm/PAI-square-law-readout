function R = pa_study_snr(varargin)
%PA_STUDY_SNR  SNR 轴：平方律（能量）在低信噪比下是否优于线性包络求和？
%
%   动机
%     §3.7 相图已确认：相位像差下"相位盲"两臂（M、E）完胜相干臂 C，
%     但该优势归属"非相干求和"这一族，而非"平方"这一算子。
%     平方能否单独立功，只剩最后一个有理论根据的地方：
%       —— 低 SNR 区。窄带信号、未知相位、高斯噪声下，
%          最优非相干检波器是"平方律"（|z|^2 累加 = Arm E），
%          而"线性包络累加"（Arm M）是次优但更稳健的替代。
%     故本脚本扫描 SNR，检验 gCNR / CNR / PSR 上 E 是否反超 M。
%
%   臂：C（相干 FBP）/ M（包络叠加）/ E（能量，本文）
%   指标：gCNR（0.5 mm 圆盘 vs 3~6 mm 环，跨域唯一合法指标）、
%         CNR 与 PSR（各自原生域，同域趋势）、幅度域 -6dB 公平宽度
%
%   版本：v1  2026-10-14

opt.Array  = 'semicircle128';
opt.Nx     = 601;
opt.snrList = [0 5 10 15 20 25 30 40];
opt.Nrep    = 5;              % 每个 SNR 重复次数（噪声随机），报告均值
opt.Save   = true;
opt.OutDir = '';
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot = fileparts(fileparts(mfilename('fullpath')));
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', sprintf('study_snr_%s', opt.Array));
end

P = struct();
P.fs=40e6; P.nSamples=4096; P.vs=1478; P.f0=5e6;
P.beta_sig=0.60; P.bw_law=0.80; P.R=55e-3; P.FOV=40e-3; P.Nx=opt.Nx;
switch lower(opt.Array)
    case 'semicircle128', P.arrayType='semicircle128'; P.N=128;
    case 'ring256',       P.arrayType='ring1024';      P.N=256;
    otherwise, error('pa_study_snr:array','未知阵列：%s', opt.Array);
end
P.f_low=P.f0*(1-P.bw_law/2); P.f_high=P.f0*(1+P.bw_law/2);
cfg = build_cfg(P);
[sx,sy] = sensor_positions(P);
R1 = roi_masks(P);

n  = numel(opt.snrList);
T.snr = opt.snrList(:);
T.gCNR = nan(n,3); T.CNR = nan(n,3); T.PSR = nan(n,3);
T.wC = nan(n,1); T.wM = nan(n,1); T.wE = nan(n,1);

fprintf('\n==== pa_study_snr : %s (Nrep=%d) ====\n', opt.Array, opt.Nrep);
fprintf('  %6s | %19s | %19s | %19s\n','SNR(dB)','gCNR C / M / E','CNR C / M / E','PSR C / M / E');

for i = 1:n
    snr = opt.snrList(i);
    acc.g = zeros(opt.Nrep,3); acc.c = zeros(opt.Nrep,3); acc.p = zeros(opt.Nrep,3);
    acc.w = zeros(opt.Nrep,3);
    for k = 1:opt.Nrep
        rng(1000 + 17*k + i);
        sig = local_synth(P, [0 0], 1, sx, sy, snr);
        r = local_arm(sig, cfg, P, R1);
        acc.g(k,:) = r.g; acc.c(k,:) = r.c; acc.p(k,:) = r.p; acc.w(k,:) = r.w;
    end
    T.gCNR(i,:) = mean(acc.g,1); T.CNR(i,:) = mean(acc.c,1);
    T.PSR(i,:)  = mean(acc.p,1); T.wC(i)=mean(acc.w(:,1)); T.wM(i)=mean(acc.w(:,2)); T.wE(i)=mean(acc.w(:,3));
    fprintf('  %6.0f | %6.3f %6.3f %6.3f | %7.2f %7.2f %7.2f | %7.2f %6.2f %6.2f\n', ...
        snr, T.gCNR(i,1),T.gCNR(i,2),T.gCNR(i,3), ...
             T.CNR(i,1), T.CNR(i,2), T.CNR(i,3), ...
             T.PSR(i,1), T.PSR(i,2), T.PSR(i,3));
end

fprintf('\n---- 判读 ----\n');
d = T.gCNR(:,3) - T.gCNR(:,2);
[dm, im] = max(d);
fprintf('  gCNR(E-M) 最大 = %+.4f @ SNR=%g dB ; 全程范围 [%+.4f, %+.4f]\n', ...
        dm, T.snr(im), min(d), max(d));
if max(abs(d)) < 0.02
    fprintf('  => 结论：低 SNR 下平方律**未**显著优于线性包络求和（gCNR 差 < 0.02）。\n');
    fprintf('     即"平方"这一算子本身不带来独立的对比度/信息增益；收益归属"非相干求和"族。\n');
else
    fprintf('  => 结论：低 SNR 下平方律对线性包络求和存在可测优势（详见上表）。\n');
end
fprintf('  公平宽度比 E/M：SNR=%g dB -> %.3f ; SNR=%g dB -> %.3f（应与 SNR 无关）\n', ...
        T.snr(1), T.wE(1)/T.wM(1), T.snr(end), T.wE(end)/T.wM(end));

R = struct('P',P,'cfg',cfg,'T',T,'snrList',opt.snrList);
if opt.Save
    if ~exist(opt.OutDir,'dir'), mkdir(opt.OutDir); end
    local_plot(R, opt.OutDir);
    save(fullfile(opt.OutDir,'study_snr.mat'),'-struct','R','-v7.3');
    fprintf('\n  [out] %s\n', opt.OutDir);
end
end

% ==================================================================
function r = local_arm(sig, cfg, P, R1)
D = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw'});
Z = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
IC = backproject_complex(Z, cfg, P, 'r');
IM = pa_backproject(D.env,   cfg,'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IE = pa_backproject(D.sqlaw, cfg,'Comp','r2','Nx',P.Nx,'FOV',P.FOV,'Normalize','none');

ax = ((1:P.Nx)-P.Nx/2)*(P.FOV/(P.Nx-1))*1e3;
[~,i0] = min(abs(ax));
pC = IC(i0,:).'; pM = IM(i0,:).'; pE = IE(i0,:).'; pEa = sqrt(max(pE,0));

r.g = [img_gcnr(IC,R1), img_gcnr(IM,R1), img_gcnr(IE,R1)];
r.c = [img_cnr(IC,R1),  img_cnr(IM,R1),  img_cnr(IE,R1)];
r.p = [img_psr(IC,R1),  img_psr(IM,R1),  img_psr(IE,R1)];
r.w = [local_width(ax,pC,0.5), local_width(ax,pM,0.5), local_width(ax,pEa,0.5)];
end

function v = img_cnr(M,R1)
a = M(R1.in); b = M(R1.out);
v = (mean(a)-mean(b))/(std(b)+eps);
end
function v = img_psr(M,R1)
v = max(M(:))/(max(M(R1.out))+eps);
end
function v = img_gcnr(M,R1)
a = M(R1.in); b = M(R1.out);
lo = min([a(:);b(:)]); hi = max([a(:);b(:)]);
if hi <= lo, v = 1; return; end
e = linspace(lo,hi,65);
pa = histcounts(a,e); pa = pa/sum(pa);
pb = histcounts(b,e); pb = pb/sum(pb);
v = 1 - sum(min(pa,pb));
end

function IC = backproject_complex(Z, cfg, P, comp)
Nx=P.Nx; dx=P.FOV/(Nx-1); qv=((1:Nx)-Nx/2)*dx; [XC,YC]=meshgrid(qv,qv);
[SX,SY]=sensor_positions(P); nS=size(Z,1); nCh=size(Z,2); ACC=zeros(Nx,Nx);
for ch=1:nCh
    d = hypot(XC-SX(ch), YC-SY(ch)); tidx = d/cfg.vs*cfg.fs+1;
    valid = (tidx>=1)&(tidx<=nS);
    vr = interp1(1:nS,real(Z(:,ch)),tidx(:),'linear',0);
    vi = interp1(1:nS,imag(Z(:,ch)),tidx(:),'linear',0);
    v  = reshape(vr+1i*vi, Nx, Nx);
    switch lower(comp)
        case 'r',  wgt=(d+1e-6)/cfg.R;
        case 'r2', wgt=((d+1e-6)/cfg.R).^2;
        otherwise, wgt=ones(size(d));
    end
    ACC = ACC + v.*wgt.*valid;
end
IC = abs(ACC);
end

function sig = local_synth(P, pts, amps, sx, sy, snr_dB)
nCh=numel(sx); t=(0:P.nSamples-1).'/P.fs;
sigT = 1/(2*pi*(P.beta_sig*P.f0/2.355));
sig = zeros(P.nSamples,nCh);
for k=1:size(pts,1)
    for m=1:nCh
        rr = hypot(pts(k,1)-sx(m), pts(k,2)-sy(m));
        tau = rr/P.vs; a = amps(k)/rr;
        sig(:,m) = sig(:,m) + a*exp(-((t-tau)/sigT).^2).*cos(2*pi*P.f0*(t-tau));
    end
end
refAmp = max(vecnorm(sig,inf,1));
sig = sig + refAmp*10^(-snr_dB/20)*randn(size(sig));
end

function [sx,sy] = sensor_positions(P)
switch lower(P.arrayType)
    case 'semicircle128', ang=(0:P.N-1)*(pi/(P.N-1))-pi;
    otherwise,            ang=(0:P.N-1)*(2*pi/P.N);
end
sx = P.R*cos(ang); sy = P.R*sin(ang);
end

function cfg = build_cfg(P)
cfg=struct(); cfg.name='snr'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
cfg.vs=P.vs; cfg.fs=P.fs; cfg.nSamples=P.nSamples; cfg.FOV=P.FOV; cfg.Nx=P.Nx;
cfg.f0=P.f0; cfg.f_low=P.f_low; cfg.f_high=P.f_high; cfg.f_order=3;
cfg.smooth=1; cfg.dcMethod='median'; cfg.dcFirstN=100; cfg.padLen=[];
cfg.filt='none'; cfg.takeAbs=false; cfg.comp='r'; cfg.bw_law=P.bw_law;
cfg.WL=0.15; cfg.WW=0.70; cfg.nyquist=cfg.fs/2;
B_rf=cfg.f_high-cfg.f_low; cfg.beta_rf=B_rf/cfg.f0;
cfg.sqlaw_lo_cut=B_rf; cfg.sqlaw_hi_cut=2*cfg.f_low;
cfg.sqlaw_ok = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;
if cfg.sqlaw_ok, cfg.lp_cutoff=0.5*(cfg.sqlaw_lo_cut+cfg.sqlaw_hi_cut);
else, cfg.lp_cutoff=cfg.f0; end
cfg.sqlaw_narrowband=[cfg.f_low,cfg.f_high];
end

function R1 = roi_masks(P)
dx=P.FOV/(P.Nx-1); qv=((1:P.Nx)-P.Nx/2)*dx; [X,Y]=meshgrid(qv,qv); r2=X.^2+Y.^2;
R1.in = r2 <= (0.5e-3)^2;
R1.out = (r2 >= (3e-3)^2) & (r2 <= (6e-3)^2);
end

function w = local_width(ax, y, lvl)
% 半高全宽（线性插值）：用"跨越阈值的相邻两点"插值。
ax=ax(:).'; y=y(:).'; pk=max(y);
if pk<=0, w=NaN; return; end
thr=lvl*pk; n=numel(y); [~,i0]=max(y);
L=i0;  while L>1 && y(L)>thr,  L=L-1;  end
Rr=i0; while Rr<n && y(Rr)>thr, Rr=Rr+1; end
if y(L)>thr,  xl=ax(1);
else, xl=ax(L)+(thr-y(L))*(ax(L+1)-ax(L))/(y(L+1)-y(L)); end
if y(Rr)>thr, xr=ax(n);
else, xr=ax(Rr-1)+(thr-y(Rr-1))*(ax(Rr)-ax(Rr-1))/(y(Rr)-y(Rr-1)); end
w = abs(xr-xl);
end

function local_plot(R, outDir)
T=R.T;
f=figure('Position',[60 60 1200 420],'Color','w');
subplot(1,3,1);
plot(T.snr,T.gCNR(:,1),'k-o','LineWidth',1.4); hold on;
plot(T.snr,T.gCNR(:,2),'b-s','LineWidth',1.4);
plot(T.snr,T.gCNR(:,3),'r-^','LineWidth',1.4);
grid on; xlabel('SNR (dB)'); ylabel('gCNR'); ylim([0 1.05]);
title('gCNR vs SNR'); legend({'C','M','E'},'Location','southeast');
subplot(1,3,2);
semilogy(T.snr,T.PSR(:,1),'k-o','LineWidth',1.4); hold on;
semilogy(T.snr,T.PSR(:,2),'b-s','LineWidth',1.4);
semilogy(T.snr,T.PSR(:,3),'r-^','LineWidth',1.4);
grid on; xlabel('SNR (dB)'); ylabel('PSR (native domain)'); title('PSR vs SNR');
subplot(1,3,3);
plot(T.snr,T.wC,'k-o','LineWidth',1.4); hold on;
plot(T.snr,T.wM,'b-s','LineWidth',1.4);
plot(T.snr,T.wE,'r-^','LineWidth',1.4);
grid on; xlabel('SNR (dB)'); ylabel('fair width (mm)'); title('Width vs SNR');
print(f, fullfile(outDir,'study_snr.png'),'-dpng','-r140'); close(f);
end

function o = parse_opts(o, varargin)
if mod(numel(varargin),2)~=0, error('parse_opts:pair','参数必须成对。'); end
for i=1:2:numel(varargin)
    k=varargin{i};
    if ~isfield(o,k), error('parse_opts:unknown','未知参数：%s',k); end
    o.(k)=varargin{i+1};
end
end
