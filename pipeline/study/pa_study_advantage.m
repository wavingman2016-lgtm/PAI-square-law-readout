function R = pa_study_advantage(varargin)
%PA_STUDY_ADVANTAGE  本文方法的「可主张优势」四轴验证
%
%   问题（回应："本方法必须带来某些可量化指标的优化，否则无法自圆其说"）
%     把「本文能量域重建 E」相对「传统相干反投影 C」与「包络基线 M」的
%     **可主张优势**在受控条件下逐条量化，并同时暴露其代价。
%
%   四轴
%     A 视角扇区缺失：把连续一段角度的通道置零（模拟有限视角 / 探头局部失效 /
%        OADAT 多段旋转采集）。比例 0/12.5/25/37.5/50%。
%       预期：C 依赖相位相干积累，扇区缺失致有限角伪影 -> gCNR 崩；
%             相位盲族（M/E）只是少加若干项 -> 稳。
%     B 随机通道缺失：同一比例随机置零（模拟阵元随机失效）。
%     C 几何补偿消融：E 原生用 r^2（能量域匹配）。改 r 后宽度是否追平 M？
%       -> 若追平，则"E 更宽"是实现选择问题而非本质缺陷。
%     D 计算成本：同一帧数据，C（含逐通道 Hilbert）vs E（平方+低通）的墙钟时间。
%
%   口径（与 pa_study_regime 一致，本项目**主口径**）
%     2D 病灶 ROI：in = 以目标为心、半径 0.5 mm 圆盘；out = 3~6 mm 圆环。
%     gCNR 为主指标（对单调映射不变 -> 唯一合法的跨臂指标）。
%     公平宽度：全部还原到幅度域 -6 dB（E 取 sqrt(I_E)）。
%
%   统计：每个条件做 Nrep 次独立噪声实现，报 均值±标准差。
%
%   版本：v1  2026-10-14

opt.Array   = 'semicircle128';
opt.SNR     = 40;
opt.Nx      = 601;      % v2 修正：Nx=401 时 ROI 仅约 80 像素，gCNR 饱和到 1.0，无区分度
opt.FOV     = 40e-3;
opt.Nrep    = 5;
opt.Save    = true;
opt.OutDir  = '';
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot   = fileparts(fileparts(mfilename('fullpath')));
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', sprintf('study_adv_%s', opt.Array));
end

P = struct();
P.fs=40e6; P.nSamples=4096; P.vs=1478; P.f0=5e6; P.beta_sig=0.60; P.bw_law=0.80;
P.R=55e-3; P.FOV=opt.FOV; P.Nx=opt.Nx; P.SNR=opt.SNR;
switch lower(opt.Array)
    case 'semicircle128', P.arrayType='semicircle128'; P.N=128;
    case 'ring256',       P.arrayType='ring1024';      P.N=256;
    otherwise, error('pa_study_advantage:array','未知阵列：%s', opt.Array);
end
P.f_low=P.f0*(1-P.bw_law/2); P.f_high=P.f0*(1+P.bw_law/2);
cfg = build_cfg(P);
[sx, sy] = sensor_positions(P);

fprintf('\n==== pa_study_advantage : %s | Nx=%d | Nrep=%d ====\n', opt.Array, opt.Nx, opt.Nrep);

R = struct('P',P,'cfg',cfg);

% ==================================================================
%  轴 A / B：视角扇区缺失 与 随机通道缺失
% ==================================================================
fracList = [0 0.125 0.25 0.375 0.50];
nF = numel(fracList);
A = struct('frac', fracList, ...
    'gA_C',nan(1,nF),'gA_M',nan(1,nF),'gA_E',nan(1,nF),...
    'gA_Csd',nan(1,nF),'gA_Msd',nan(1,nF),'gA_Esd',nan(1,nF),...
    'gB_C',nan(1,nF),'gB_M',nan(1,nF),'gB_E',nan(1,nF),...
    'gB_Csd',nan(1,nF),'gB_Msd',nan(1,nF),'gB_Esd',nan(1,nF));
