function R = pa_study_speckle(varargin)
%PA_STUDY_SPECKLE  Fig. S3：散斑统计（预言 P2），外部评审「数据类」整改项 ⑥
%
%   问题
%     P2「能量域图像的散斑起伏更小」一直未实测；且原文 CV(I_E)=1/sqrt(M)
%     只在「等强度 i.i.d. 复高斯」下成立，带几何补偿时权重并不相等。
%
%   设计（先诊断，再验证，最后定性）
%     A. 前提检验（单像素、通道级）
%        对 a_m = g_m z_m(tau_m) 逐通道统计：
%          - CV_inst = std(|a|^2)/mean(|a|^2)        等强度程度
%          - R_circ  = |mean(exp(i*phi_m))|          圆方差，0=相位均匀 1=全同相
%          - 相位直方图的均匀性（Kuiper 统计量）
%        => 先回答「i.i.d. 复高斯前提在本几何下成立到什么程度」。
%
%     B. 闭合式的**系综**验证（单像素 x Nens 独立实现）
%        理论说的是 a_m 在 M 个通道上的分布，故正确做法是
%        **固定一个像素、重复整幅实验 Nens 次**（每次散射体独立重抽），
%        再对系综求 CV。空间 ROI 上的 CV **不能**检验这条闭式（见 C）。
%        报 CV_ens(I_E) vs 1/sqrt(M)、CV_ens(I_BS) vs 1。
%
%     C. 空间斑图（定性 + 去相关长度）
%        实测散斑**去相关长度**：沿径向取剖面，算归一化自相关，
%        报 1/e 宽度；与理论 lambda*R/D 比较。
%        诚实结论写进图注：若去相关长度 >> ROI 尺寸，则 ROI 内的
%        std/mean 量到的是**包络调制**（相干旁瓣）而非散斑分布，
%        此时 P2 的闭式**不适用**于空间 ROI；空间可测的、
%        不依赖前提的陈述是「同一散斑实现内，能量域的局部包络更平滑」。
%
%     D. 归因诊断（v3 新增；**v4 按 v0.21 裁定改写结论**）
%        Part B 实测 CV(I_E)=0.1116 高于闭式 1/sqrt(M)=0.0884。**不调数字、不改理论**，
%        只把「偏差从哪来」的可检验环节摆出来：
%          D1 合成对照：按闭式的随机模型直接生成 i.i.d. 等强度复高斯 a_m（不过传播链）。
%             若命中 1/sqrt(M) 与 1，则闭式与实现无误，偏差必来自「传播实现」而非理论/代码。
%          D2 矩匹配描述：N_eff = M*(theo/CV_meas)^2 只是把一个实测 CV **改写**成一个等效通道数，
%             是**描述**、不是独立性证据。⚠️ **`I_BS` 不给 N_eff**：相干和的模平方基准是
%             Gamma(1)（指数分布，形状参数 1），**不是** M；把 `1/CV^2` 当通道数没有模型依据。
%             （v0.21 已把旧稿的 `N_eff(I_BS)=62.5/128` 撤回，此处同步删除该输出。）
%          D3 几何 vs 白噪声：同一几何权重下，把真实传播结果与「每通道独立白噪声」并列。
%             两者之差说明**权重结构与通道间耦合确实在起作用**，但它**不足以**把差量归给任何单一机制。
%        => ★ **结论形态（v0.21 定稿）**：闭式在**独立随机模型**下成立（Part D1 自洽）；
%           真实几何下的超出量**指示**对「平稳、零均值、正规复高斯」模型的偏离，
%           但**成因未定（unresolved）**。候选机制至少四条：非高斯性 / 非正规性（伪协方差非零）/
%           realization 间方差混合 / 有限系综与估计偏差。判别它们需要基于 R̂ 的有限样本区间
%           分析（实验包 **E8**，**本轮未做**）。⚠️ 特别地，在正规复高斯下 `CV(I_BS) ≡ 1`
%           **与 R 是否对角无关**，故「通道独立性失效」**不是** CV(I_BS)>1 的有效解释。
%
%   输出：results/study_speckle/speckle.mat（含图，供 Python 出 Fig. S2）
%         results/study_speckle/speckle.csv
%
%   版本：v4  2026-10-16（同步 v0.21 裁定：删「共享波前 ⇒ 相位非独立 ⇒ N_eff」因果链与
%                        `N_eff(I_BS)` 输出；归因改标 unresolved，指向 E8）

