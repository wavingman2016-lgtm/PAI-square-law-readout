function R = pa_study_cost(varargin)
%PA_STUDY_COST  规范计时（外部评审「数据类」整改项 ⑤）
%
%   问题
%     已发布的算力比（E = 0.56x C）来自**单帧墙钟**，没有预热次数、
%     重复次数、标准差与硬件说明，无法复核。
%
%   方案
%     1) 预热 Nwarm 次（丢弃），消除首次调用的 JIT / 缓存污染；
%     2) 正式重复 Nrep 次，报 均值±标准差；
%     3) 记录硬件与软件元数据（CPU、核心数、MATLAB 版本、操作系统）；
%     4) 分解计时：Hilbert、复数相干反投影、包络叠加反投影、
%        平方+低通预处理、实数能量反投影；
%     5) **端到端口径**：C/M = 前处理(含 Hilbert) + 反投影；
%        E    = 前处理(平方+低通) + 反投影。两臂的预处理各自必需，
%        故端到端是公平口径；「仅反投影」也一并给出供参考。
%
%   输出：results/study_cost/cost.csv + cost.mat
%
%   版本：v1  2026-10-15

opt.Array  = 'semicircle128';
opt.Nx     = 601;
opt.FOV    = 40e-3;
opt.Nwarm  = 3;
opt.Nrep   = 10;
opt.Save   = true;
opt.OutDir = '';
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot   = fileparts(fileparts(mfilename('fullpath')));
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', 'study_cost');
end

P = struct();
P.fs = 40e6;  P.nSamples = 4096;  P.vs = 1478;  P.f0 = 5e6;
P.beta_sig = 0.60;  P.bw_law = 0.80;
P.R = 55e-3;  P.FOV = opt.FOV;  P.Nx = opt.Nx;  P.SNR = 40;
switch lower(opt.Array)
    case 'semicircle128', P.arrayType = 'semicircle128'; P.N = 128;
    case 'ring256',       P.arrayType = 'ring1024';      P.N = 256;
    otherwise, error('pa_study_cost:array', '未知阵列：%s', opt.Array);
end
P.f_low  = P.f0 * (1 - P.bw_law/2);
P.f_high = P.f0 * (1 + P.bw_law/2);
cfg = build_cfg(P);
[sx,sy] = sensor_positions(P);

% ---------------------------------------------------------------- 元数据
env = ver('MATLAB');
[~, cpuInfo] = system('wmic cpu get Name,NumberOfCores /format:list 2>nul');
cpuName = strtrim(regexp(strrep(cpuInfo, sprintf('\r\n'), ' '), 'Name=(.*?)(?:  Number|$)', 'tokens', 'once'));
if isempty(cpuName), cpuName = '(未取到, 见 hostinfo)'; end
hw = struct( ...
    'matlab_version', version, ...
    'matlab_release' , env.Release, ...
    'computer'       , computer, ...
    'cpu'            , cpuName, ...
    'cores'          , feature('numcores'), ...
    'os'             , computer('arch'), ...
    'date'           , datestr(now, 'yyyy-mm-dd HH:MM:SS'));
fprintf('\n==== pa_study_cost : %s | Nx=%d | Nwarm=%d | Nrep=%d ====\n', ...
        opt.Array, opt.Nx, opt.Nwarm, opt.Nrep);
fprintf('  MATLAB %s (%s) | %s | cores=%d | arch=%s\n', ...
        hw.matlab_version, hw.matlab_release, hw.computer, hw.cores, hw.os);

% ---------------------------------------------------------------- 预热
rng(99);
sig = local_synth(P, [0 0], 1, sx, sy, P.SNR);
for w = 1:opt.Nwarm
    one_pass(cfg, P, sx, sy, sig);
end
fprintf('  预热 %d 次完成\n', opt.Nwarm);

% ---------------------------------------------------------------- 正式重复
K = 7;
name = {'tHilbert','tCbp','tMbp','tEbp','tPre_env','tPre_sqlaw','tPre_only'};
T = zeros(numel(name), opt.Nrep);
for r = 1:opt.Nrep
    v = one_pass(cfg, P, sx, sy, sig);
    for k = 1:numel(name), T(k,r) = v.(name{k}); end
end

M = struct('name', {name}, 'mean', mean(T,2), 'sd', std(T,0,2), ...
           'min', min(T,[],2), 'max', max(T,[],2), 'Nrep', opt.Nrep);
for k = 1:numel(name)
    M.(name{k}) = M.mean(k);