B = A;

fprintf('\n---- 轴 A 视角扇区缺失（连续角度块置零）----\n');
fprintf('  %6s | %-13s %-13s %-13s | d(E-C)   d(E-M)\n','frac','gCNR_C','gCNR_M','gCNR_E');
for i = 1:nF
    [A.gA_C(i),A.gA_M(i),A.gA_E(i), A.gA_Csd(i),A.gA_Msd(i),A.gA_Esd(i)] = ...
        local_sweep(cfg,P,sx,sy,fracList(i),'sector',opt.Nrep);
    fprintf('  %5.1f%% | %6.4f±%.4f %6.4f±%.4f %6.4f±%.4f | %+7.4f  %+7.4f\n', ...
        100*fracList(i), A.gA_C(i),A.gA_Csd(i), A.gA_M(i),A.gA_Msd(i), A.gA_E(i),A.gA_Esd(i), ...
        A.gA_E(i)-A.gA_C(i), A.gA_E(i)-A.gA_M(i));
end

fprintf('\n---- 轴 B 随机通道缺失 ----\n');
fprintf('  %6s | %-13s %-13s %-13s | d(E-C)   d(E-M)\n','frac','gCNR_C','gCNR_M','gCNR_E');
for i = 1:nF
    [B.gB_C(i),B.gB_M(i),B.gB_E(i), B.gB_Csd(i),B.gB_Msd(i),B.gB_Esd(i)] = ...
        local_sweep(cfg,P,sx,sy,fracList(i),'random',opt.Nrep);
    fprintf('  %5.1f%% | %6.4f±%.4f %6.4f±%.4f %6.4f±%.4f | %+7.4f  %+7.4f\n', ...
        100*fracList(i), B.gB_C(i),B.gB_Csd(i), B.gB_M(i),B.gB_Msd(i), B.gB_E(i),B.gB_Esd(i), ...
        B.gB_E(i)-B.gB_C(i), B.gB_E(i)-B.gB_M(i));
end
R.A = A; R.B = B;

% ==================================================================
%  轴 C：几何补偿消融（E: r^2 vs r）
% ==================================================================
fprintf('\n---- 轴 C 几何补偿消融（E 的公平宽度与 gCNR）----\n');
C = struct('wC',nan,'wM',nan,'wE_r2',nan,'wE_r',nan, ...
           'gC',nan,'gM',nan,'gE_r2',nan,'gE_r',nan, ...
           'wC_sd',nan,'wM_sd',nan,'wE_r2_sd',nan,'wE_r_sd',nan);
[wC,wM,wE2,wEr, gC,gM,gE2,gEr, wCs,wMs,wE2s,wErs] = local_compens_ablation(cfg,P,sx,sy,opt.Nrep);
C.wC=wC; C.wM=wM; C.wE_r2=wE2; C.wE_r=wEr;
C.gC=gC; C.gM=gM; C.gE_r2=gE2; C.gE_r=gEr;
C.wC_sd=wCs; C.wM_sd=wMs; C.wE_r2_sd=wE2s; C.wE_r_sd=wErs;
fprintf('  公平宽度(mm): C=%.4f  M=%.4f  E(r2)=%.4f  E(r)=%.4f\n', wC,wM,wE2,wEr);
fprintf('  gCNR        : C=%.4f  M=%.4f  E(r2)=%.4f  E(r)=%.4f\n', gC,gM,gE2,gEr);
fprintf('  => E(r)/E(r2) 宽度比 = %.3f  (>1 表示 r 补偿更宽；<1 表示更窄/追平)\n', wEr/max(wE2,eps));
R.C = C;