opt.Array   = 'semicircle128';
opt.Nx      = 601;
opt.FOV     = 40e-3;
opt.Nens    = 120;     % 系综样本数（Part B）；CV 的相对标准误 ~ 1/sqrt(2*Nens)
opt.Nscat   = 400;     % 散斑区内的散射体个数
opt.roiR    = 4e-3;    % 空间斑图 ROI 半径
opt.Save    = true;
opt.OutDir  = '';
opt = parse_opts(opt, varargin{:});

if isempty(opt.OutDir)
    pipeRoot   = fileparts(fileparts(mfilename('fullpath')));
    opt.OutDir = fullfile(fileparts(pipeRoot), 'results', 'study_speckle');
end

P = struct();
P.fs = 40e6;  P.nSamples = 4096;  P.vs = 1478;  P.f0 = 5e6;
P.beta_sig = 0.60;  P.bw_law = 0.80;
P.R = 55e-3;  P.FOV = opt.FOV;  P.Nx = opt.Nx;  P.SNR = 60;
switch lower(opt.Array)
    case 'semicircle128', P.arrayType = 'semicircle128'; P.N = 128;
    case 'ring256',       P.arrayType = 'ring1024';      P.N = 256;
    otherwise, error('pa_study_speckle:array', '未知阵列：%s', opt.Array);
end
P.f_low  = P.f0 * (1 - P.bw_law/2);
P.f_high = P.f0 * (1 + P.bw_law/2);
cfg = build_cfg(P);
[sx,sy] = sensor_positions(P);
M    = numel(sx);
fprintf('\n==== pa_study_speckle : %s | Nx=%d | M=%d | Nens=%d | Nscat=%d ====\n', ...
        opt.Array, opt.Nx, M, opt.Nens, opt.Nscat);
fprintf('  理论 lambda = %.1f mm ; 孔径 D = %.1f mm ; lambda*R/D = %.1f mm\n', ...
        P.vs/P.f0*1e3, 2*P.R*1e3, (P.vs/P.f0)*(P.R)/(2*P.R)*1e3);

dx = P.FOV/(P.Nx-1);  qv = ((1:P.Nx)-P.Nx/2)*dx;
[X,Y] = meshgrid(qv,qv);
mask = hypot(X,Y) <= opt.roiR;

% 理论线
g0    = local_g_at(0,0,sx,sy,P);
theo_eq = 1/sqrt(M);
theo_w  = sqrt(sum(g0.^4)) / sum(g0.^2);
fprintf('  理论 CV(I_E)：等权 1/sqrt(M)=%.4f ；带权 sqrt(Sg4)/Sg2=%.4f （差 %.2f%%）\n', ...
        theo_eq, theo_w, 100*(theo_w-theo_eq)/theo_eq);

% ==================================================================
%  Part A：前提检验（通道级，单像素）
% ==================================================================
fprintf('\n---- Part A  前提检验：a_m = g_m z_m(tau_m) 的通道级统计 ----\n');
fprintf('  %8s | %-10s | %-10s | %s\n', 'r(mm)', 'CV_inst', 'R_circ', 'Kuiper');
A = struct('r_mm',[0 1 2 3],'cv_inst',nan(1,4),'r_circ',nan(1,4),'kuiper',nan(1,4));
for i = 1:numel(A.r_mm)
    [cv, rc, ku] = local_premise(P, cfg, sx, sy, A.r_mm(i)*1e-3, opt.Nscat);
    A.cv_inst(i) = cv;  A.r_circ(i) = rc;  A.kuiper(i) = ku;
    fprintf('  %8.1f | %10.4f | %10.4f | %.4f\n', A.r_mm(i), cv, rc, ku);
end
fprintf('  => R_circ 接近 0 表示通道间相位近似均匀（i.i.d. 前提的核心）\n');
fprintf('  => CV_inst 接近 1 表示 |a_m|^2 近似等强度指数型（复高斯的必然结果）\n');
fprintf('  => Kuiper V 在 64 bins 下均匀零假设的期望约 0.016\n');

