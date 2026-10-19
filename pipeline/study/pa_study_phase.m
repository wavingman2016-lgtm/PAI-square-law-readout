function R = pa_study_phase(varargin)
%PA_STUDY_PHASE  相位像差轴 + SNR 轴（三臂，Nrep 次平均）
%
%   为什么必须重做
%     pa_study_regime.m / pa_study_snr.m 的每个格点只做**一次**噪声/相位实现，
%     而相位像差轴的单次方差极大（同一 σ_φ=4 在两套脚本里给出 C 的 gCNR
%     0.215 与 0.767 —— 相差 0.55），单次结果不足以支撑任何结论。
%     本脚本用 Nrep 次独立实现，报 均值 ± 标准差。
%
%   两轴
%     相位像差 sigma_phi [rad]：每通道解析信号乘 e^{i phi_m}, phi_m ~ N(0,sigma^2)
%     SNR [dB]：白噪声相对目标回波
%
%   三臂（同前处理、同反投影核、几何补偿各自匹配）
%     C：Hilbert + 复数相干求和取模，comp = r      （传统 FBP）
%     M：Hilbert -> |z| 叠加，       comp = r      （包络基线）
%     E：x^2 -> 低通 -> 1/2|z|^2，   comp = r^2    （本文）
%
%   主口径：2D 病灶 ROI（0.5 mm 圆盘 vs 3~6 mm 环），主指标 gCNR
%
%   版本：v1  2026-10-14

opt.Nx      = 601;
opt.Nrep    = 6;
opt.sigList = [0 0.5 1 2 4];
opt.snrList = [0 5 10 15 20 25 30 40];
opt.OutDir  = '';
opt = pa_local_opts(opt, varargin{:});

P = struct();
P.fs=40e6; P.nSamples=4096; P.vs=1478; P.f0=5e6; P.beta_sig=0.60; P.bw_law=0.80;
P.R=55e-3; P.FOV=40e-3; P.Nx=opt.Nx; P.arrayType='semicircle128'; P.N=128;
P.f_low=P.f0*(1-P.bw_law/2); P.f_high=P.f0*(1+P.bw_law/2);
cfg = pa_build_cfg(P);
[sx,sy] = pa_sensor_positions(P);
R1 = pa_roi2d(P);

fprintf('\n==== pa_study_phase | Nx=%d Nrep=%d ====\n', opt.Nx, opt.Nrep);

% ---------------- 相位像差轴 ----------------
ns = numel(opt.sigList);
SA = struct('sig',opt.sigList, 'gC',nan(1,ns),'gM',nan(1,ns),'gE',nan(1,ns), ...
            'sC',nan(1,ns),'sM',nan(1,ns),'sE',nan(1,ns), ...
            'pC',nan(1,ns),'pM',nan(1,ns),'pE',nan(1,ns), ...
            'wC',nan(1,ns),'wM',nan(1,ns),'wE',nan(1,ns));
fprintf('\n---- 相位像差轴（cratio=0）----\n');
fprintf('  %6s | %-15s %-15s %-15s | d(E-C)  d(E-M)\n','sig','gCNR_C','gCNR_M','gCNR_E');
for i = 1:ns
    g = zeros(opt.Nrep,3); p = zeros(opt.Nrep,3); w = zeros(opt.Nrep,3);
    for r = 1:opt.Nrep
        rng(3000 + 17*r);          % 独立实现
        sig = pa_local_synth(P,sx,sy,opt.sigList(i),0,40);
        [gg,pp,ww] = pa_eval_arms(sig,cfg,P,R1);
        g(r,:)=gg; p(r,:)=pp; w(r,:)=ww;
    end
    SA.gC(i)=mean(g(:,1)); SA.gM(i)=mean(g(:,2)); SA.gE(i)=mean(g(:,3));
    SA.sC(i)=std(g(:,1));  SA.sM(i)=std(g(:,2));  SA.sE(i)=std(g(:,3));
    SA.pC(i)=mean(p(:,1)); SA.pM(i)=mean(p(:,2)); SA.pE(i)=mean(p(:,3));
    SA.wC(i)=mean(w(:,1)); SA.wM(i)=mean(w(:,2)); SA.wE(i)=mean(w(:,3));
    fprintf('  %6.2f | %6.4f±%.4f %6.4f±%.4f %6.4f±%.4f | %+7.4f %+7.4f\n', ...
        opt.sigList(i), SA.gC(i),SA.sC(i), SA.gM(i),SA.sM(i), SA.gE(i),SA.sE(i), ...
        SA.gE(i)-SA.gC(i), SA.gE(i)-SA.gM(i));
