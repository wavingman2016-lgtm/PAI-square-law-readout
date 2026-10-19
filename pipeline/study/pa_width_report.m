function pa_width_report()
%PA_WIDTH_REPORT  统一用"正确插值"的半高宽重算全部受控仿真的宽度（不出图）
%
%   为什么需要它
%     1) 旧版 pa_study_resolution.local_width 的 interp_cross 在"两侧都不跨阈"时
%        回退到 i-1..i+1，会跳过下降沿改取旁瓣上升沿 -> 强旁瓣剖面（相干 PSF）
%        得到错误宽度。已修正。
%     2) MATLAB -batch 下 local_plot 有时会挂死（无图形窗口），故本脚本**只算不画**。
%     3) 宽度是 E1 唯一允许跨臂比较的量，必须独立可复核。
%
%   读取：results/study_<array>_<regime>/study_resolution.mat（由 pa_study_resolution 产出）
%   输出：控制台表格
%
%   版本：v1  2026-10-14

pipeRoot = fileparts(fileparts(mfilename('fullpath')));   % .../pipeline
root     = fullfile(fileparts(pipeRoot), 'results');

dirs = {'study_semicircle128_noise', 'study_ring256_noise', ...
        'study_semicircle128_clutter', 'study_ring256_clutter'};

fprintf('\n%-26s %8s %8s %8s %8s %8s %8s\n', ...
    'case', 'wC', 'wM', 'w_-3(M)', 'w(M^2)', 'wE(-3dB)', 'w_sqrtE');
fprintf('%s\n', repmat('-', 1, 82));

for i = 1:numel(dirs)
    f = fullfile(root, dirs{i}, 'study_resolution.mat');
    if ~exist(f, 'file')
        fprintf('%-26s  [缺文件]\n', dirs{i}); continue;
    end
    S  = load(f);
    ax = S.R1.ax(:).';
    pC = S.R1.profC(:).';  pM = S.R1.profM(:).';  pE = S.R1.profE(:).';
    wC  = local_width(ax, pC, 0.5);
    wM  = local_width(ax, pM, 0.5);
    w3M = local_width(ax, pM, 1/sqrt(2));
    wM2 = local_width(ax, pM.^2, 0.5);          % 图像域平方 = 恒等式左端
    wE  = local_width(ax, pE, 0.5);
    wEa = local_width(ax, sqrt(max(pE, 0)), 0.5);
    fprintf('%-26s %8.4f %8.4f %8.4f %8.4f %8.4f %8.4f\n', ...
        strrep(dirs{i}, 'study_', ''), wC, wM, w3M, wM2, wE, wEa);
    fprintf('   恒等式核对: |w(M^2) - w_-3(M)| = %.4f mm = %.3f px ; E/M = %.3f ; M/C = %.2f\n', ...
        abs(wM2 - w3M), abs(wM2 - w3M)/abs(ax(2)-ax(1)), wEa/wM, wM/wC);
end

% 参考量
lambda = 1478 / 5e6 * 1e3;
fprintf('\n参考: lambda = %.4f mm ; lambda/2 = %.4f mm（相干臂理论极限）\n', lambda, lambda/2);
end

% ==================================================================
function w = local_width(ax, y, lvl)
% 半高全宽（线性插值）：用"跨越阈值的相邻两点"插值。
ax = ax(:).'; y = y(:).';
pk = max(y); if pk <= 0, w = NaN; return; end
thr = lvl*pk; n = numel(y);
[~, i0] = max(y);
L = i0;  while L > 1 && y(L) > thr,  L  = L  - 1; end
Rr = i0; while Rr < n && y(Rr) > thr, Rr = Rr + 1; end
if y(L) > thr
    xl = ax(1);
else
    xl = ax(L) + (thr - y(L)) * (ax(L+1) - ax(L)) / (y(L+1) - y(L));
end
if y(Rr) > thr
    xr = ax(n);
else
    xr = ax(Rr-1) + (thr - y(Rr-1)) * (ax(Rr) - ax(Rr-1)) / (y(Rr) - y(Rr-1));
end
w = abs(xr - xl);
end