% ==================================================================
%  Part B：闭合式的系综验证（单像素 x Nens）
% ==================================================================
fprintf('\n---- Part B  系综验证（中心像素，Nens=%d 次独立实现）----\n', opt.Nens);
Ie = nan(1,opt.Nens);  Ibs = nan(1,opt.Nens);  Im = nan(1,opt.Nens);
for k = 1:opt.Nens
    rng(77000 + 13*k);
    [Ie(k), Im(k), Ibs(k)] = local_one_ens(P, cfg, sx, sy, opt.Nscat);
end
cvE_ens = std(Ie)/mean(Ie);
cvBS_ens= std(Ibs)/mean(Ibs);
cvM_ens = std(Im)/mean(Im);
B = struct('Ie',Ie,'Im',Im,'Ibs',Ibs,'Nens',opt.Nens, ...
           'cvE',cvE_ens,'cvM',cvM_ens,'cvBS',cvBS_ens, ...
           'theo_eq',theo_eq,'theo_w',theo_w, ...
           'ratio_E',cvE_ens/theo_eq,'ratio_BS',cvBS_ens);
fprintf('  CV_ens(I_E)  = %.4f   理论 1/sqrt(M)=%.4f (带权 %.4f)  比值 %.3f\n', ...
        cvE_ens, theo_eq, theo_w, B.ratio_E);
fprintf('  CV_ens(I_BS) = %.4f   理论 1.0000                    比值 %.3f\n', ...
        cvBS_ens, B.ratio_BS);
fprintf('  CV_ens(I_M)  = %.4f （参照，不参与 P2）\n', cvM_ens);
sem = 1/sqrt(2*opt.Nens);
fprintf('  估计量的相对标准误 ~ 1/sqrt(2*Nens) = %.3f => 95%% 区间约 ±%.3f（相对）\n', ...
        sem, 1.96*sem);
fprintf('  => 实测/理论 = %.3f ± %.3f (I_E) ; %.3f ± %.3f (I_BS)\n', ...
        cvE_ens/theo_eq, 1.96*sem*cvE_ens/theo_eq, cvBS_ens, 1.96*sem*cvBS_ens);