% ==================================================================
%  轴 D：计算成本（C 含 Hilbert vs E 平方+低通）
% ==================================================================
fprintf('\n---- 轴 D 计算成本（单帧重建，同网格同核）----\n');
D = local_cost(cfg,P,sx,sy);
fprintf('  C (Hilbert + 复数相干反投影): %.3f s\n', D.tC);
fprintf('  M (Hilbert + 包络叠加)      : %.3f s\n', D.tM);
fprintf('  E (平方+低通 + 实数反投影)   : %.3f s\n', D.tE);
fprintf('  => E/C = %.2fx ; E/M = %.2fx （<1 表示更快）\n', D.tE/D.tC, D.tE/D.tM);
R.D = D;

% ==================================================================
if opt.Save
    if ~exist(opt.OutDir,'dir'), mkdir(opt.OutDir); end
    save(fullfile(opt.OutDir,'study_advantage.mat'),'-struct','R','-v7.3');
    fprintf('\n  [out] %s\n', opt.OutDir);
end
end

% ==================================================================
function [gC,gM,gE, sC,sM,sE] = local_sweep(cfg,P,sx,sy,frac,mode,Nrep)
nCh = numel(sx);
gC=zeros(Nrep,1); gM=gC; gE=gC;
baseAng = atan2(sy,sx);
for r = 1:Nrep
    rng(1000 + 37*r + round(100*frac));
    sig = local_synth(P,[0 0],1,sx,sy);
    keep = true(1,nCh);
    nDrop = round(frac*nCh);
    if nDrop > 0
        if strcmpi(mode,'sector')
            % 连续角度块：丢掉最小的一段。
            % v2 修正：分母必须是**阵列实际覆盖的角度跨度**（半环 = pi，全环 = 2pi），
            % 原写法按 2pi 归一，在半环阵列上使 frac=0.375 实际只保留了约 1/8 通道。
            a = mod(baseAng + pi, 2*pi);            % 归一到 [0,2pi)
            if strcmpi(P.arrayType,'semicircle128'), span = pi; else, span = 2*pi; end
            keep = a >= (span*frac);                % 丢掉 a 最小的一段
        else
            idx = randperm(nCh, nDrop);
            keep(idx) = false;
        end
    end
    sig(:,~keep) = 0;
    [~,img,~] = local_arms(sig,cfg,P);
    R1 = local_roi(P);
    gC(r)=local_img_gcnr(img.C,R1); gM(r)=local_img_gcnr(img.M,R1); gE(r)=local_img_gcnr(img.E,R1);
end
sC=std(gC); sM=std(gM); sE=std(gE);
gC=mean(gC); gM=mean(gM); gE=mean(gE);
end

