function [prof, ax, roi] = pa_profile(IM, grid, mode, varargin)
%PA_PROFILE  从重建图提取点扩散函数(PSF) / 线扩散函数(LSF) 剖面
%
%   [prof, ax, roi] = pa_profile(IM, grid, mode, 'Name', Value, ...)
%
%   钨丝点线图的基本量：
%     mode='point'  钨丝**横断面**（点状吸收体）-> 取过峰值的横向剖面 = PSF
%     mode='line'   钨丝**纵断面**（线状吸收体）-> 沿丝轴的纵向剖面 = LSF
%     mode='auto'   自动判峰后取横向剖面（等价 point）
%
%   可选参数
%     'PeakXY'    手动指定峰值像素 [row, col]（默认自动找全局最大）
%     'Width'     背景带外移量（像素，默认 = 0.25*图宽）
%     'Band'      峰值带半宽（像素，默认 = 0.05*图宽）
%     'Dir'       'row' 沿行取剖面 | 'col' 沿列取剖面（默认 'row'）
%
%   输出
%     prof   : 归一化剖面（峰值 = 1）
%     ax     : 对应横坐标（mm）
%     roi    : 结构体 {peakRow, peakCol, inIdx, outIdx, inMask, outMask}
%
%   版本：v1  2026-10-14

opt.PeakXY = [];
opt.Width  = [];
opt.Band   = [];
opt.Dir    = 'row';
opt = parse_opts(opt, varargin{:});

[Ny, Nx] = size(IM);
if isempty(opt.Width), opt.Width = round(0.25 * min(Ny, Nx)); end
if isempty(opt.Band),  opt.Band  = max(2, round(0.05 * min(Ny, Nx))); end

% ---- 定位峰值 ----------------------------------------------------
if isempty(opt.PeakXY)
    [~, lin] = max(IM(:));
    [pr, pc] = ind2sub([Ny, Nx], lin);
else
    pr = opt.PeakXY(1);  pc = opt.PeakXY(2);
end

% ---- 取剖面 ------------------------------------------------------
switch lower(opt.Dir)
    case 'row'
        profRaw = IM(pr, :);
        ax = grid.x;
        ci = pc;
    case 'col'
        profRaw = IM(:, pc);
        ax = grid.y;
        ci = pr;
    otherwise
        error('pa_profile:dir', '未知方向：%s', opt.Dir);
end

prof = profRaw(:).';
prof = prof / (max(prof) + eps);

% ---- 定义 ROI（用于 CNR / gCNR）---------------------------------
n = numel(prof);
inIdx  = max(1, ci - opt.Band) : min(n, ci + opt.Band);
outL   = max(1, ci - opt.Width) : max(1, ci - opt.Band) - 1;
outR   = min(n, ci + opt.Band) + 1 : min(n, ci + opt.Width);
outIdx = [outL(:); outR(:)];
outIdx = outIdx(outIdx >= 1 & outIdx <= n);
if isempty(outIdx)
    outIdx = [1:max(1, ci - opt.Band - 1), min(n, ci + opt.Band + 1):n];
    outIdx = outIdx(outIdx >= 1 & outIdx <= n);
end

inMask  = false(n, 1);  inMask(inIdx)  = true;
outMask = false(n, 1);  outMask(outIdx) = true;

roi = struct('peakRow', pr, 'peakCol', pc, 'inIdx', inIdx, ...
             'outIdx', outIdx, 'inMask', inMask, 'outMask', outMask, ...
             'dir', opt.Dir);

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
