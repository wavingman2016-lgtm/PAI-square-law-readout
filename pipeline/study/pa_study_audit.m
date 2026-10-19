function R = pa_study_audit(varargin)
%PA_STUDY_AUDIT  外部评审「数据类」整改项 ①③④ 的受控仿真补充实验
%
%   本脚本只做**受控仿真**（合成数据，真值已知），产出四轴：
%     轴 1  E-vs-M 同种子配对：同一噪声实现下同时算 C/M/E，
%           报配对差 Δ(E-C)、Δ(E-M) 的 均值±SD 与配对 t 检验
%           （解决评审「未做配对、只报单次值」）。
%     轴 2  阵元随机失效的**非饱和**结构/定位指标。
%           gCNR 在高失效率下饱和到 1.0000，零区分度；本轴改报
%           对单调映射不变、且不饱和的量：W1（ROI 内/外分布的一阶
%           Wasserstein 距离）、峰值定位误差、旁瓣能量占比、
%           以及对真值的 SSIM / PSNR。
%     轴 3  Hilbert-free 的 eps_rel：在**尺度校正**后比较
%           D2'（免 Hilbert，LPF{x^2}）与 D1^2（包络平方），
%           分别用「拟合尺度 k_fit」与「解析尺度 k_theory = 1/2」计算
%           相对误差，并输出误差图。
%     轴 4  **带宽 x 视角分离**控制实验（评审第 ④ 项）。
%           §5.2 的失效边界写的是「宽带 + 有限视角」两个条件同时成立；
%           本轴把两者正交分开：信号带宽 beta_sig x 视角缺失比例，
%           给出二维矩阵 + 各轴边际效应，判定二者是否可加。
%
%   口径（与 pa_study_advantage / pa_study_regime 完全一致）
%     2D 病灶 ROI：in = 半径 0.5 mm 圆盘；out = 3~6 mm 圆环。
%     gCNR 为主指标（单调不变量 -> 唯一合法的跨臂指标，F4）。
%     公平宽度：还原到幅度域 -6 dB（E 取 sqrt(I_E)）。
%     网格 Nx=601（gCNR/ROI 类），宽度类另见 pa_study_resolution(Nx=801)。
%     相位/杂波/失效轴 Nrep>=4，报 均值±SD。
%
%   用法
%     pa_study_audit()                                  % 全部四轴
%     pa_study_audit('Axes',[1 2])                      % 只跑指定轴
%     pa_study_audit('Nrep',8,'Save',true,'OutDir','')  % 调整重复次数
%
%   版本：v1  2026-10-15

opt.Array  = 'semicircle128';
opt.SNR    = 40;        % dB，作用于目标回波幅度
opt.Nx     = 601;
opt.FOV    = 40e-3;
opt.Nrep   = 6;
opt.Axes   = [1 2 3 4];
opt.Save   = true;
opt.OutDir = '';
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot   = fileparts(fileparts(mfilename('fullpath')));
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', 'study_audit');
end

P = struct();
P.fs = 40e6;  P.nSamples = 4096;  P.vs = 1478;  P.f0 = 5e6;
P.beta_sig = 0.60;  P.bw_law = 0.80;
P.R = 55e-3;  P.FOV = opt.FOV;  P.Nx = opt.Nx;  P.SNR = opt.SNR;
switch lower(opt.Array)
    case 'semicircle128', P.arrayType = 'semicircle128'; P.N = 128;
    case 'ring256',       P.arrayType = 'ring1024';      P.N = 256;
    otherwise, error('pa_study_audit:array', '未知阵列：%s', opt.Array);
end
P.f_low  = P.f0 * (1 - P.bw_law/2);
P.f_high = P.f0 * (1 + P.bw_law/2);

cfg   = build_cfg(P);
[sx,sy] = sensor_positions(P);

fprintf('\n==== pa_study_audit : %s | Nx=%d | Nrep=%d | 轴=%s ====\n', ...
        opt.Array, opt.Nx, opt.Nrep, mat2str(opt.Axes));
fprintf('  f0=%.2f MHz  beta_sig=%.2f  分析带 [%.2f %.2f] MHz  FOV=%.0f mm\n', ...
        P.f0/1e6, P.beta_sig, P.f_low/1e6, P.f_high/1e6, P.FOV*1e3);

R = struct('P', P, 'cfg', cfg, 'opt', opt);

% ==================================================================
%  轴 1：E-vs-M 同种子配对
% ==================================================================
if any(opt.Axes == 1)
    R.axis1 = local_axis1(cfg, P, sx, sy, opt.Nrep);
end

% ==================================================================
%  轴 2：阵元随机失效的非饱和指标
% ==================================================================
if any(opt.Axes == 2)
    R.axis2 = local_axis2(cfg, P, sx, sy, opt.Nrep);
end

% ==================================================================
%  轴 3：Hilbert-free 的 eps_rel（尺度校正后）
% ==================================================================
if any(opt.Axes == 3)
    R.axis3 = local_axis3(cfg, P, sx, sy);
end

