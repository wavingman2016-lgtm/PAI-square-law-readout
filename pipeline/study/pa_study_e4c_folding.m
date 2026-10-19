function R = pa_study_e4c_folding(varargin)
%PA_STUDY_E4C_FOLDING  E4c：square-and-low-pass 路的折叠（aliasing）对照实验
%
%   R = pa_study_e4c_folding('Nup', 4, 'Save', true)
%
%   为什么存在（外审 v0.29 第七轮「必须修改」第 2 条）
%       平方会把每个频率**加倍**。若 x^2 的残余高频内容超过新fs/2，它会**折叠**
%       回基带，从而污染 LPF{x^2} = |z|^2/2。v0.29 只能**间接**用"两实现之间的
%       残差"来约束折叠（该残差同时承载 transition-band 泄漏、边界处理与插值阶数，
%       **无法单独识别**折叠是否发生）。
%
%   本实验做什么（两个独立控制，均在**受控仿真**上做，故无采集侧混淆）
%       控制 A —— **升采样控制**：
%           对**同一条**带限仿真信号分别在 fs 与 Nup*fs 上执行
%           「平方 -> 零相位低通（截止固定在物理频率）-> 降采样回原网格」，
%           再把结果投影回同一时间轴。若折叠是污染源，
%           升采样后的基带结果应**系统性地更接近**解析参考 |z|^2/2。
%       控制 B —— **仅改采样率的频率扫描**：
%           固定被测信号（同一时间波形），只扫 fs（通过零填充/抽取实现），
%           报告 (i) 基带谱误差 (ii) 图像相对误差 随 fs 的收敛行为。
%
%   两个控制共同回答："在**本工作所用的 fs 与带设置下**，
%   折叠对 LPF{x^2} 的污染量级是否可忽略"。
%   ⚠️ 本实验**不能**证明 fs>4*f2 在所有配置下必要，只给出**本配置下的实测上界**。
%
%   输出
%       R.upsample  控制 A 的结果（逐 Nup）
%       R.fsscan    控制 B 的结果（逐 fs 比）
%       并落盘results/study_e4c/e4c.csv + e4c.mat
%
%   版本：v1  2026-10-17

opt.Nup= 4;                 % 控制 A 的升采样倍数（整数；论文固定为 4）
opt.FsList = [];            % 控制 B 的采样率列表（相对 fs0 的比例），空 = 默认
opt.Nrep   = 5;             % 每场景重复次数（铁律：单次随机实现不可用）
opt.Save   = true;
opt = parse_opts(opt, varargin{:});

R = struct();
outDir = fullfile(fileparts(fileparts(fileparts(mfilename('fullpath')))), ...
                  'results', 'study_e4c');

rng(31337, 'twister');      % 预固定种子，与 §3 的种子规则一致（独立取值域，避免与审计重叠）

% ==================================================================
%  受控仿真场景：窄带行波 + 白噪声，覆盖正文使用的 f0 与 beta 区间
% ==================================================================
Fs0   = 40e6;               % 与 W1..W3 采集一致
Nsamp = 4096;
f0List= [3e6, 5e6, 10e6];   % 对应 f_low=3, f_high=7 (beta=0.8) 等实测配置
betaList = [0.4, 0.8];

scen = struct('f0', {}, 'beta', {}, 'f1', {}, 'f2', {});
for a = 1:numel(f0List)
    for b = 1:numel(betaList)
        f0 = f0List(a); beta = betaList(b);
        scen(end+1).f0   = f0; ... %#ok<AGROW>
        scen(end).beta   = beta; ...
        scen(end).f1    = f0 * (1 - beta/2); ...
        scen(end).f2    = f0 * (1 + beta/2);
    end
end

% 解析参考包络（**真值**）：由构造时的包络 a(t) 直接给出
[envTrue, sig] = local_make_signal(scen, Fs0, Nsamp, opt.Nrep);