end
% 端到端口径
e2e_c = M.tPre_env  + M.tHilbert + M.tCbp;      % C: 包络/滤波前处理 + Hilbert + 相干反投影
e2e_m = M.tPre_env  + M.tHilbert + M.tMbp;      % M: 同上 + 包络叠加
e2e_e = M.tPre_only + M.tEbp;                   % E: 平方+低通前处理 + 实数反投影
% 逐次比值（比值比「均值之比」更稳健）
tC_r = (T(5,:) + T(1,:) + T(2,:));
tM_r = (T(5,:) + T(1,:) + T(3,:));
tE_r = (T(7,:) + T(4,:));
M.e2e_c = e2e_c;  M.e2e_m = e2e_m;  M.e2e_e = e2e_e;
M.ratio_EC_mean = mean(tE_r ./ tC_r);
M.ratio_EC_sd   = std(tE_r ./ tC_r);
M.ratio_EM_mean = mean(tE_r ./ tM_r);
M.ratio_EM_sd   = std(tE_r ./ tM_r);
M.bp_ratio_EC   = M.tEbp / M.tCbp;              % 仅反投影
M.bp_ratio_EM   = M.tEbp / M.tMbp;
M.hw = hw;  M.T = T;  M.P = P;

fprintf('\n  %-14s %10s %10s %10s %10s\n', '环节', 'mean(s)', 'sd(s)', 'min(s)', 'max(s)');
for k = 1:numel(name)
    fprintf('  %-14s %10.4f %10.4f %10.4f %10.4f\n', ...
            name{k}, M.mean(k), M.sd(k), M.min(k), M.max(k));
end
fprintf('\n  端到端（各臂必需前处理 + 反投影）：\n');
fprintf('    C = %8.4f ± %.4f s\n', e2e_c, std(tC_r));
fprintf('    M = %8.4f ± %.4f s\n', e2e_m, std(tM_r));
fprintf('    E = %8.4f ± %.4f s\n', e2e_e, std(tE_r));
fprintf('    E/C = %.4f ± %.4f   E/M = %.4f ± %.4f\n', ...
        M.ratio_EC_mean, M.ratio_EC_sd, M.ratio_EM_mean, M.ratio_EM_sd);
fprintf('  仅反投影： E/C = %.4f   E/M = %.4f\n', M.bp_ratio_EC, M.bp_ratio_EM);

% ---------------------------------------------------------------- 存盘
if opt.Save
    if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end
    save(fullfile(opt.OutDir, 'cost.mat'), '-struct', 'M', '-v7.3');
    fid = fopen(fullfile(opt.OutDir, 'cost.csv'), 'w');
    fprintf(fid, 'stage,mean_s,sd_s,min_s,max_s,Nrep\n');
    for k = 1:numel(name)
        fprintf(fid, '%s,%.6f,%.6f,%.6f,%.6f,%d\n', name{k}, ...
                M.mean(k), M.sd(k), M.min(k), M.max(k), opt.Nrep);
    end
    fprintf(fid, 'e2e_C,%.6f,,,,\n', e2e_c);
    fprintf(fid, 'e2e_M,%.6f,,,,\n', e2e_m);
    fprintf(fid, 'e2e_E,%.6f,,,,\n', e2e_e);
    fprintf(fid, 'ratio_E_over_C,%.6f,%.6f,,,\n', M.ratio_EC_mean, M.ratio_EC_sd);
    fprintf(fid, 'ratio_E_over_M,%.6f,%.6f,,,\n', M.ratio_EM_mean, M.ratio_EM_sd);
    fprintf(fid, 'bp_ratio_E_over_C,%.6f,,,,\n', M.bp_ratio_EC);
    fprintf(fid, 'bp_ratio_E_over_M,%.6f,,,,\n', M.bp_ratio_EM);
    fprintf(fid, '# matlab=%s release=%s computer=%s cores=%d arch=%s date=%s\n', ...
            hw.matlab_version, hw.matlab_release, hw.computer, hw.cores, hw.os, hw.date);
    fprintf(fid, '# cpu=%s\n', strrep(hw.cpu, ',', ' '));
    fclose(fid);
    fprintf('\n  [out] %s\n', opt.OutDir);
end
R = M;
end