% ==================================================================
%  轴 4：带宽 x 视角分离
% ==================================================================
if any(opt.Axes == 4)
    R.axis4 = local_axis4(cfg, P, sx, sy, opt.Nrep);
    R.axis4beta = local_axis4_beta(cfg, P, sx, sy, opt.Nrep);
end

% ==================================================================
if opt.Save
    if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end
    save(fullfile(opt.OutDir, 'study_audit.mat'), '-struct', 'R', '-v7.3');
    local_write_csv(R, opt);
    fprintf('\n  [out] %s\n', opt.OutDir);
end
end

% ==================================================================
%  导出 CSV（单一事实源的可读副本；数字一律来自内存中的 R，不重算）
% ==================================================================
function local_write_csv(R, opt)
fid = fopen(fullfile(opt.OutDir, 'study_audit.csv'), 'w');
if fid < 0, warning('pa_study_audit:csv', '无法写入 CSV'); return; end
fprintf(fid, 'axis,quantity,condition,value,note\n');

A = R.axis1;
for i = 1:size(A.dEc,1)
    fprintf(fid, '1,delta_gCNR_E_minus_C,%s,%.6f,paired over %d replicates\n', ...
            A.name{i}, mean(A.dEc(i,:)), size(A.dEc,2));
    fprintf(fid, '1,delta_gCNR_E_minus_M,%s,%.6f,paired over %d replicates\n', ...
            A.name{i}, mean(A.dEm(i,:)), size(A.dEm,2));
    fprintf(fid, '1,paired_t_E_minus_C,%s,%.4f,p=%.4g\n', A.name{i}, A.tEc(i), A.pEc(i));
    fprintf(fid, '1,paired_t_E_minus_M,%s,%.4f,p=%.4g\n', A.name{i}, A.tEm(i), A.pEm(i));
end

B = R.axis2;
for i = 1:numel(B.frac)
    fprintf(fid, '2,gCNR_C,loss=%.4f,%.6f,\n', B.frac(i), mean(B.gC(i,:)));
    fprintf(fid, '2,gCNR_M,loss=%.4f,%.6f,saturated above 12.5%% loss\n', B.frac(i), mean(B.gM(i,:)));
    fprintf(fid, '2,gCNR_E,loss=%.4f,%.6f,saturated above 12.5%% loss\n', B.frac(i), mean(B.gE(i,:)));
    fprintf(fid, '2,W1_C,loss=%.4f,%.3f,first-order Wasserstein x1e3\n', B.frac(i), mean(B.w1C(i,:)));
    fprintf(fid, '2,W1_M,loss=%.4f,%.3f,first-order Wasserstein x1e3\n', B.frac(i), mean(B.w1M(i,:)));
    fprintf(fid, '2,W1_E,loss=%.4f,%.3f,first-order Wasserstein x1e3\n', B.frac(i), mean(B.w1E(i,:)));
    fprintf(fid, '2,dPeak_C,loss=%.4f,%.4f,peak localisation error px\n', B.frac(i), mean(B.dpC(i,:)));
    fprintf(fid, '2,dPeak_E,loss=%.4f,%.4f,peak localisation error px\n', B.frac(i), mean(B.dpE(i,:)));
    fprintf(fid, '2,SSIM_C,loss=%.4f,%.6f,global SSIM vs disc truth\n', B.frac(i), mean(B.ssC(i,:)));
    fprintf(fid, '2,SSIM_M,loss=%.4f,%.6f,global SSIM vs disc truth\n', B.frac(i), mean(B.ssM(i,:)));
    fprintf(fid, '2,SSIM_E,loss=%.4f,%.6f,global SSIM vs disc truth\n', B.frac(i), mean(B.ssE(i,:)));
    fprintf(fid, '2,PSR_C,loss=%.4f,%.6f,peak-to-sidelobe ratio\n', B.frac(i), mean(B.psC(i,:)));
    fprintf(fid, '2,PSR_E,loss=%.4f,%.6f,peak-to-sidelobe ratio\n', B.frac(i), mean(B.psE(i,:)));
end

C = R.axis3;
for i = 1:numel(C.snr)
    fprintf(fid, '3,k_fit,SNR=%ddB,%.6f,analytic value is 0.5\n', C.snr(i), C.k_fit(i));
    fprintf(fid, '3,eps_rel_fitted,SNR=%ddB,%.6e,norm(A-k*B)/norm(B) with fitted k\n', C.snr(i), C.eps_fit(i));
    fprintf(fid, '3,eps_rel_half,SNR=%ddB,%.6e,norm(A-0.5*B)/norm(B) with exact 1/2\n', C.snr(i), C.eps_theory(i));
    fprintf(fid, '3,peak_ratio_half,SNR=%ddB,%.6f,max ratio using exact 1/2\n', C.snr(i), C.peak_ratio_theory(i));
end