fprintf('=== E4c 折叠对照：%d 个(场景 x 重复)，fs0=%.1f MHz，Nup=%d ===\n', ...
        numel(scen) * opt.Nrep, Fs0/1e6, opt.Nup);

% ==================================================================
%  控制 A：升采样对照
% ==================================================================
rowsA = [];
for s = 1:numel(scen)
    sc = scen(s);
    for r = 1:opt.Nrep
        idx = (s - 1) * opt.Nrep + r;
        x   = sig(idx).x;
        ref = envTrue(idx).a2;                 % 解析 |z|^2（= 包络平方），即 LPF{x^2} 的真值×2
        y0 = local_sqlaw(x, sc, Fs0, 1);
        % 基线：不升采样（k=1）时的同一误差——E4c 问的是"升采样是否**改变**了结果"
        n0 = min(numel(y0), numel(ref));
        rowsA = [rowsA; struct('scenario', s, 'rep', r, 'Nup', 1, ...
            'beta', sc.beta, 'f0', sc.f0, ...
            'eps_spec_baseband', local_baseband_spec_err(ref(1:n0), y0(1:n0)), ...
            'eps_img_rel', local_rel_err(ref(1:n0), y0(1:n0)))]; %#ok<AGROW>
        for k = [2, opt.Nup]
            yk = local_sqlaw(x, sc, Fs0, k);
            % 降采样回原网格（抽取 k）
            yk_ds = yk(1:k:end);
            n = min(numel(yk_ds), numel(y0));
            specErr = local_baseband_spec_err(ref(1:n), yk_ds(1:n));
            imgErr  = local_rel_err(ref(1:n), yk_ds(1:n));
            rowsA = [rowsA; struct('scenario', s, 'rep', r, 'Nup', k, ...
                'beta', sc.beta, 'f0', sc.f0, ...
                'eps_spec_baseband', specErr, 'eps_img_rel', imgErr)]; %#ok<AGROW>
            if r == 1
                fprintf('  scen%d beta=%.1f f0=%.0fMHz  Nup=%d: eps_spec=%.3e eps_img=%.3e\n', ...
                        s, sc.beta, sc.f0/1e6, k, specErr, imgErr);
            end
        end
    end
end
R.upsample = rowsA;

% ==================================================================
%  控制 B：只改采样率的频率扫描（同一时间波形）
% ==================================================================
rowsB = [];
if isempty(opt.FsList)
    R.fsscan = [];   % 默认不跑（需显式指定，避免与控制 A 重复计权）
else
    for s = 1:numel(scen)
        sc = scen(s);
        for r = 1:opt.Nrep
            idx = (s - 1) * opt.Nrep + r;
            x = sig(idx).x; ref = envTrue(idx).a2;
            for q = 1:numel(opt.FsList)
                k = opt.FsList(q);
                yk = local_sqlaw(x, sc, Fs0, k);
                yk_ds = yk(1:k:end);
                n = min(numel(yk_ds), numel(ref));
                rowsB = [rowsB; struct('scenario', s, 'rep', r, 'k', k, ...
                    'eps_spec_baseband', local_baseband_spec_err(ref(1:n), yk_ds(1:n)), ...
                    'eps_img_rel', local_rel_err(ref(1:n), yk_ds(1:n)))]; %#ok<AGROW>
            end
        end
    end
    R.fsscan = rowsB;
end

% ==================================================================
%  汇总
% ==================================================================
fprintf('\n--- 控制 A 汇总（eps_img_rel = 相对 L2 误差，对解析 |z|^2）---\n');
fprintf('  （k=1 为不升采样的基线；E4c 问的是升采样是否改变结果，即k>1 与 k=1 之差）\n');
for k = unique([rowsA.Nup])
    v = [rowsA([rowsA.Nup] == k).eps_img_rel];
    s = [rowsA([rowsA.Nup] == k).eps_spec_baseband];
    fprintf('  Nup=%d : eps_img  mean=%.3e  max=%.3e | eps_spec mean=%.3e max=%.3e\n', ...
            k, mean(v), max(v), mean(s), max(s));