end

% ---------------- SNR 轴 ----------------
nn = numel(opt.snrList);
SB = struct('snr',opt.snrList, 'gC',nan(1,nn),'gM',nan(1,nn),'gE',nan(1,nn), ...
            'sC',nan(1,nn),'sM',nan(1,nn),'sE',nan(1,nn), ...
            'pC',nan(1,nn),'pM',nan(1,nn),'pE',nan(1,nn));
fprintf('\n---- SNR 轴（sigma_phi=0，无杂波）----\n');
fprintf('  %6s | %-15s %-15s %-15s | d(E-C)  d(E-M)\n','SNR','gCNR_C','gCNR_M','gCNR_E');
for i = 1:nn
    g = zeros(opt.Nrep,3); p = zeros(opt.Nrep,3);
    for r = 1:opt.Nrep
        rng(4000 + 19*r);
        sig = pa_local_synth(P,sx,sy,0,0,opt.snrList(i));
        [gg,pp,~] = pa_eval_arms(sig,cfg,P,R1);
        g(r,:)=gg; p(r,:)=pp;
    end
    SB.gC(i)=mean(g(:,1)); SB.gM(i)=mean(g(:,2)); SB.gE(i)=mean(g(:,3));
    SB.sC(i)=std(g(:,1));  SB.sM(i)=std(g(:,2));  SB.sE(i)=std(g(:,3));
    SB.pC(i)=mean(p(:,1)); SB.pM(i)=mean(p(:,2)); SB.pE(i)=mean(p(:,3));
    fprintf('  %6.1f | %6.4f±%.4f %6.4f±%.4f %6.4f±%.4f | %+7.4f %+7.4f\n', ...
        opt.snrList(i), SB.gC(i),SB.sC(i), SB.gM(i),SB.sM(i), SB.gE(i),SB.sE(i), ...
        SB.gE(i)-SB.gC(i), SB.gE(i)-SB.gM(i));
end

R = struct('SA',SA,'SB',SB,'P',P);
if ~isempty(opt.OutDir)
    if ~exist(opt.OutDir,'dir'), mkdir(opt.OutDir); end
    save(fullfile(opt.OutDir,'study_phase.mat'),'-struct','R','-v7.3');
    fprintf('\n  [out] %s\n', opt.OutDir);
end
end