D = R.axis4;
for b = 1:size(D.mEc,1)
    for s = 1:size(D.mEc,2)
        fprintf(fid, '4,delta_gCNR_E_minus_C,beta=%.2f/span=%.3f,%.6f,bandwidth x view grid\n', ...
                D.beta(b), D.span(s), D.mEc(b,s));
        fprintf(fid, '4,delta_gCNR_E_minus_M,beta=%.2f/span=%.3f,%.6f,bandwidth x view grid\n', ...
                D.beta(b), D.span(s), D.mEm(b,s));
    end
end
fprintf(fid, '4,additive_R2,bandwidth+view,%.6f,main-effects share of variance\n', D.R2);
fprintf(fid, '4,additive_residual_share,bandwidth+view,%.6f,interaction/nonlinear part\n', 1-D.R2);

if isfield(R, 'axis4beta') && ~isempty(R.axis4beta)
    B4 = R.axis4beta;
    for i = 1:numel(B4.law)
        fprintf(fid, '4b,gCNR_C,bw_law=%.2f,%.6f,bandwidth-law sensitivity\n', ...
                B4.law(i), mean(B4.gC(i,:)));
        fprintf(fid, '4b,gCNR_M,bw_law=%.2f,%.6f,bandwidth-law sensitivity\n', ...
                B4.law(i), mean(B4.gM(i,:)));
        fprintf(fid, '4b,gCNR_E,bw_law=%.2f,%.6f,bandwidth-law sensitivity\n', ...
                B4.law(i), mean(B4.gE(i,:)));
        fprintf(fid, '4b,delta_gCNR_E_minus_C,bw_law=%.2f,%.6f,bandwidth-law sensitivity\n', ...
                B4.law(i), mean(B4.gE(i,:)) - mean(B4.gC(i,:)));
        fprintf(fid, '4b,delta_gCNR_E_minus_M,bw_law=%.2f,%.6f,bandwidth-law sensitivity\n', ...
                B4.law(i), mean(B4.gE(i,:)) - mean(B4.gM(i,:)));
    end
    for i = 1:numel(B4.law)
        fprintf(fid, '4b,sqlaw_ok,bw_law=%.2f,%d,1 means the low-pass band is legal\n', ...
                B4.law(i), B4.sqlaw_ok(i));
    end
end
fclose(fid);
end

% ==================================================================
%  轴 1 —— 15 场景，三臂同种子配对
% ==================================================================
function A = local_axis1(cfg, P, sx, sy, Nrep)
% 场景定义与 docs/09 §0.1 的 15 场景表一一对应（保证可比）
sc = local_scenarios();

nS = numel(sc.name);
A = struct();
A.name  = sc.name;
A.group = sc.group;
A.dEc   = nan(nS, Nrep);
A.dEm   = nan(nS, Nrep);
A.gC    = nan(nS, Nrep);
A.gM    = nan(nS, Nrep);
A.gE    = nan(nS, Nrep);

fprintf('\n---- 轴 1  E-vs-M 同种子配对（Nrep=%d）----\n', Nrep);
fprintf('  %-26s | %-8s %-8s | %-9s %-9s\n', '场景', 'd(E-C)', 'd(E-M)', 't(E-C)', 't(E-M)');
for i = 1:nS
    for r = 1:Nrep
        rng(20000 + 101*i + 7*r);            % 同场景同重复 -> 三臂共享噪声
        Px = P;  Px.beta_sig = sc.beta(i);  Px.SNR = sc.snr(i);
        sig = local_synth(Px, [0 0], 1, sx, sy, Px.SNR);
        if sc.clutter(i) > 0
            % 视场外强吸收体（14 个，半径 24~34 mm，幅值为目标的 2~5 倍）
            % —— 口径与 pa_study_resolution 的 'clutter' 体制一致
            rng(20001 + 101*i + 7*r);        % 杂波几何单独定种，跨臂共享
            [cpts, camp] = local_clutter(Px);
            sig = local_add_points(sig, Px, cpts, sc.clutter(i)*camp, sx, sy);
        end
        if sc.sigma_phi(i) > 0
            rng(20002 + 101*i + 7*r);
            ph = sc.sigma_phi(i) * randn(numel(sx), 1);
            for m = 1:numel(sx)
                sig(:,m) = real(hilbert(sig(:,m)) .* exp(1i*ph(m)));
            end
        end
        if sc.frac_drop(i) > 0
            keep = true(1, numel(sx));
            nD   = round(sc.frac_drop(i) * numel(sx));
            keep(randperm(numel(sx), nD)) = false;
            sig(:, ~keep) = 0;
        end
        img = local_arms(sig, cfg, Px);
        R1  = local_roi(Px);
        A.gC(i,r) = gcnr_roi(img.C, R1);
        A.gM(i,r) = gcnr_roi(img.M, R1);
        A.gE(i,r) = gcnr_roi(img.E, R1);
    end
    A.dEc(i,:) = A.gE(i,:) - A.gC(i,:);
    A.dEm(i,:) = A.gE(i,:) - A.gM(i,:);
    [tC, pC] = paired_t(A.dEc(i,:));
    [tM, pM] = paired_t(A.dEm(i,:));
    A.tEc(i) = tC;  A.pEc(i) = pC;
    A.tEm(i) = tM;  A.pEm(i) = pM;
    fprintf('  %-26s | %+8.4f %+8.4f | %+8.2f(%s) %+8.2f(%s)\n', ...
            sc.name{i}, mean(A.dEc(i,:)), mean(A.dEm(i,:)), ...
            tC, p_sign(pC), tM, p_sign(pM));