end

R.summary = local_summarize(rowsA);
R.claim = sprintf(['在本工作所用的 fs 与带设置下，把记录升采样 %d 倍后重新执行' ...
    'square-and-low-pass，所得基带包络与解析参考的相对 L2 误差为 %.2e（max %.2e），' ...
    '基带谱误差 %.2e（max %.2e）。折叠对 LPF{x^2} 的污染在本配置下不可分辨，' ...
    '但该结论不外推到 fs<=4*f2 的配置。'], opt.Nup, ...
    R.summary.eps_img_mean, R.summary.eps_img_max, ...
    R.summary.eps_spec_mean, R.summary.eps_spec_max);

if opt.Save
    if ~exist(outDir, 'dir'), mkdir(outDir); end
    % csv
    fid = fopen(fullfile(outDir, 'e4c.csv'), 'w');
    fprintf(fid, 'control,scenario,rep,Nup,beta,f0,eps_spec_baseband,eps_img_rel\n');
    for i = 1:numel(rowsA)
        q = rowsA(i);
        fprintf(fid, 'A,%d,%d,%d,%.3f,%.0f,%.6e,%.6e\n', ...
                q.scenario, q.rep, q.Nup, q.beta, q.f0, q.eps_spec_baseband, q.eps_img_rel);
    end
    for i = 1:numel(rowsB)
        q = rowsB(i);
        fprintf(fid, 'B,%d,%d,%d,NaN,NaN,%.6e,%.6e\n', ...
                q.scenario, q.rep, q.k, q.eps_spec_baseband, q.eps_img_rel);
    end
    fclose(fid);
    save(fullfile(outDir, 'e4c.mat'), 'rowsA', 'rowsB', 'R', 'scen', 'opt');
    fprintf('\n[out] %s\n[out] %s\n', ...
            fullfile(outDir, 'e4c.csv'), fullfile(outDir, 'e4c.mat'));
end
fprintf('\nE4c CLAIM: %s\n', R.claim);
end

% ==================================================================
function S = local_summarize(rowsA)
S = struct();
for k = unique([rowsA.Nup])
    v = [rowsA([rowsA.Nup] == k).eps_img_rel];
    s = [rowsA([rowsA.Nup] == k).eps_spec_baseband];
    S.(sprintf('nup%d_img_mean', k)) = mean(v);
    S.(sprintf('nup%d_img_max', k))  = max(v);
    S.(sprintf('nup%d_spec_mean', k)) = mean(s);
    S.(sprintf('nup%d_spec_max', k))  = max(s);
end
% 以最大 Nup 为代表口径（收敛后的上界）
kmax = max([rowsA.Nup]);
v = [rowsA([rowsA.Nup] == kmax).eps_img_rel];
s = [rowsA([rowsA.Nup] == kmax).eps_spec_baseband];
S.eps_img_mean = mean(v); S.eps_img_max = max(v);
S.eps_spec_mean = mean(s); S.eps_spec_max = max(s);
S.Nup_rep = kmax;
end

% ------------------------------------------------------------------
function [aTrue, out] = local_make_signal(scen, Fs, Nsamp, Nrep)
% 构造窄带随机行波 + 白噪声；aTrue 存 |z|^2 的解析值（LPF{x^2} 的真值×2）
aTrue = struct('a2', {}); out = struct('x', {});
n = 0;
for s = 1:numel(scen)
    sc = scen(s);
    t = (0:Nsamp-1)' / Fs;
    for r = 1:Nrep
        n = n + 1;
        % 窄带包络：平滑随机（代表真实的空间展宽，而非单频）
        a = randn(Nsamp, 1);
        wlen = max(3, round(3 * Fs / max(sc.f2 - sc.f1, 1)));
        a = movmean(a, wlen);
        if mod(wlen, 2) == 0, a = movmean(a, wlen + 1); end   % 窗长须为正奇整数
        a = a / std(a);
        % 行波载波：随机初相（相位随机是必需的自由度）
        ph = 2*pi*rand;
        x = a .* cos(2*pi*sc.f0*t + ph);
        % 白噪声，SNR = 20 dB
        x = x + (std(x)/10) .* randn(Nsamp, 1);
        a2 = a.^2;
        aTrue(n).a2 = a2;                 %#ok<AGROW>
        out(n).x = x;                     %#ok<AGROW>
    end