% ==================================================================
function v = one_pass(cfg, P, sx, sy, sig)
t = tic;  D = pa_preprocess(sig, cfg, 'Methods', {'env','env2','sqlaw','filtered'});  t1 = toc(t);
t = tic;
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
tH = toc(t);
t = tic;  IC = coherent_bp(Z, cfg, P, 'r');                                        tC = toc(t);
t = tic;  IM = pa_backproject(D.env,   cfg, 'Comp','r',  'Nx',P.Nx,'FOV',P.FOV,'Normalize','none'); tM = toc(t);
t = tic;  IE = pa_backproject(D.sqlaw, cfg, 'Comp','r2', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none'); tE = toc(t);
t = tic;  De = pa_preprocess(sig, cfg, 'Methods', {'env','filtered'});              tPE = toc(t);
t = tic;  Ds = pa_preprocess(sig, cfg, 'Methods', {'sqlaw'});                       tPS = toc(t);
v = struct('tHilbert',tH,'tCbp',tC,'tMbp',tM,'tEbp',tE, ...
           'tPre_env',tPE,'tPre_sqlaw',tPS,'tPre_only',tPS);
end

% ==================================================================
function IC = coherent_bp(Z, cfg, P, comp)
Nx = P.Nx; FOV = P.FOV; dx = FOV/(Nx-1);
qv = ((1:Nx)-Nx/2)*dx;  [XC,YC] = meshgrid(qv,qv);
[SX,SY] = sensor_positions(P);
nS = size(Z,1);  nCh = size(Z,2);
ACC = zeros(Nx,Nx);
for ch = 1:nCh
    d = hypot(XC-SX(ch), YC-SY(ch));
    tidx = d/cfg.vs*cfg.fs + 1;
    valid = (tidx >= 1) & (tidx <= nS);
    vr = interp1(1:nS, real(Z(:,ch)), tidx(:), 'linear', 0);
    vi = interp1(1:nS, imag(Z(:,ch)), tidx(:), 'linear', 0);
    v  = reshape(vr + 1i*vi, Nx, Nx);
    switch lower(comp)
        case 'r',  wgt = (d + 1e-6)/cfg.R;
        case 'r2', wgt = ((d + 1e-6)/cfg.R).^2;
        otherwise,  wgt = ones(size(d));
    end
    ACC = ACC + v .* wgt .* valid;
end
IC = abs(ACC);
end

% ==================================================================
function sig = local_synth(P, pts, amps, sx, sy, SNRdB)
nCh = numel(sx);  t = (0:P.nSamples-1).'/P.fs;
sigF = P.beta_sig*P.f0/2.355;  sigT = 1/(2*pi*sigF);
sig  = zeros(P.nSamples, nCh);
for k = 1:size(pts,1)
    for m = 1:nCh
        rr  = hypot(pts(k,1)-sx(m), pts(k,2)-sy(m));
        tau = rr/P.vs;   a = amps(k)/rr;
        g   = exp(-((t-tau)/sigT).^2) .* cos(2*pi*P.f0*(t-tau));
        sig(:,m) = sig(:,m) + a*g;
    end
end
refAmp = max(vecnorm(sig, inf, 1));
sig = sig + refAmp*10^(-SNRdB/20)*randn(size(sig));
end

function [sx,sy] = sensor_positions(P)
switch lower(P.arrayType)
    case 'semicircle128', ang = (0:P.N-1)*(pi/(P.N-1)) - pi;
    otherwise,            ang = (0:P.N-1)*(2*pi/P.N);
end
sx = P.R*cos(ang);  sy = P.R*sin(ang);
end

function cfg = build_cfg(P)
cfg = struct();
cfg.name='cost'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
cfg.vs=P.vs; cfg.fs=P.fs; cfg.nSamples=P.nSamples; cfg.FOV=P.FOV; cfg.Nx=P.Nx;
cfg.f0=P.f0; cfg.f_low=P.f_low; cfg.f_high=P.f_high; cfg.f_order=3;
cfg.smooth=1; cfg.dcMethod='median'; cfg.dcFirstN=100; cfg.padLen=[];
cfg.filt='none'; cfg.takeAbs=false; cfg.comp='r'; cfg.bw_law=P.bw_law;
cfg.WL=0.15; cfg.WW=0.70; cfg.nyquist=cfg.fs/2;
B_rf = cfg.f_high - cfg.f_low;  cfg.beta_rf = B_rf/cfg.f0;
cfg.sqlaw_lo_cut = B_rf;  cfg.sqlaw_hi_cut = 2*cfg.f_low;
cfg.sqlaw_ok = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;
if cfg.sqlaw_ok, cfg.lp_cutoff = 0.5*(cfg.sqlaw_lo_cut + cfg.sqlaw_hi_cut);
else,            cfg.lp_cutoff = cfg.f0; end
cfg.sqlaw_narrowband = [cfg.f_low, cfg.f_high];
end

function o = parse_opts(o, varargin)
if mod(numel(varargin),2) ~= 0, error('parse_opts:pair','参数必须成对。'); end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o,k), error('parse_opts:unknown','未知参数：%s', k); end
    o.(k) = varargin{i+1};
end
end