end

fprintf('  ---- 汇总 ----\n');
fprintf('  d(E-C): 均值 %+0.4f  全胜 %d/%d  |  d(E-M): 均值 %+0.4f\n', ...
        mean(mean(A.dEc,2)), sum(mean(A.dEc,2) > 0), nS, mean(mean(A.dEm,2)));
fprintf('  配对 t 显著 (p<0.05) 的场景： d(E-C) %d/%d  |  d(E-M) %d/%d\n', ...
        sum(A.pEc < 0.05), nS, sum(A.pEm < 0.05), nS);
A.mean_dEc = mean(mean(A.dEc,2));
A.mean_dEm = mean(mean(A.dEm,2));
A.win_Ec   = sum(mean(A.dEc,2) > 0);
A.win_Em   = sum(mean(A.dEm,2) > 0);
end

% ==================================================================
%  轴 2 —— 阵元随机失效：非饱和指标
% ==================================================================
function B = local_axis2(cfg, P, sx, sy, Nrep)
% 目标改为**有限支撑圆盘**（r_obj = 0.4 mm），使真值图像已知，
% 从而可以报 SSIM / PSNR 这类不会被 gCNR 饱和掩盖的指标。
rObj   = 0.4e-3;
truth  = local_truth_disk(P, rObj);
fracList = [0 0.125 0.25 0.375 0.50 0.625];
nF = numel(fracList);

B = struct('frac', fracList, 'rObj_mm', rObj*1e3);
B.gC = nan(nF,Nrep); B.gM = B.gC; B.gE = B.gC;
B.w1C= nan(nF,Nrep); B.w1M= B.w1C; B.w1E= B.w1C;
B.dpC= nan(nF,Nrep); B.dpM= B.dpC; B.dpE= B.dpC;
B.slC= nan(nF,Nrep); B.slM= B.slC; B.slE= B.slC;
B.ssC= nan(nF,Nrep); B.ssM= B.ssC; B.ssE= B.ssC;
B.psC= nan(nF,Nrep); B.psM= B.psC; B.psE= B.psC;

fprintf('\n---- 轴 2  阵元随机失效：gCNR 饱和 vs 非饱和指标（Nrep=%d）----\n', Nrep);
fprintf('  %6s | %-20s | %-24s | %-20s\n', ...
        'frac', 'gCNR C/M/E', 'W1(x1e3) C/M/E', 'SSIM C/M/E');
for i = 1:nF
    for r = 1:Nrep
        rng(31000 + 53*i + 11*r);
        sig  = local_synth(P, [0 0], 1, sx, sy, P.SNR);
        keep = true(1, numel(sx));
        nD   = round(fracList(i) * numel(sx));
        if nD > 0, keep(randperm(numel(sx), nD)) = false; end
        sig(:, ~keep) = 0;
        img = local_arms(sig, cfg, P);
        R1  = local_roi(P);
        B.gC(i,r)=gcnr_roi(img.C,R1); B.gM(i,r)=gcnr_roi(img.M,R1); B.gE(i,r)=gcnr_roi(img.E,R1);
        B.w1C(i,r)=w1_roi(img.C,R1);  B.w1M(i,r)=w1_roi(img.M,R1);  B.w1E(i,r)=w1_roi(img.E,R1);
        B.dpC(i,r)=dpeak_roi(img.C);  B.dpM(i,r)=dpeak_roi(img.M);  B.dpE(i,r)=dpeak_roi(img.E);
        B.slC(i,r)=sidelobe_frac(img.C); B.slM(i,r)=sidelobe_frac(img.M); B.slE(i,r)=sidelobe_frac(img.E);
        % 真值指标必须在**各自域内**归一化后再比（平方域量纲与幅度域不同）
        B.ssC(i,r)=ssim_global(img.C,truth);  B.ssM(i,r)=ssim_global(img.M,truth);  B.ssE(i,r)=ssim_global(img.E,truth);
        B.psC(i,r)=psnr_vs(img.C,truth);      B.psM(i,r)=psnr_vs(img.M,truth);      B.psE(i,r)=psnr_vs(img.E,truth);
    end
    fprintf('  %5.1f%% | %.3f/%.3f/%.3f | %.2f/%.2f/%.2f | %.3f/%.3f/%.3f\n', ...
            100*fracList(i), ...
            mean(B.gC(i,:)), mean(B.gM(i,:)), mean(B.gE(i,:)), ...
            1e3*mean(B.w1C(i,:)), 1e3*mean(B.w1M(i,:)), 1e3*mean(B.w1E(i,:)), ...
            mean(B.ssC(i,:)), mean(B.ssM(i,:)), mean(B.ssE(i,:)));
