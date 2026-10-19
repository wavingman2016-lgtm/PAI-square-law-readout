function B = pa_band_audit(sigMat, cfg, varargin)
%PA_BAND_AUDIT  实测信号带宽审计（决定 D2' 能否直接替代 Hilbert，低通截止取多少）
%
%   B = pa_band_audit(sigMat, cfg, 'Name', Value, ...)
%
%   为什么必须先做这一步
%     pa_cfg 里 f_low/f_high 是**分析带**（人为设定，为保留全部 PA 频段而开得较宽），
%     而"用 LPF(x^2) 免去 Hilbert"这一捷径要求信号满足窄带条件
%         B < 2*f_low   <=>   f_high < 3*f_low   <=>   beta = B/f0 < 1
%     满足时合法低通区间为 ( B , 2*f_low )。若分析带远宽于换能器实际带宽，
%     该区间会变成空集，LPF(x^2) 就退化成"带 2f0 残留的裸平方"——这正是
%     "部分数据 D2 表现不理想"的直接成因。故必须先从数据量出真实带宽。
%
%   稳健性设计（2026-10-14 二次修正，v2）
%     ① 逐通道周期图后**取中位数**（而非均值）：抗异常通道、抗窄带毛刺
%     ② 平滑后再找峰：避免峰位被单频毛刺吸走
%     ③ **同时**给出 -6 dB 带与 5%-95% 累积能量带：
%        - 单频尖峰虽在 -6 dB 判据下能"劫持"峰位，但其总能量极小，
%          故累积能量带对它不敏感。实测 data1 的 -6 dB 带曾被尖峰压缩到
%          0.03 MHz，而累积能量带稳定给出 3-9 MHz 的真实换能器带。
%     ④ 尖峰自动识别：B6 < 0.25*f_peak 时判为毛刺驱动，改用累积能量带
%
%   输入
%     sigMat : [nSamples x nChannels] 已完成去 DC + 带通的信号
%     cfg    : pa_cfg 配置
%
%   输出（结构体 B）
%     f_peak      峰值频率 (Hz)
%     f_lo6/f_hi6 平滑谱上相对峰值 -6 dB 带上下限 (Hz)
%     B6          -6 dB 带宽 (Hz)
%     f05/f95     5% / 95% 累积能量频率 (Hz)
%     Bcum        累积能量带宽 f95-f05 (Hz)
%     f_lo/f_hi   **实际用于判据**的带边 (Hz)
%     B_used      实际带宽 = f_hi - f_lo (Hz)
%     beta_used   B_used / f0
%     bandSrc     'B6' | 'cum'（哪个被判据采用）
%     spurFlag    是否检测到窄带尖峰主导
%
%     fcnt        能量重心频率 (Hz)
%     f50         累积能量 50% 频率 (Hz)
%     ok          D2' 是否可直接使用（B_used < 2*f_lo）
%     lp_cutoff   推荐低通截止 (Hz)（合法时取区间中点）
%     lp_range    合法低通区间 [lo, hi] (Hz)（不合法时 hi <= lo）
%     nActiveCh   参与统计的有效通道数
%     smoothBins  平滑窗宽（bin）
%
%   版本：v2  2026-10-14（中位数谱 + 累积能量带 + 尖峰识别 + 正确判据）

opt.MaxCh  = 64;
opt.Smooth = [];          % 平滑窗宽（bin）；[] = 按分析带 5% 自动
opt = parse_opts(opt, varargin{:});

nS = size(sigMat, 1);
nC = size(sigMat, 2);
win = hann(nS);
nHalf = floor(nS / 2) + 1;
df    = cfg.fs / nS;
freq  = (0:nHalf-1)' * df;

% 选通道：取 AC 均方根最强的若干通道（信噪比最好）
rmsCh = sqrt(mean(sigMat .^ 2, 1));
[~, ord] = sort(rmsCh, 'descend');
sel = ord(1:min(opt.MaxCh, nC));
sel = sel(rmsCh(sel) > 0);
nActive = numel(sel);

if nActive == 0
    B = local_empty(cfg);
    return;
end

% ------------------------------------------------------------------
% ① 逐通道周期图（对数域中位数，再回线性域）
%    在中位数前取 log 可让"多数通道都有的成分"主导，
%    少数通道上的强窄带干扰会被压制。
% ------------------------------------------------------------------
Lg = zeros(nHalf, nActive);
for j = 1:nActive
    Pf = abs(fft(sigMat(:, sel(j)) .* win)) .^ 2;
    Lg(:, j) = log(Pf(1:nHalf) + eps);
end
P = exp(median(Lg, 2));

