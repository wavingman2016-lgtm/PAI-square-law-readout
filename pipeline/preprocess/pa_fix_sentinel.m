function [sigMat, info] = pa_fix_sentinel(sigMat, varargin)
%PA_FIX_SENTINEL  修复采集边界哨兵样本（整行全 0 的无效采样点）
%
%   [sigMat, info] = pa_fix_sentinel(sigMat, 'Name', Value, ...)
%
%   背景（实测发现，见 docs/05 #4）
%     OADAT 的 *_raw 每条 trace 的**第 0 个采样点恒为 0**（哨兵值）.
%     若不去掉，它会在带通/平方时被当作真实下降沿，产生假低频分量.
%     自有数据也可能存在前若干点未采集的情况.
%
%   判据（保守，只处理"无害"的情形）
%     某采样点在**所有通道上同时为 0**，且位于 trace 起始段
%     （默认前 10 点之内）-> 判为哨兵，用其后一个正常样本值填充.
%
%   可选参数
%     'ScanLen'  起始扫描长度（默认 10）
%
%   版本：v1  2026-10-14

opt.ScanLen = 10;
opt = parse_opts(opt, varargin{:});

info = struct('nFixedSamples', 0, 'fixedIndex', []);

if isempty(sigMat), return; end

nS = min(opt.ScanLen, size(sigMat, 1));
fixed = [];
for k = 1:nS
    if all(sigMat(k, :) == 0) && k < size(sigMat, 1)
        fixed(end+1) = k; %#ok<AGROW>
    end
end

for k = fixed
    sigMat(k, :) = sigMat(k + 1, :);
end

info.nFixedSamples = numel(fixed);
info.fixedIndex    = fixed;

end

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