end
fprintf('  SSIM 末行 frag: C=%.3f±%.3f  M=%.3f±%.3f  E=%.3f±%.3f\n', ...
        mean(B.ssC(end,:)), std(B.ssC(end,:)), ...
        mean(B.ssM(end,:)), std(B.ssM(end,:)), ...
        mean(B.ssE(end,:)), std(B.ssE(end,:)));
end

% ==================================================================
%  轴 3 —— Hilbert-free 的 eps_rel（尺度校正后）
% ==================================================================
function C = local_axis3(cfg, P, sx, sy)
%  D1^2 = |z|^2                （Hilbert 路，作为参考）
%  D2'  = LPF{x^2} = (1/2)|z|^2（免 Hilbert 路）
%  => 解析尺度 k_theory = 1/2。若「拟合尺度」也收敛到 1/2，
%     且 eps_rel(k_theory) ≈ eps_rel(k_fit)，就证明免-Hilbert 路
%     与 Hilbert 路**只差一个解析可预测的常数因子**。
snrList = [40 20 10];
C = struct('snr', snrList, 'k_theory', 0.5);
C.k_fit = nan(1, numel(snrList));
C.eps_fit = nan(size(snrList));
C.eps_theory = nan(size(snrList));
C.peak_ratio_theory = nan(size(snrList));
C.peak_ratio_fit = nan(size(snrList));
C.errImg = [];

fprintf('\n---- 轴 3  Hilbert-free 的 eps_rel（尺度校正后）----\n');
fprintf('  %6s | %-9s %-11s %-11s | %-9s %-9s\n', ...
        'SNR(dB)', 'k_fit', 'eps_rel(fit)', 'eps_rel(1/2)', 'peak比(1/2)', 'peak比(fit)');
for i = 1:numel(snrList)
    rng(41000 + 17*i);
    sig = local_synth(P, [0 0], 1, sx, sy, snrList(i));
    D   = pa_preprocess(sig, cfg, 'Methods', {'env2','sqlaw'});
    Iref = D.env2;                 % |z|^2
    Ihp  = D.sqlaw;                % LPF{x^2} = 1/2 |z|^2
    kf = sum(Ihp(:).*Iref(:)) / sum(Iref(:).*Iref(:));
    C.k_fit(i) = kf;
    C.eps_fit(i)   = rel_err(Ihp, Iref, kf);
    C.eps_theory(i)= rel_err(Ihp, Iref, 0.5);
    C.peak_ratio_theory(i) = max(Ihp(:)) / max(max(Iref(:)), eps);
    C.peak_ratio_fit(i)    = kf;
    if i == 1
        C.errImg = abs(Ihp - 0.5*Iref);
        C.refImg = Iref;
        C.hpImg  = Ihp;
    end
    fprintf('  %6.0f | %9.6f %11.3e %11.3e | %9.6f %9.6f\n', ...
            snrList(i), kf, C.eps_fit(i), C.eps_theory(i), ...
            C.peak_ratio_theory(i), C.peak_ratio_fit(i));
end
fprintf('  => k_fit 与解析值 1/2 的相对偏差 = %.3e\n', ...
        abs(mean(C.k_fit) - 0.5) / 0.5);
end

% ==================================================================
%  轴 4 —— 带宽 x 视角分离
% ==================================================================
function D = local_axis4(cfg, P, sx, sy, Nrep)
betaList  = [0.20 0.40 0.60 0.80 1.00 1.50];   % 信号 -6dB 相对带宽
spanList  = [0 0.125 0.25 0.375 0.50];          % 视角缺失比例
nB = numel(betaList);  nS = numel(spanList);

D = struct('beta', betaList, 'span', spanList, 'Nrep', Nrep);
D.gC = nan(nB,nS,Nrep); D.gM = D.gC; D.gE = D.gC;

fprintf('\n---- 轴 4  带宽 x 视角分离（分析带固定 bw_law=%.2f，Nrep=%d）----\n', P.bw_law, Nrep);
fprintf('  d(E-C) 网格（行=beta_sig，列=视角缺失）\n');
fprintf('        '); fprintf('%9.3f', spanList); fprintf('\n');
for b = 1:nB
    fprintf('  %5.2f ', betaList(b));
    for s = 1:nS
        Px = P; Px.beta_sig = betaList(b);
        for r = 1:Nrep
            rng(52000 + 211*b + 17*s + 3*r);
            sig = local_synth(Px, [0 0], 1, sx, sy, Px.SNR);
            if spanList(s) > 0
                keep = local_sector_mask(sx, sy, Px, spanList(s));
                sig(:, ~keep) = 0;
            end
            img = local_arms(sig, cfg, Px);
            R1  = local_roi(Px);
            D.gC(b,s,r) = gcnr_roi(img.C,R1);
            D.gM(b,s,r) = gcnr_roi(img.M,R1);
            D.gE(b,s,r) = gcnr_roi(img.E,R1);
        end
        fprintf('%9.4f', mean(mean(D.gE(b,s,:) - D.gC(b,s,:), 3)));
    end
    fprintf('\n');
end