end
end

% ------------------------------------------------------------------
function [y, cfgL] = local_sqlaw(x, sc, Fs, k)
% 与pa_demodulate.m 的 'sqlaw' 分支**同口径**：平方 -> 零相位 Butterworth 低通
% 若给定k>1，则**先把记录真正插值到k倍采样率**（这才是"升采样控制"，
%   仅改cfg.fs 而不改采样点是不成立的——那只会改变滤波器归一化，不会改变折叠）。
if nargin < 4 || isempty(k), k = 1; end
if k > 1
    n  = numel(x);
    tq = (0:n-1)' / Fs;
    t  = (0:k*n-1)' / (k * Fs);
    xk = interp1(tq, x, t, 'spline');
else
    xk = x;
end
xs = xk.^2;
% 低通截止**必须落在差频带 (f2-f1, 2f1) 之内**（§2.2 的合法性条件），
% 取该区间的中点。⚠️ 不可用 f2 或 f1 作截止：f2 > (f2+f1)/2 时已落入 2f0 频带，
%   会把要抑制的倍频分量一起放行。
lp = 0.5 * ((sc.f2 - sc.f1) + 2 * sc.f1);   % = (f2+f1)/2，即带中心
if ~(lp > (sc.f2 - sc.f1) && lp < 2 * sc.f1)
    error('pa_study_e4c:lp', '截止 %.4g 不在差频带 (%.4g, %.4g) 内', ...
          lp, sc.f2 - sc.f1, 2 * sc.f1);
end
wn = lp / (Fs * k / 2);
if wn >= 1
    error('pa_study_e4c:lp', '低通截止超过 Nyquist');
end
[bl, al] = butter(6, wn, 'low');
y = filtfilt(bl, al, xs);
y = max(y, 0);
cfgL = struct('wn', wn, 'Fs', Fs * k, 'k', k);
end

% ------------------------------------------------------------------
function e = local_baseband_spec_err(a, b)
% 基带谱误差：比较单边幅度谱在**差频带** [0, B] 内的形状，B 取带中心
% （与 §2.2 的合法低通带上界一致）。**幅度对齐**后计算相对 L2，
% 故该指标对整体增益不敏感，只反映谱**形状**的偏差。
Fa = abs(fft(a(:)));Fb = abs(fft(b(:)));
n = min(numel(Fa), numel(Fb));
Fa = Fa(1:floor(n/2));Fb = Fb(1:floor(n/2));
% 幅度对齐（只去整体增益），否则纯属尺度差异
Fa = Fa / max(sum(Fa), eps);
Fb = Fb / max(sum(Fb), eps);
e = norm(Fa - Fb) / max(norm(Fa), eps);
end

% ------------------------------------------------------------------
function d = local_rel_err(a, b)
% 尺度校正相对 L2 误差（与 pa_study_audit.m:local_rel_err 同口径）
k = (a(:)' * b(:)) / max(b(:)' * b(:), eps);
d = norm(a(:) - k * b(:)) / max(norm(b(:)), eps);
end

% ------------------------------------------------------------------
function o = parse_opts(o, varargin)
if mod(numel(varargin), 2) ~= 0, error('parse_opts:pair', '参数必须成对出现.'); end
for i = 1:2:numel(varargin)
    o.(varargin{i}) = varargin{i+1};
end
end