% ==================================================================
function [gg,pp,ww] = pa_eval_arms(sig,cfg,P,R1)
D = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','filtered'});
Z = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
IC = pa_backproject_coherent(Z, cfg, 'Comp','r','Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IM = pa_backproject(D.env,   cfg,'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IE = pa_backproject(D.sqlaw, cfg,'Comp','r2','Nx',P.Nx,'FOV',P.FOV,'Normalize','none');

gg = [pa_gcnr(IC,R1), pa_gcnr(IM,R1), pa_gcnr(IE,R1)];
pp = [max(IC(:))/(max(IC(R1.out))+eps), max(IM(:))/(max(IM(R1.out))+eps), max(IE(:))/(max(IE(R1.out))+eps)];

ax = ((1:P.Nx)-P.Nx/2)*(P.FOV/(P.Nx-1))*1e3; [~,i0]=min(abs(ax));
ww = [pa_width(ax,IC(i0,:).',0.5), pa_width(ax,IM(i0,:).',0.5), pa_width(ax,sqrt(max(IE(i0,:).',0)),0.5)];
end

function g = pa_gcnr(img,R1)
g = local_gcnr(img(R1.in), img(R1.out));
end

function g = local_gcnr(a,b)
if isempty(a)||isempty(b), g=NaN; return; end
lo=min([a(:);b(:)]); hi=max([a(:);b(:)]); if hi<=lo, g=1; return; end
e=linspace(lo,hi,65); pa=histcounts(a,e); pa=pa/sum(pa);
pb=histcounts(b,e); pb=pb/sum(pb); g=1-sum(min(pa,pb));
end

function w = pa_width(ax,y,lvl)
ax=ax(:).'; y=y(:).'; pk=max(y); if pk<=0, w=NaN; return; end
thr=lvl*pk; n=numel(y); [~,i0]=max(y);
L=i0; while L>1 && y(L)>thr, L=L-1; end
Rr=i0; while Rr<n && y(Rr)>thr, Rr=Rr+1; end
if y(L)>thr, xl=ax(1); else, xl=ax(L)+(thr-y(L))*(ax(L+1)-ax(L))/(y(L+1)-y(L)); end
if y(Rr)>thr, xr=ax(n); else, xr=ax(Rr-1)+(thr-y(Rr-1))*(ax(Rr)-ax(Rr-1))/(y(Rr)-y(Rr-1)); end
w=abs(xr-xl);
end

function R1 = pa_roi2d(P)
dx=P.FOV/(P.Nx-1); qv=((1:P.Nx)-P.Nx/2)*dx;
[X,Y]=meshgrid(qv,qv); r2=X.^2+Y.^2;
R1.in=r2<=(0.5e-3)^2; R1.out=(r2>=(3e-3)^2)&(r2<=(6e-3)^2);
end

function sig = pa_local_synth(P,sx,sy,sigma_phi,cratio,snr_dB)
nCh=numel(sx); t=(0:P.nSamples-1).'/P.fs;
sigF=P.beta_sig*P.f0/2.355; sigT=1/(2*pi*sigF);
sig=zeros(P.nSamples,nCh);
sig=local_add(sig,P,t,[0 0],1,sx,sy,sigT);
if cratio>0
    rng(11); rad=24e-3+10e-3*rand(14,1); ang=2*pi*rand(14,1);
    sig=local_add(sig,P,t,[rad.*cos(ang),rad.*sin(ang)],cratio*ones(14,1),sx,sy,sigT);
end
if sigma_phi>0
    phi=sigma_phi*randn(nCh,1);
    for m=1:nCh, z=hilbert(sig(:,m)).*exp(1i*phi(m)); sig(:,m)=real(z); end
end
refAmp=max(vecnorm(sig,inf,1));
sig=sig+refAmp*10^(-snr_dB/20)*randn(size(sig));
end

function d = local_add(d,P,t,pts,amps,sx,sy,sigT)
for k=1:size(pts,1)
    for m=1:numel(sx)
        rr=hypot(pts(k,1)-sx(m),pts(k,2)-sy(m)); tau=rr/P.vs; a=amps(k)/rr;
        d(:,m)=d(:,m)+a*exp(-((t-tau)/sigT).^2).*cos(2*pi*P.f0*(t-tau));
    end
end
end

function [sx,sy]=pa_sensor_positions(P)
ang=(0:P.N-1)*(pi/(P.N-1))-pi; sx=P.R*cos(ang); sy=P.R*sin(ang);
end

function cfg = pa_build_cfg(P)
cfg=struct(); cfg.name='phase'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
cfg.vs=P.vs; cfg.fs=P.fs; cfg.nSamples=P.nSamples; cfg.FOV=P.FOV; cfg.Nx=P.Nx;
cfg.f0=P.f0; cfg.f_low=P.f_low; cfg.f_high=P.f_high; cfg.f_order=3;
cfg.smooth=1; cfg.dcMethod='median'; cfg.dcFirstN=100; cfg.padLen=[];
cfg.filt='none'; cfg.takeAbs=false; cfg.comp='r'; cfg.bw_law=P.bw_law;
cfg.WL=0.15; cfg.WW=0.70; cfg.nyquist=cfg.fs/2;
B_rf=cfg.f_high-cfg.f_low; cfg.beta_rf=B_rf/cfg.f0;
cfg.sqlaw_lo_cut=B_rf; cfg.sqlaw_hi_cut=2*cfg.f_low;
cfg.sqlaw_ok=cfg.sqlaw_hi_cut>cfg.sqlaw_lo_cut;
if cfg.sqlaw_ok, cfg.lp_cutoff=0.5*(cfg.sqlaw_lo_cut+cfg.sqlaw_hi_cut); else, cfg.lp_cutoff=cfg.f0; end
cfg.sqlaw_narrowband=[cfg.f_low,cfg.f_high];
end

function o = pa_local_opts(o,varargin)
if mod(numel(varargin),2)~=0, error('opts:pair','参数必须成对。'); end
for i=1:2:numel(varargin)
    k=varargin{i}; if ~isfield(o,k), error('opts:unknown','未知参数：%s',k); end
    o.(k)=varargin{i+1};
end
end