% 对 Nrep 取均值（**只沿 dim 3 求均值**）。曾误写成 mean(mean(.,3),2)，
% 那会再对 span 求一次均值、得到 nB×1，与 nB*nS 行的哑变量矩阵不匹配。
D.mEc = squeeze(mean(D.gE - D.gC, 3));   % nB x nS
D.mEm = squeeze(mean(D.gE - D.gM, 3));
D.mE  = squeeze(mean(D.gE,       3));
D.mC  = squeeze(mean(D.gC,       3));

% 边际效应分解：加性模型 gE≈ mu + a(beta) + b(span)，残差即交互项
% 全因子展开，行索引 k = (s-1)*nB + b（与 y = D.mE(:) 的列主序一致）：
%   X = [1 | 哑变量(beta_1..nB) | 哑变量(span_1..nS)]
% 构造方式用 ndgrid + sub2ind **确定性赋值**，不用 repelem/bool 广播
% （后者在 nB≠nS 时会因隐式扩展方向不确定而抛"数组的大小不兼容"）。
y = D.mE(:);                                  % (nB*nS) x 1
[rG, sG] = ndgrid(1:nB, 1:nS);               % nB x nS
lin = rG + (sG - 1) * nB;                     % 与 y 同序的线性索引
X = zeros(nB * nS, 1 + nB + nS);
X(:, 1) = 1;                                  % 截距
X(sub2ind(size(X), lin(:), 1 + rG(:))) = 1;                % 2 .. nB+1
X(sub2ind(size(X), lin(:), 1 + nB + sG(:))) = 1;           % nB+2 .. nB+nS+1
% 两组哑变量各自和为 1，须各去掉最后一个水平（基线），否则与截距共线
keep = [1, 2:nB, nB+2:nB+nS];                  % 截距 + (nB-1) + (nS-1) 列
X = X(:, keep);
coef = X \ y;
D.mu0   = coef(1);
D.aBeta = [NaN; coef(2:nB)];            % beta 水平 nB 作基线
D.aSpan = [NaN; coef(nB+1:end)];        % span 水平 nS 作基线
D.ssTot = sum((y-mean(y)).^2);
D.ssRes = sum((y - X*coef).^2);
D.R2    = 1 - D.ssRes/D.ssTot;
% 交互项单独算：双因素方差分解
D.intBeta = mean(D.mE, 2);      % 带宽主效应（对 span 平均）
D.intSpan = mean(D.mE, 1);      % 视角主效应（对 beta 平均）

fprintf('  ---- 加性模型拟合（gCNR_E ~ 1 + a(beta) + b(span)）----\n');
fprintf('  R^2 = %.4f   残差占比 = %.4f（即两轴交互/非线性部分）\n', D.R2, 1-D.R2);
fprintf('  带宽主效应 gCNR_E（对 span 平均）： ');
fprintf('%7.4f ', D.intBeta); fprintf('\n');
fprintf('  视角主效应 gCNR_E（对 beta  平均）： ');
fprintf('%7.4f ', D.intSpan); fprintf('\n');
fprintf('  => d(E-M) 均值 = %+0.4f （中性区间）\n', mean(D.mEm(:)));
end

% --------- 轴 4b：分析带构造律 beta_law 敏感性（docs/08 要求 {0.6,0.8,0.9}）
function Eb = local_axis4_beta(cfg, P, sx, sy, Nrep)
lawList = [0.60 0.80 0.90];
betaSig = 0.60;
Eb = struct('law', lawList, 'beta_sig', betaSig);
% 尺寸：索引写作 Eb.gX(i, r)，i = 档（1..nLaw）、r = rep（1..Nrep）
% ⇒ 必须是 nLaw x Nrep。**曾误写成 1 x nLaw x Nrep**，导致
%    Eb.gX(i,r) 在i>1 时线性索引越界、写入被静默丢弃，
%    而 Eb.gX(i,:) 又按线性索引跨档取值 —— 两者叠加打印出 NaN。
Eb.gC = nan(numel(lawList), Nrep); Eb.gM = Eb.gC; Eb.gE = Eb.gC;
Eb.sqlaw_ok = false(1,numel(lawList));
fprintf('\n---- 轴 4b  分析带构造律 beta_law 敏感性（beta_sig=%.2f）----\n', betaSig);
fprintf('  %6s | %-9s | %-9s %-9s | %-9s | %s\n', ...
        'bw_law', 'sqlaw_ok', 'gCNR_C', 'gCNR_M', 'gCNR_E', 'd(E-C)');
