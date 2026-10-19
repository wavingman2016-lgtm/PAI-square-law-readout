function [sigMat, info] = pa_dc_remove(sigMat, method, firstN)
%PA_DC_REMOVE  逐通道去直流（预处理链第 1 步，必须在任何非线性运算之前）
%
%   [sigMat, info] = pa_dc_remove(sigMat, method)
%
%   为什么必须在平方之前做
%     OADAT 实测：*_raw 每通道存在约 2000 counts 的直流偏置，而真实
%     交流幅度仅 +/- 1~4 counts.若直接平方：
%         (DC + p)^2 = DC^2 + 2*DC*p + p^2
%     其中 2*DC*p 项比 p^2 大 3 个数量级，**平方成像会退化成"放大版
%     原图"**，完全丧失能量域语义.这是 PAI_FBP_6_DAS.m 用 data.^2 时
%     结果不稳定的直接原因之一.
%
%   输入
%     sigMat : [nSamples x nChannels]
%     method : 'median'（默认，对该通道时间轴取中位数，抗脉冲）
%              'mean'  （OADAT sigMatNormalize 官方口径）
%
%   版本：v1  2026-10-14

if nargin < 2 || isempty(method)
    method = 'median';
end
if nargin < 3 || isempty(firstN)
    firstN = 100;
end

info = struct('method', method, 'dcPerChannel', []);

switch lower(method)
    case 'median'
        dc = median(sigMat, 1);
    case 'mean'
        dc = mean(sigMat, 1);
    case 'firstn'
        % 原 128 阵元脚本的旧做法：只取前 N 点中位数作为基线
        % （PAI_FBP_1_V2.m L88-90）
        n = min(firstN, size(sigMat, 1));
        dc = median(sigMat(1:n, :), 1);
    otherwise
        error('pa_dc_remove:method', '未知 method：%s', method);
end

sigMat = sigMat - repmat(dc, size(sigMat, 1), 1);
info.dcPerChannel = dc;

end
