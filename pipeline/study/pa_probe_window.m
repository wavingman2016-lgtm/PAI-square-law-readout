function pa_probe_window()
% 窗不变性微检验：仿射窗 vs 裁剪窗 对 gCNR/CNR 的影响
% 结论预期：
%   - 仿射窗 (WL/WW 线性重标) -> gCNR 严格不变（两直方图同尺度缩放）
%   - 裁剪饱和窗 (UI8 clamp)  -> gCNR 略变（饱和把像素堆到端点）
% 故：指标必须在**数据域 float** 上算，窗只用于渲染。

S = load('results/study_semicircle128_noise/study_resolution.mat');
IE = S.R1.IE;                      % 能量图（float）
IE = IE / max(IE(:));              % 归一到 [0,1]，模拟渲染前状态

ax = S.R1.ax(:)';
[~, i0] = min(abs(ax));
prof = IE(i0, :).';                % 过峰横向剖面

% ROI：目标半宽 0.9 mm，背景 4~8 mm
c = 0;
inMask  = abs(ax - c) <= 0.9;
outMask = abs(ax - c) >= 4 & abs(ax - c) <= 8;

fprintf('%-28s %10s %10s\n', 'window', 'gCNR', 'CNR');
fprintf('%s\n', repmat('-', 1, 50));

% (0) 数据域 float（参考）
m0 = metrics(prof(inMask), prof(outMask));
fprintf('%-28s %10.4f %10.3f\n', 'float (data domain)', m0.gCNR, m0.CNR);

% (1) 四档仿射窗：u -> clip((u-(WL-WW/2))/WW, 0, 1) 但**不裁剪**（纯仿射）
WLs = [0.50 0.25 0.40 0.35];
WWs = [1.00 0.50 0.50 0.80];
for k = 1:numel(WLs)
    WL = WLs(k); WW = WWs(k);
    u = (prof - (WL - WW/2)) / WW;         % 纯仿射，不裁剪
    m = metrics(u(inMask), u(outMask));
    fprintf('%-28s %10.4f %10.3f\n', sprintf('affine WL=%.2f WW=%.2f', WL, WW), m.gCNR, m.CNR);
end

% (2) 带裁剪饱和（真实显示路径）
for k = 1:numel(WLs)
    WL = WLs(k); WW = WWs(k);
    u = min(max((prof - (WL - WW/2)) / WW, 0), 1);
    m = metrics(u(inMask), u(outMask));
    fprintf('%-28s %10.4f %10.3f\n', sprintf('clipped WL=%.2f WW=%.2f', WL, WW), m.gCNR, m.CNR);
end
end

function m = metrics(a, b)
lo = min([a(:); b(:)]); hi = max([a(:); b(:)]);
if hi <= lo, m.gCNR = 1; else
    edges = linspace(lo, hi, 65);
    pa = histcounts(a, edges); pa = pa/sum(pa);
    pb = histcounts(b, edges); pb = pb/sum(pb);
    m.gCNR = 1 - sum(min(pa, pb));
end
m.CNR = (mean(a) - mean(b)) / (std(b) + eps);
end