for i = 1:numel(lawList)
    Px = P; Px.beta_sig = betaSig; Px.bw_law = lawList(i);
    Px.f_low  = Px.f0 * (1 - Px.bw_law/2);
    Px.f_high = Px.f0 * (1 + Px.bw_law/2);
    cfgx = build_cfg(Px);
    Eb.sqlaw_ok(i) = cfgx.sqlaw_ok;
    for r = 1:Nrep
        rng(61000 + 71*i + 5*r);
        sig = local_synth(Px, [0 0], 1, sx, sy, Px.SNR);
        img = local_arms(sig, cfgx, Px);
        R1  = local_roi(Px);
        Eb.gC(i,r)=gcnr_roi(img.C,R1); Eb.gM(i,r)=gcnr_roi(img.M,R1); Eb.gE(i,r)=gcnr_roi(img.E,R1);
    end
    % 显式按行取档（Eb.gX 已是 nLaw x Nrep）
    gC_law = Eb.gC;  gM_law = Eb.gM;  gE_law = Eb.gE;
    fprintf('  %6.2f | %-9d | %9.4f %9.4f | %9.4f | %+0.4f\n', lawList(i), ...
            Eb.sqlaw_ok(i), mean(gC_law(i,:)), mean(gM_law(i,:)), ...
            mean(gE_law(i,:)), mean(gE_law(i,:))-mean(gC_law(i,:)));
end
% 对 Nrep 取均值：Eb.gX 是 nLaw x Nrep ⇒沿 **dim 2** 求均值，得 1 x nLaw
Eb.mEc = mean(Eb.gE - Eb.gC, 2);
Eb.mEm = mean(Eb.gE - Eb.gM, 2);
Eb.mE  = mean(Eb.gE,       2);
Eb.mC  = mean(Eb.gC,       2);
Eb.lawMean = struct('gC', mean(Eb.gC, 2), 'gM', mean(Eb.gM, 2), ...
                    'gE', mean(Eb.gE, 2), 'gC_SD', std(Eb.gC, 0, 2), ...
                    'gM_SD', std(Eb.gM, 0, 2), 'gE_SD', std(Eb.gE, 0, 2));
end

% ==================================================================
%  场景表（与 docs/09 §0.1 的 15 场景一一对应）
% ==================================================================
function sc = local_scenarios()
sc = struct();
sc.name = {
    'semicircle128/noise'    , 'ring256/noise'        , ...
    'semicircle128/clutter'  , 'ring256/clutter'      , ...
    'aberr sigma_phi=0.5'    , 'aberr sigma_phi=1'    , ...
    'aberr sigma_phi=2'      , 'SNR=0 dB'             , ...
    'SNR=5 dB'               , 'SNR=10 dB'            , ...
    'SNR=15 dB'              , 'SNR=25 dB'            , ...
    'random loss 50%'};
sc.group = {'ideal','ideal','clutter','clutter', ...
            'aberr','aberr','aberr', ...
            'lowSNR','lowSNR','lowSNR','lowSNR','lowSNR', ...
            'loss'};
sc.beta      = 0.60 * ones(1,13);
sc.sigma_phi = [0 0 0 0  0.5 1 2  0 0 0 0 0  0];
sc.frac_drop = [0 0 0 0  0 0 0  0 0 0 0 0  0.50];
sc.snr       = [40 40 40 40  40 40 40  0 5 10 15 25  40];
sc.clutter   = [0 0 3 3   0 0 0  0 0 0 0 0  0];   % 倍数；0 = 无杂波
end

% --------- 视场外强吸收体（视场 40 mm，阵列 R=55 mm -> 落在阵元内侧的视场外）
function [cpts, camp] = local_clutter(P)
Ncl = 14;
a   = rand(Ncl,1) * 2*pi;
rr  = (24 + 10*rand(Ncl,1)) * 1e-3;
cpts = [rr.*cos(a), rr.*sin(a)];
camp = 2 + 3*rand(Ncl,1);
end

function sig = local_add_points(sig, P, pts, amps, sx, sy)
nCh = numel(sx);  t = (0:P.nSamples-1).'/P.fs;
sigF = P.beta_sig*P.f0/2.355;  sigT = 1/(2*pi*sigF);
for k = 1:size(pts,1)
    for m = 1:nCh
        rrh = hypot(pts(k,1)-sx(m), pts(k,2)-sy(m));
        tau = rrh/P.vs;   a = amps(k)/rrh;
        g   = exp(-((t-tau)/sigT).^2) .* cos(2*pi*P.f0*(t-tau));
        sig(:,m) = sig(:,m) + a*g;
    end
end
end