% ------------------------------------------------------------------
% ② 平滑
% ------------------------------------------------------------------
bw = max(cfg.f_high - cfg.f_low, df);
if isempty(opt.Smooth)
    nb = max(3, round(0.05 * bw / df));
else
    nb = max(3, round(opt.Smooth));
end
nb = min(nb, max(3, floor(nHalf / 10)));
Ps = movmean(P, nb);

% 只在分析带内统计
inBand = freq >= cfg.f_low & freq <= cfg.f_high;
if ~any(inBand)
    inBand = true(size(freq));
end
Psb = Ps;  Psb(~inBand) = 0;

[~, ipk] = max(Psb);
f_peak = freq(ipk);
if f_peak <= 0, f_peak = cfg.f0; end

% ------------------------------------------------------------------
% ③ -6 dB 带（在平滑谱上扫描）
% ------------------------------------------------------------------
pdb = 10 * log10(Psb / (max(Psb) + eps));
k = ipk;  while k > 1 && pdb(k) > -6, k = k - 1; end
f_lo6 = freq(k);
k = ipk;  while k < numel(pdb) && pdb(k) > -6, k = k + 1; end
f_hi6 = freq(k);
B6    = f_hi6 - f_lo6;

% ------------------------------------------------------------------
% ④ 5%-95% 累积能量带（抗单频尖峰）
% ------------------------------------------------------------------
Pp = Psb / (sum(Psb) + eps);
c  = cumsum(Pp);
i05 = find(c >= 0.05, 1, 'first');
i95 = find(c >= 0.95, 1, 'first');
i50 = find(c >= 0.50, 1, 'first');
if isempty(i05), i05 = 1;                end
if isempty(i95), i95 = numel(freq);      end
if isempty(i50), i50 = round(numel(freq)/2); end
f05 = freq(i05);  f95 = freq(i95);  f50 = freq(i50);
Bcum = f95 - f05;

% 能量重心
fcnt = sum(freq .* Pp);

% ------------------------------------------------------------------
% ⑤ 尖峰识别与实际判据带的选择
% ------------------------------------------------------------------
spurFlag = (B6 < 0.25 * max(f_peak, eps));       % -6 dB 带极窄 -> 毛刺主导
if spurFlag
    f_lo = f05;  f_hi = f95;  bandSrc = 'cum';
else
    f_lo = f_lo6;  f_hi = f_hi6;  bandSrc = 'B6';
end
B_used    = max(f_hi - f_lo, df);
beta_used = B_used / max(f_peak, eps);

% ------------------------------------------------------------------
% ⑥ D2' 合法性（正确形式）：合法低通区间 = ( B , 2*f_lo )
% ------------------------------------------------------------------
% 信号占据 [f_lo, f_hi]；基带项 |z|^2 占据 [0, B_used]，
% 二倍频项占据 [2*f_lo, 2*f_hi]。不重叠 <=> B_used < 2*f_lo
lo = B_used;
hi = 2 * f_lo;
ok = hi > lo;
if ok
    lp = 0.5 * (lo + hi);
else
    lp = cfg.f0;
end

B = struct('f_peak', f_peak, 'f_lo6', f_lo6, 'f_hi6', f_hi6, 'B6', B6, ...
           'f05', f05, 'f95', f95, 'Bcum', Bcum, 'f50', f50, ...
           'f_lo', f_lo, 'f_hi', f_hi, 'B_used', B_used, ...
           'beta_used', beta_used, 'bandSrc', bandSrc, 'spurFlag', spurFlag, ...
           'fcnt', fcnt, 'ok', ok, 'lp_cutoff', lp, 'lp_range', [lo hi], ...
           'nActiveCh', nActive, 'smoothBins', nb);

end

% ==================================================================
function B = local_empty(cfg)
B = struct('f_peak', NaN, 'f_lo6', NaN, 'f_hi6', NaN, 'B6', NaN, ...
           'f05', NaN, 'f95', NaN, 'Bcum', NaN, 'f50', NaN, ...
           'f_lo', NaN, 'f_hi', NaN, 'B_used', NaN, ...
           'beta_used', NaN, 'bandSrc', 'none', 'spurFlag', false, ...
           'fcnt', NaN, 'ok', false, 'lp_cutoff', cfg.f0, ...
           'lp_range', [NaN NaN], 'nActiveCh', 0, 'smoothBins', NaN);
end

% ==================================================================
function o = parse_opts(o, varargin)
if mod(numel(varargin), 2) ~= 0
    error('parse_opts:pair', '参数必须成对出现.');
end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o, k), error('parse_opts:unknown', '未知参数：%s', k); end
    o.(k) = varargin{i+1};
end
end
