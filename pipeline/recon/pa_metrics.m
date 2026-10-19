function M = pa_metrics(prof, ax, roi, varargin)
%PA_METRICS  统一的图像质量指标（定义一次，全项目复用）
%
%   M = pa_metrics(prof, ax, roi, 'Name', Value, ...)
%
%   指标（每个都给出明确定义，消除原脚本里"同一名字不同算法"的问题）
%
%     aFWHM  表观半高宽，mm.! 仅作**表观量**记录，**不得**用于主张分辨率：
%            对高斯型 PSF 有 FWHM(g^2) = FWHM(g)/sqrt(2)，即 -29.3%，
%            这是平方运算的数学必然，与成像系统分辨能力无关（docs/04 #3）.
%
%     CNR    对比度噪声比：(mean_in - mean_out) / std_out
%     PSR    峰值旁瓣比：peak(prof) / max(prof 在旁瓣带内)
%     gCNR   广义 CNR：1 - sum_k min(p_in(k), p_out(k))，**对显示窗不敏感**，
%            建议作为主指标（原脚本未用，属新增）.
%     DR     动态范围 (dB)：20*log10(peak / median)
%     Conc   中心能量占比（无量纲）：ROI 内剖面积分 / 全剖面积分
%
%   可选参数
%     'Sidelobe'  旁瓣带的相对位置范围（默认 [0.15 0.45] * 半宽）
%
%   输出
%     M : 结构体
%
%   版本：v1  2026-10-14

opt.Sidelobe = [0.15 0.45];
opt = parse_opts(opt, varargin{:});

prof = prof(:).';
ax   = ax(:).';
n    = numel(prof);

% ---- aFWHM -------------------------------------------------------
M.aFWHM = local_fwhm(ax, prof);

% ---- CNR ---------------------------------------------------------
pin  = prof(roi.inMask);
pout = prof(roi.outMask);
M.CNR = (mean(pin) - mean(pout)) / (std(pout) + eps);

% ---- PSR ---------------------------------------------------------
halfSpan = max(abs(ax(roi.inIdx(end)) - ax(roi.inIdx(1))), eps) / 2;
lo = find(abs(ax) >= opt.Sidelobe(1) * halfSpan, 1, 'first');
hi = find(abs(ax) >= opt.Sidelobe(2) * halfSpan, 1, 'first');
if isempty(lo), lo = 1; end
if isempty(hi), hi = n; end
sideIdx = [1:max(1, lo-1), min(n, hi+1):n];
sideIdx = sideIdx(sideIdx >= 1 & sideIdx <= n);
if isempty(sideIdx), sideIdx = roi.outIdx; end
M.PSR = max(prof) / (max(prof(sideIdx)) + eps);

% ---- gCNR --------------------------------------------------------
M.gCNR = local_gcnr(pin, pout);

% ---- DR ----------------------------------------------------------
M.DR = 20 * log10((max(prof) + eps) / (median(prof) + eps));

% ---- 中心能量占比 ------------------------------------------------
M.Conc = sum(prof(roi.inMask)) / (sum(prof) + eps);

% ---- 元信息 ------------------------------------------------------
M.peakPos_mm = ax(find(prof == max(prof), 1, 'first'));

end

% ==================================================================
function f = local_fwhm(x, y)
% 线性插值精度更高的半高宽
y = y(:).';  x = x(:).';
peak = max(y);
if peak <= 0, f = NaN; return; end
half = peak / 2;

above = y >= half;
if ~any(above), f = NaN; return; end

i1 = find(above, 1, 'first');
i2 = find(above, 1, 'last');

if i1 > 1
    xl = x(i1-1) + (half - y(i1-1)) * (x(i1) - x(i1-1)) / (y(i1) - y(i1-1) + eps);
else
    xl = x(i1);
end
if i2 < numel(y)
    xr = x(i2) + (half - y(i2)) * (x(i2+1) - x(i2)) / (y(i2+1) - y(i2) + eps);
else
    xr = x(i2);
end

f = abs(xr - xl);
end

% ==================================================================
function g = local_gcnr(a, b)
% 广义 CNR：1 - 两分布直方图的归一化重叠面积
if isempty(a) || isempty(b), g = NaN; return; end
lo = min([a(:); b(:)]);
hi = max([a(:); b(:)]);
if hi <= lo, g = 1; return; end
edges = linspace(lo, hi, 65);
pa = histcounts(a, edges);  pa = pa / sum(pa);
pb = histcounts(b, edges);  pb = pb / sum(pb);
g = 1 - sum(min(pa, pb));
end

% ==================================================================
function o = parse_opts(o, varargin)
if mod(numel(varargin), 2) ~= 0
    error('parse_opts:pair', '参数必须成对出现.');
end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o, k)
        error('parse_opts:unknown', '未知参数：%s', k);
    end
    o.(k) = varargin{i+1};
end
end