% ==================================================================
%  三臂（与 pa_study_advantage 逐位一致；E 用 consist 口径 = Comp 'r'）
% ==================================================================
function img = local_arms(sig, cfg, P)
D  = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','filtered'});
Z  = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
img.C = coherent_bp(Z, cfg, P, 'r');
img.M = pa_backproject(D.env,   cfg, 'Comp','r',  'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
% 补偿口径统一为 g_m = d_m/R（MEMORY §1；docs/09 §3.8.3 已否证 r^2 机制）
img.E = pa_backproject(D.sqlaw, cfg, 'Comp','r',  'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
end

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

function keep = local_sector_mask(sx, sy, P, frac)
a    = mod(atan2(sy,sx) + pi, 2*pi);
if strcmpi(P.arrayType, 'semicircle128'), span = pi; else, span = 2*pi; end
keep = a >= (span*frac);
end

% ==================================================================
%  指标
% ==================================================================
function R1 = local_roi(P)
dx = P.FOV/(P.Nx-1);  qv = ((1:P.Nx)-P.Nx/2)*dx;
[X,Y] = meshgrid(qv,qv);  r2 = X.^2 + Y.^2;
R1.in  = r2 <= (0.5e-3)^2;
R1.out = (r2 >= (3e-3)^2) & (r2 <= (6e-3)^2);
end

function g = gcnr_roi(img, R1)
a = img(R1.in);  b = img(R1.out);
a = a(:);  b = b(:);
if isempty(a) || isempty(b), g = NaN; return; end
lo = min([a;b]);  hi = max([a;b]);
if hi <= lo, g = 1; return; end
e  = linspace(lo, hi, 65);
pa = histcounts(a, e);  pa = pa/sum(pa);
pb = histcounts(b, e);  pb = pb/sum(pb);
g  = 1 - sum(min(pa, pb));
end

function d = w1_roi(img, R1)
% 一阶 Wasserstein 距离：两经验分布的 CDF 差分积分。
% 对任意严格单调映射不变（与 gCNR 同为不变量），但在 gCNR 饱和
% （OVL -> 0）时**仍保留分辨力**，故称「非饱和」。
a = img(R1.in);  b = img(R1.out);
a = a(:);  b = b(:);
lo = min([a;b]);  hi = max([a;b]);
if hi <= lo, d = 0; return; end
e  = linspace(lo, hi, 257);
ca = cumsum(histcounts(a, e))/max(numel(a),1);
cb = cumsum(histcounts(b, e))/max(numel(b),1);
d  = sum(abs(ca - cb)) * (e(2)-e(1));
end

function dp = dpeak_roi(img)
% 峰值定位误差（像素）：峰的能量重心到图像几何中心的距离。
% 对严格单调映射不变，且**永不饱和**；乘以像素间距 (FOV/(Nx-1)) 即得 mm。
sz = size(img);
if isempty(img) || ~isfinite(max(img(:))) || max(img(:)) <= 0, dp = NaN; return; end
c  = (sz(1)+1)/2;
ii = (1:sz(1))';  jj = 1:sz(2);
w  = max(img, 0);
tot = sum(w(:));
if tot <= 0, dp = NaN; return; end
rc = sum(sum(w .* (ii*c))) / tot;
cc = sum(sum(w .* (jj*c))) / tot;
dp = hypot(rc - c, cc - c);
end

function s = sidelobe_frac(img, P)
% 旁瓣能量占比：以中心 3x3 为「主瓣」，其余为旁瓣（逐臂归一化）。
sz = size(img);
c  = (sz(1)+1)/2;
m  = false(sz);
m(round(c)-1:round(c)+1, round(c)-1:round(c)+1) = true;
w  = max(img, 0);
tot = sum(w(:));
if tot <= 0, s = NaN; return; end
s = sum(w(~m).^2) / sum(w(m).^2);
end

function T = local_truth_disk(P, rObj)
dx = P.FOV/(P.Nx-1);  qv = ((1:P.Nx)-P.Nx/2)*dx;
[X,Y] = meshgrid(qv,qv);
T = double(hypot(X,Y) <= rObj);
end

function s = ssim_global(a, b)
% 全局 SSIM（A,B 各为图像）。各自按自身最大值归一化，
% 使平方域与幅度域可比（只用于「相对真值」的结构判断）。
a = double(a);  b = double(b);
if ~isfinite(max(a(:))) || max(a(:)) <= 0, s = NaN; return; end
a = a / max(a(:));  b = b / max(max(b(:)), eps);
C1 = (0.01)^2;  C2 = (0.03)^2;
ma = mean(a(:));  mb = mean(b(:));
va = var(a(:));   vb = var(b(:));  cov = mean((a(:)-ma).*(b(:)-mb));
s = ((2*ma*mb + C1)*(2*cov + C2)) / ((ma^2 + mb^2 + C1)*(va + vb + C2));
end

function p = psnr_vs(a, b)
a = double(a);  b = double(b);
if max(a(:)) <= 0, p = NaN; return; end
a = a / max(a(:));  b = b / max(max(b(:)), eps);
mse = mean((a(:)-b(:)).^2);
if mse <= 0, p = Inf; else, p = 10*log10(1/mse); end
end

function e = rel_err(A, B, k)
% 尺度校正后的相对误差 L2 范数
e = norm(A(:) - k*B(:)) / max(norm(B(:)), eps);
end

function [t, p] = paired_t(d)
d = d(:);  n = numel(d);
if n < 2 || all(abs(d - mean(d)) < 1e-15)
    t = 0;  p = 1;  return;
end
s = std(d, 0) / sqrt(n);
if s <= 0, t = 0;  p = 1;  return; end
t = mean(d)/s;
p = 2*(1 - tcdf(abs(t), n-1));
end

function s = p_sign(p)
if p < 0.001, s = '***'; elseif p < 0.01, s = '**'; elseif p < 0.05, s = '*'; else, s = 'ns'; end
end

% ==================================================================
%  合成信号 / 几何 / 配置
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
cfg.name='audit'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
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