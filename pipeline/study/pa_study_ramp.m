function R = pa_study_ramp(varargin)
%PA_STUDY_RAMP  公平性检查：传统基线是否应带斜坡滤波？
%
%   用户对"主流方法"的定义是：Hilbert 变换 + **滤波**反投影（FBP）。
%   pa_backproject_coherent 的 'Filt' 支持 'none' | 'ramp'。
%   本脚本比较：
%     C      ：Hilbert + 相干 DAS（1/r 补偿），无斜坡滤波
%     C_ramp ：Hilbert + 斜坡(Hamming)滤波 + 相干 DAS（1/r 补偿）  <- 完整"滤波反投影"
%   在 4 个体制下（理想 / 相位像差 / 相干杂波 / 低 SNR）比较 gCNR 与 PSR。
%
%   若 C_ramp 明显优于 C，则正文必须用 C_ramp 作传统基线（否则是"过易对照"）。
%
%   版本：v1  2026-10-14

opt.Nx   = 601; opt.Nrep = 4;
P = struct();
P.fs=40e6; P.nSamples=4096; P.vs=1478; P.f0=5e6; P.beta_sig=0.60; P.bw_law=0.80;
P.R=55e-3; P.FOV=40e-3; P.Nx=opt.Nx; P.arrayType='semicircle128'; P.N=128;
P.f_low=P.f0*(1-P.bw_law/2); P.f_high=P.f0*(1+P.bw_law/2);
cfg = build_cfg(P);
[sx,sy]=sensor_positions(P);
R1 = local_roi(P);

cases = { ...
    'ideal',    0,   0,   40 ; ...   % sigma_phi, cratio, SNR
    'aberr1',   1,   0,   40 ; ...
    'aberr4',   4,   0,   40 ; ...
    'clutter5', 0,   5,   40 ; ...
    'snr0',     0,   0,    0 ; ...
    'snr10',    0,   0,   10 };

fprintf('\n==== pa_study_ramp : 传统基线是否带斜坡滤波 ====\n');
fprintf('  %-10s | %-16s %-16s | %-16s %-16s\n','case', ...
    'gCNR C','gCNR C_ramp','PSR C','PSR C_ramp');
T = struct('name',{},'gC',{},'gCr',{},'pC',{},'pCr',{});
for i = 1:size(cases,1)
    nm=cases{i,1}; sp=cases{i,2}; cr=cases{i,3}; sn=cases{i,4};
    gC=zeros(opt.Nrep,1); gCr=gC; pC=gC; pCr=gC;
    for r=1:opt.Nrep
        rng(700+13*r);
        sig = local_synth(P,sx,sy,sp,cr,sn);
        D = pa_preprocess(sig, cfg, 'Methods', {'filtered'});
        Z = complex(zeros(size(D.filtered)));
        for ch=1:size(D.filtered,2), Z(:,ch)=hilbert(D.filtered(:,ch)); end
        IC  = pa_backproject_coherent(Z, cfg, 'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none', 'Filt','none');
        ICr = pa_backproject_coherent(Z, cfg, 'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none', 'Filt','ramp');
        gC(r)=gcnr(IC(R1.in),IC(R1.out));
        gCr(r)=gcnr(ICr(R1.in),ICr(R1.out));
        pC(r)=max(IC(:))/(max(IC(R1.out))+eps);
        pCr(r)=max(ICr(:))/(max(ICr(R1.out))+eps);
    end
    fprintf('  %-10s | %7.4f±%.4f  %7.4f±%.4f  | %8.2f       %8.2f\n', ...
        nm, mean(gC),std(gC), mean(gCr),std(gCr), mean(pC), mean(pCr));
    T(end+1) = struct('name',nm,'gC',mean(gC),'gCr',mean(gCr),'pC',mean(pC),'pCr',mean(pCr));
end
R = struct('T',T);
outDir = fullfile(fileparts(fileparts(mfilename('fullpath'))),'..','results','study_ramp');
if ~exist(outDir,'dir'), mkdir(outDir); end
save(fullfile(outDir,'study_ramp.mat'),'-struct','R');
fprintf('\n  [out] %s\n', outDir);
end

function sig = local_synth(P,sx,sy,sigma_phi,cratio,snr_dB)
nCh=numel(sx); t=(0:P.nSamples-1).'/P.fs;
sigF=P.beta_sig*P.f0/2.355; sigT=1/(2*pi*sigF);
sig=zeros(P.nSamples,nCh);
sig=sig+local_add(sig,P,t,[0 0],1,sx,sy,sigT);
if cratio>0
    rng(11); rad=24e-3+10e-3*rand(14,1); ang=2*pi*rand(14,1);
    cp=[rad.*cos(ang),rad.*sin(ang)];
    sig=sig+local_add(sig,P,t,cp,cratio*ones(14,1),sx,sy,sigT);
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

function R1 = local_roi(P)
dx=P.FOV/(P.Nx-1); qv=((1:P.Nx)-P.Nx/2)*dx;
[X,Y]=meshgrid(qv,qv); r2=X.^2+Y.^2;
R1.in=r2<=(0.5e-3)^2; R1.out=(r2>=(3e-3)^2)&(r2<=(6e-3)^2);
end

function g = gcnr(a,b)
lo=min([a(:);b(:)]); hi=max([a(:);b(:)]); if hi<=lo, g=1; return; end
e=linspace(lo,hi,65); pa=histcounts(a,e); pa=pa/sum(pa);
pb=histcounts(b,e); pb=pb/sum(pb); g=1-sum(min(pa,pb));
end

function [sx,sy]=sensor_positions(P)
ang=(0:P.N-1)*(pi/(P.N-1))-pi; sx=P.R*cos(ang); sy=P.R*sin(ang);
end

function cfg = build_cfg(P)
cfg=struct(); cfg.name='ramp'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
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