% ==================================================================
function [wC,wM,wE2,wEr, gC,gM,gE2,gEr, wCs,wMs,wE2s,wErs] = local_compens_ablation(cfg,P,sx,sy,Nrep)
wC=zeros(Nrep,1); wM=wC; wE2=wC; wEr=wC;
gC=wC; gM=wC; gE2=wC; gEr=wC;
for r = 1:Nrep
    rng(500 + 11*r);
    sig = local_synth(P,[0 0],1,sx,sy);
    D = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','filtered'});
    Z = complex(zeros(size(D.filtered)));
    for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
    IC = local_complex_backproject(Z, cfg, P, 'r');
    IM = pa_backproject(D.env,   cfg,'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
    IE2= pa_backproject(D.sqlaw, cfg,'Comp','r2','Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
    IEr= pa_backproject(D.sqlaw, cfg,'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
    ax = ((1:P.Nx)-P.Nx/2)*(P.FOV/(P.Nx-1))*1e3; [~,i0]=min(abs(ax));
    wC(r) = local_width(ax, IC(i0,:).', 0.5);
    wM(r) = local_width(ax, IM(i0,:).', 0.5);
    wE2(r)= local_width(ax, sqrt(max(IE2(i0,:).',0)), 0.5);
    wEr(r)= local_width(ax, sqrt(max(IEr(i0,:).',0)), 0.5);
    R1 = local_roi(P);
    gC(r)=local_img_gcnr(IC,R1); gM(r)=local_img_gcnr(IM,R1);
    gE2(r)=local_img_gcnr(IE2,R1); gEr(r)=local_img_gcnr(IEr,R1);
end
wCs=std(wC); wMs=std(wM); wE2s=std(wE2); wErs=std(wEr);
wC=mean(wC); wM=mean(wM); wE2=mean(wE2); wEr=mean(wEr);
gC=mean(gC); gM=mean(gM); gE2=mean(gE2); gEr=mean(gEr);
end

% ==================================================================
function D = local_cost(cfg,P,sx,sy)
rng(99);
sig = local_synth(P,[0 0],1,sx,sy);
% 预热（避免首次调用开销污染计时）
D0 = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','filtered'});
t=tic; Z=complex(zeros(size(D0.filtered)));
for ch=1:size(D0.filtered,2), Z(:,ch)=hilbert(D0.filtered(:,ch)); end
tHil = toc(t);
t=tic; IC=local_complex_backproject(Z,cfg,P,'r'); tCbp=toc(t);
t=tic; IM=pa_backproject(D0.env,  cfg,'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none'); tMbp=toc(t);
t=tic; IE=pa_backproject(D0.sqlaw,cfg,'Comp','r2','Nx',P.Nx,'FOV',P.FOV,'Normalize','none'); tEbp=toc(t);
t=tic; D1=pa_preprocess(sig, cfg, 'Methods', {'sqlaw'}); tPre=toc(t);
D = struct('tHilbert',tHil,'tC',tHil+tCbp,'tM',tHil+tMbp,'tE',tPre+tEbp, ...
           'tCbp',tCbp,'tMbp',tMbp,'tEbp',tEbp,'tPre',tPre);
end

% ==================================================================
function [prof, img, IC] = local_arms(sig, cfg, P)
D = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','filtered'});
Z = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
IC = local_complex_backproject(Z, cfg, P, 'r');
IM = pa_backproject(D.env,   cfg,'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IE = pa_backproject(D.sqlaw, cfg,'Comp','r2','Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
ax = ((1:P.Nx)-P.Nx/2)*(P.FOV/(P.Nx-1))*1e3; [~,i0]=min(abs(ax));
img.C=IC; img.M=IM; img.E=IE;
prof.ax=ax; prof.C=IC(i0,:).'; prof.M=IM(i0,:).'; prof.E=IE(i0,:).';
end

function IC = local_complex_backproject(Z, cfg, P, comp)
Nx=P.Nx; FOV=P.FOV; dx=FOV/(Nx-1);
qv=((1:Nx)-Nx/2)*dx; [XC,YC]=meshgrid(qv,qv);
[SX,SY]=sensor_positions(P);
nS=size(Z,1); nCh=size(Z,2);
ACC=zeros(Nx,Nx);
for ch=1:nCh
    d=hypot(XC-SX(ch),YC-SY(ch));
    tidx=d/cfg.vs*cfg.fs+1; valid=(tidx>=1)&(tidx<=nS);
    vr=interp1(1:nS,real(Z(:,ch)),tidx(:),'linear',0);
    vi=interp1(1:nS,imag(Z(:,ch)),tidx(:),'linear',0);
    v=reshape(vr+1i*vi,Nx,Nx);
    switch lower(comp)
        case 'r', wgt=(d+1e-6)/cfg.R;
        case 'r2',wgt=((d+1e-6)/cfg.R).^2;
        otherwise,wgt=ones(size(d));
    end
    ACC=ACC+v.*wgt.*valid;
end
IC=abs(ACC);
end

% ==================================================================
function R1 = local_roi(P)
dx=P.FOV/(P.Nx-1); qv=((1:P.Nx)-P.Nx/2)*dx;
[X,Y]=meshgrid(qv,qv); r2=X.^2+Y.^2;
R1.in  = r2 <= (0.5e-3)^2;
R1.out = (r2 >= (3e-3)^2) & (r2 <= (6e-3)^2);
end

function g = local_img_gcnr(img, R1)
g = gcnr(img(R1.in), img(R1.out));
end

function g = gcnr(a,b)
if isempty(a)||isempty(b), g=NaN; return; end
lo=min([a(:);b(:)]); hi=max([a(:);b(:)]);
if hi<=lo, g=1; return; end
e=linspace(lo,hi,65);
pa=histcounts(a,e); pa=pa/sum(pa);
pb=histcounts(b,e); pb=pb/sum(pb);
g=1-sum(min(pa,pb));
end

function w = local_width(ax,y,lvl)
ax=ax(:).'; y=y(:).'; pk=max(y); if pk<=0, w=NaN; return; end
thr=lvl*pk; n=numel(y); [~,i0]=max(y);
L=i0; while L>1 && y(L)>thr, L=L-1; end
Rr=i0; while Rr<n && y(Rr)>thr, Rr=Rr+1; end
if y(L)>thr, xl=ax(1); else, xl=ax(L)+(thr-y(L))*(ax(L+1)-ax(L))/(y(L+1)-y(L)); end
if y(Rr)>thr, xr=ax(n); else, xr=ax(Rr-1)+(thr-y(Rr-1))*(ax(Rr)-ax(Rr-1))/(y(Rr)-y(Rr-1)); end
w=abs(xr-xl);
end

function sig = local_synth(P,pts,amps,sx,sy)
nCh=numel(sx); t=(0:P.nSamples-1).'/P.fs;
sigF=P.beta_sig*P.f0/2.355; sigT=1/(2*pi*sigF);
sig=zeros(P.nSamples,nCh);
for k=1:size(pts,1)
    for m=1:nCh
        rr=hypot(pts(k,1)-sx(m),pts(k,2)-sy(m));
        tau=rr/P.vs; a=amps(k)/rr;
        g=exp(-((t-tau)/sigT).^2).*cos(2*pi*P.f0*(t-tau));
        sig(:,m)=sig(:,m)+a*g;
    end
end
refAmp=max(vecnorm(sig,inf,1));
sig=sig+refAmp*10^(-P.SNR/20)*randn(size(sig));
end

function [sx,sy]=sensor_positions(P)
switch lower(P.arrayType)
    case 'semicircle128', ang=(0:P.N-1)*(pi/(P.N-1))-pi;
    otherwise,            ang=(0:P.N-1)*(2*pi/P.N);
end
sx=P.R*cos(ang); sy=P.R*sin(ang);
end

function cfg = build_cfg(P)
cfg=struct();
cfg.name='adv'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
cfg.vs=P.vs; cfg.fs=P.fs; cfg.nSamples=P.nSamples; cfg.FOV=P.FOV; cfg.Nx=P.Nx;
cfg.f0=P.f0; cfg.f_low=P.f_low; cfg.f_high=P.f_high; cfg.f_order=3;
cfg.smooth=1; cfg.dcMethod='median'; cfg.dcFirstN=100; cfg.padLen=[];
cfg.filt='none'; cfg.takeAbs=false; cfg.comp='r'; cfg.bw_law=P.bw_law;
cfg.WL=0.15; cfg.WW=0.70; cfg.nyquist=cfg.fs/2;
B_rf=cfg.f_high-cfg.f_low; cfg.beta_rf=B_rf/cfg.f0;
cfg.sqlaw_lo_cut=B_rf; cfg.sqlaw_hi_cut=2*cfg.f_low;
cfg.sqlaw_ok=cfg.sqlaw_hi_cut>cfg.sqlaw_lo_cut;
if cfg.sqlaw_ok, cfg.lp_cutoff=0.5*(cfg.sqlaw_lo_cut+cfg.sqlaw_hi_cut);
else, cfg.lp_cutoff=cfg.f0; end
cfg.sqlaw_narrowband=[cfg.f_low,cfg.f_high];
end

function o = parse_opts(o,varargin)
if mod(numel(varargin),2)~=0, error('parse_opts:pair','参数必须成对。'); end
for i=1:2:numel(varargin)
    k=varargin{i}; if ~isfield(o,k), error('parse_opts:unknown','未知参数：%s',k); end
    o.(k)=varargin{i+1};
end
end