% ==================================================================
%  Part C：空间斑图 + 去相关长度 + 包络 CV
% ==================================================================
fprintf('\n---- Part C  空间斑图（定性）+ 去相关长度 ----\n');
rng(77001);
pts = local_scat_pts(opt.Nscat, opt.roiR);
sig = local_synth(P, pts, ones(opt.Nscat,1), sx, sy, P.SNR);
D   = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','filtered'});
Z   = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
IE  = pa_backproject(D.sqlaw, cfg, 'Comp','r2','Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IM  = pa_backproject(D.env,   cfg, 'Comp','r', 'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IC  = coherent_bp(Z, cfg, P, 'r');
IBS = IC.^2;

% 沿 +x 方向的剖面自相关 -> 去相关长度（1/e 宽度）
% 必须先去趋势：PSF 包络在 40 mm 视场上衰减很慢，直接相关会量到包络。
j0 = (P.Nx+1)/2;
profE = IE(j0, :);  profB = IBS(j0, :);
lagE  = local_decorr(profE, dx) * 1e3;      % mm
lagB  = local_decorr(profB, dx) * 1e3;
lamR_D = (P.vs/P.f0) * (P.R/(2*P.R)) * 1e3; % lambda*R/D, D=2R -> lambda/2
fprintf('  实测去相关长度(1/e)： I_E = %.2f mm ； I_BS = %.2f mm\n', lagE, lagB);
fprintf('  参考 lambda/2 = %.2f mm （D=2R 时的 lambda*R/D）\n', lamR_D);
fprintf('  ROI 直径 = %.1f mm  => ROI 内 CV 能否检验闭式：%s\n', 2*opt.roiR*1e3, ...
        local_yn(lagB > 2*opt.roiR*1e3));

% 分环包络 CV（说明「ROI 内 CV 量到的是包络，不是分布」）
edges = [0 0.5 1 1.5 2 3 4];
Rrad  = hypot(X,Y)*1e3;
ring = struct('edges',edges,'cvE',nan(1,numel(edges)-1),'cvB',nan(1,numel(edges)-1), ...
              'cvM',nan(1,numel(edges)-1),'meanE',nan(1,numel(edges)-1),'meanB',nan(1,numel(edges)-1));
fprintf('  %-12s %7s | %-16s | %-16s\n', 'ring(mm)', 'nPix', 'CV_E (env.)', 'CV_BS (env.)');
for i = 1:numel(edges)-1
    m = mask & Rrad >= edges(i) & Rrad < edges(i+1);
    ring.cvE(i) = cv_roi(IE, m);  ring.cvB(i) = cv_roi(IBS, m);  ring.cvM(i) = cv_roi(IM, m);
    ring.meanE(i) = mean(IE(m));  ring.meanB(i) = mean(IBS(m));
    fprintf('  %4.1f-%4.1f %7d | %7.4f         | %7.4f\n', ...
            edges(i), edges(i+1), sum(m(:)), ring.cvE(i), ring.cvB(i));
end
fprintf('  => E 的 ROI 内包络 CV 远低于 BS，即同一散斑实现内能量域更平滑；\n');
fprintf('     但这不是 P2 闭式的检验（前提见 Part A，去相关长度见上）。\n');

% ==================================================================
%  Part D：为什么实测 CV 高于闭式？——归因，不是解释掉差异
% ==================================================================
fprintf('\n---- Part D  归因诊断：CV 超出闭式的来源 ----\n');
D4 = struct();

% D1. **理论自洽性对照**：直接按闭式的随机模型生成 a_m（i.i.d. 复高斯、等强度），
%     不经过传播/几何/插值。若此处 CV 命中1/sqrt(M) 与 1，说明闭式与实现无误，
%     Part B 的偏差只能来自「传播实现」而非「理论或代码」。
rng(99001);
Nn = 4000;  a = zeros(M, Nn);
for k = 1:Nn
    a(:,k) = (randn(M,1) + 1i*randn(M,1))/sqrt(2);   % CN(0,1)，等强度 i.i.d.
end
IeD  = sum(abs(a).^2, 1);
IbsD = abs(sum(a,1)).^2;
D4.cvE_syn  = std(IeD)/mean(IeD);
D4.cvBS_syn = std(IbsD)/mean(IbsD);
fprintf('  D1 合成 i.i.d. 对照： CV(I_E)=%.4f (闭式 %.4f，比值 %.3f) | CV(I_BS)=%.4f (闭式 1，比值 %.3f)\n', ...
        D4.cvE_syn, theo_eq, D4.cvE_syn/theo_eq, D4.cvBS_syn, D4.cvBS_syn);

% D2. **矩匹配描述**：把实测 CV 改写成一个等效独立通道数 N_eff = (theo/实测)^2 * M。
%     这是**描述性**换算，不是独立性证据，也不构成本项目的任何因果主张。
%     ⚠️ 只对 I_E 给出：I_BS 的闭式基准是 Gamma(1)（指数），**不是 M**，故 I_BS 不定义 N_eff。
D4.Neff_E  = M * (theo_eq/cvE_ens)^2;
fprintf('  D2 矩匹配描述（I_E，仅描述性）： N_eff(I_E)=%.1f / M=%d (%.2f)\n', ...
        D4.Neff_E, M, D4.Neff_E/M);
fprintf('     (I_BS 不定义 N_eff：其闭式基准为 Gamma(1)，不是 M；旧稿的 62.5/128 已撤回)\n');

% D3. **相干性来源分解**：把中心像素的a_m 按「共享的入射波前」重抽，
%     对比两种极限——(a) 真实几何实现；(b) 每次实现给每个通道**独立**的白噪声 a_m。
%     两者之比即「几何相干使有效自由度下降」的纯效应。
Ie_geo = Ie;  Ibs_geo = Ibs;
rng(99002);
gv = local_g_at(0, 0, sx, sy, P);
gv = gv(:);                       % 强制列向量，避免 gv.*aa 变成 M x M 外积
Ie_ind = nan(1,opt.Nens);  Ibs_ind = nan(1,opt.Nens);
for k = 1:opt.Nens
    aa = (randn(M,1) + 1i*randn(M,1))/sqrt(2);
    Ie_ind(k)  = sum(abs(gv.*aa).^2);
    Ibs_ind(k) = abs(sum(gv.*aa))^2;
end
D4.cvE_geo  = cvE_ens;   D4.cvBS_geo  = cvBS_ens;
D4.cvE_ind  = std(Ie_ind)/mean(Ie_ind);
D4.cvBS_ind = std(Ibs_ind)/mean(Ibs_ind);
D4.Neff_E_geo = D4.Neff_E;  D4.Neff_E_ind = M*(theo_eq/D4.cvE_ind)^2;
fprintf('  D3 几何 vs 白噪声： CV(I_E) %.4f -> %.4f ; CV(I_BS) %.4f -> %.4f\n', ...
        D4.cvE_geo, D4.cvE_ind, D4.cvBS_geo, D4.cvBS_ind);
fprintf('     => 结论（v0.21 定稿）：闭式在**独立随机模型**下成立（见 D1）；\n');
fprintf('        真实几何下的超出量**指示**对「平稳、零均值、正规复高斯」模型的偏离，\n');
fprintf('        但**成因未定（unresolved）**，不归给「通道独立性失效」。\n');
fprintf('        候选机制：非高斯性 / 非正规性 / realization 间方差混合 / 有限系综偏差 —— 需 E8 判别（未做）。\n');

R = struct('P',P,'cfg',cfg,'opt',opt,'mask',mask, ...
           'M_channels',M,'lam',P.vs/P.f0, ...
           'theo_eq',theo_eq,'theo_w',theo_w, ...
           'premise',A,'ensemble',B,'ring',ring,'attrib',D4, ...
           'lagE_mm',lagE,'lagB_mm',lagB,'lamR_D_mm',lamR_D, ...
           'roiImg',struct('E',IE,'M',IM,'BS',IBS,'IC',IC), ...
           'profE',profE,'profB',profB,'ax_mm',qv*1e3);

if opt.Save
    if ~exist(opt.OutDir, 'dir'), mkdir(opt.OutDir); end
    save(fullfile(opt.OutDir, 'speckle.mat'), '-struct', 'R', '-v7.3');
    fid = fopen(fullfile(opt.OutDir, 'speckle.csv'), 'w');
    fprintf(fid, 'part,quantity,value,theory,note\n');
    fprintf(fid, 'A,CV_inst_at_r0,%.6f,%.6f,std(|a|^2)/mean(|a|^2); theory=1 for complex Gaussian\n', A.cv_inst(1), 1.0);
    fprintf(fid, 'A,R_circ_at_r0,%.6f,0,mean resultant length (0=uniform phase)\n', A.r_circ(1));
    fprintf(fid, 'B,CV_ensemble_I_E,%.6f,%.6f,ensemble over Nens independent realisations\n', cvE_ens, theo_eq);
    fprintf(fid, 'B,CV_ensemble_I_BS,%.6f,1.000000,ensemble over Nens independent realisations\n', cvBS_ens);
    fprintf(fid, 'B,CV_ensemble_I_M,%.6f,,reference only\n', cvM_ens);
    fprintf(fid, 'D,CV_I_E_synthetic_iid,%.6f,%.6f,closure self-consistency under the stated random model\n', D4.cvE_syn, theo_eq);
    fprintf(fid, 'D,CV_I_BS_synthetic_iid,%.6f,1.000000,closure self-consistency under the stated random model\n', D4.cvBS_syn);
    fprintf(fid, 'D,Neff_I_E_geometry,%.3f,%d,moment-matching description only; NOT an independence proof\n', D4.Neff_E, M);
    fprintf(fid, 'D,CV_I_E_white_noise,%.6f,%.6f,same geometry weights but independent per-channel phases\n', D4.cvE_ind, theo_eq);
    fprintf(fid, 'C,decorrelation_len_E_mm,%.4f,,1/e width of autocorrelation along x\n', lagE);
    fprintf(fid, 'C,decorrelation_len_BS_mm,%.4f,,1/e width of autocorrelation along x\n', lagB);
    fprintf(fid, 'C,lambda_over_2_mm,%.4f,,reference lambda*R/D with D=2R\n', lamR_D);
    fprintf(fid, 'C,envelope_CV_E_roi0_2mm,%.6f,,local envelope modulation inside the ROI\n', ring.cvE(3));
    fprintf(fid, 'C,envelope_CV_BS_roi0_2mm,%.6f,,local envelope modulation inside the ROI\n', ring.cvB(3));
    fclose(fid);
    fprintf('\n  [out] %s\n', opt.OutDir);
end
end

% ==================================================================
function [cv_inst, r_circ, kuiper] = local_premise(P, cfg, sx, sy, r0, Nscat)
rng(81000 + round(1e5*r0));
pts = local_scat_pts(Nscat, max(r0*1.5, 2e-3));
sig = local_synth(P, pts, ones(Nscat,1), sx, sy, P.SNR);
D   = pa_preprocess(sig, cfg, 'Methods', {'filtered'});
Z   = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
g   = local_g_at(r0, 0, sx, sy, P);
tau = hypot(sx - r0, sy) / cfg.vs * cfg.fs + 1;
nS  = size(Z,1);
a   = zeros(numel(sx),1);
for m = 1:numel(sx)
    v = interp1(1:nS, Z(:,m), tau(m), 'linear', 0);
    a(m) = g(m) * v;
end
p2   = abs(a).^2;
cv_inst = std(p2) / max(mean(p2), eps);
phi     = angle(a);
r_circ  = abs(mean(exp(1i*phi)));
% Kuiper 统计量：相位均匀性的分布检验
e  = linspace(-pi, pi, 65);
h  = histcounts(phi, e);  h = h/sum(h);
u  = 1/numel(e);
d  = cumsum(h - u);
kuiper = max(d) - min(d);        % Kuiper V：均匀零假设下 O(1/n)~0.016
end

function [Ie, Im, Ibs] = local_one_ens(P, cfg, sx, sy, Nscat)
pts = local_scat_pts(Nscat, 4e-3);
sig = local_synth(P, pts, ones(Nscat,1), sx, sy, P.SNR);
D   = pa_preprocess(sig, cfg, 'Methods', {'env','sqlaw','filtered'});
Z   = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2), Z(:,ch) = hilbert(D.filtered(:,ch)); end
Ie  = pa_backproject(D.sqlaw, cfg, 'Comp','r2','Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
Im  = pa_backproject(D.env,   cfg, 'Comp','r',  'Nx',P.Nx,'FOV',P.FOV,'Normalize','none');
IC  = coherent_bp(Z, cfg, P, 'r');
c   = (P.Nx+1)/2;
Ie  = Ie(c,c);  Im = Im(c,c);  Ibs = IC(c,c)^2;
end

function pts = local_scat_pts(Nscat, R)
a  = rand(Nscat,1)*2*pi;
rr = R * sqrt(rand(Nscat,1));
pts = [rr.*cos(a), rr.*sin(a)];
end

function L = local_decorr(prof, dx)
% 散斑去相关长度：先去趋势（减去移动平均，窗宽远大于散斑、远小于包络），
% 再取归一化自相关首次过 1/e 处的滞后。
w = max(3, round(3e-3/dx));              % 3 mm 窗
prof = prof(:) - movmean(prof(:), w);
n    = numel(prof);
if n < 8 || ~any(prof), L = NaN; return; end
ac  = xcorr(prof, 'coeff');
mid = n;                       % xcorr('coeff') 的零滞后在第 n 位
half = ac(mid:end);
k = find(half <= 1/exp(1), 1, 'first');
if isempty(k), k = numel(half); end
L = (k-1) * dx;
end

function cv = cv_roi(img, mask)
a = img(mask);  a = a(:);  m = mean(a);
if m <= 0, cv = NaN; return; end
cv = std(a)/m;
end

function g = local_g_at(x0, y0, sx, sy, P)
d = hypot(sx - x0, sy - y0);
g = (d + 1e-6) / P.R;
end

function s = local_yn(c)
if c, s = '是（ROI 内 CV 不能检验闭式）'; else, s = '否（可检验闭式）'; end
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
cfg.name='speckle'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
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

% -------------------------------------------------------------------------
% v1 的教训（保留备查）
%   v1 直接在 4 mm 半径空间 ROI 上算 std/mean，得到 CV(I_E)=0.21、
%   CV(I_BS)=2.13，均比闭式大 2 倍以上。分环诊断显示包络均值在 ROI 内
%   仍有 1.4 倍衰减，且**散斑去相关长度 lambda*R/D 远大于 ROI 直径**，
%   所以 ROI 内的 std/mean 量到的是「同一散斑实现内的包络调制 + 相干旁瓣」，
%   不是散斑涨落的分布。v2 改为 A/B/C 三段：前提检验 -> 系综验证 -> 空间定性。