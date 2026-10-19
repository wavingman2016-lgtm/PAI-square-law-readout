function [sigMatF, info] = pa_bandpass(sigMat, cfg, varargin)
%PA_BANDPASS  零相位 Butterworth 带通（预处理链第 2 步，对齐 OADAT 口径）
%
%   [sigMatF, info] = pa_bandpass(sigMat, cfg, 'Name', Value, ...)
%
%   与 OADAT 官方实现（pyoat.preprocessing.filterBandPass.sigMatFilter）
%   的对应关系：
%
%     OADAT 原式                             本函数等价写法
%     ---------------------------------------------------------------
%     nyquistRatio = 0.5*fSampling            cfg.fs/2
%     Wn = [f_low, f_high] / nyquistRatio     [cfg.f_low, cfg.f_high]/(cfg.fs/2)
%     butter(fOrder, Wn, 'bandpass')          butter(order, Wn, 'bandpass')
%     filtfilt(b, a, sigMat, padlen=0, axis=0) filtfilt(b, a, sigMat)
%
%   ! 两处刻意的差异（可由选项切回 OADAT 原样）
%     (1) PadLen：OADAT 用 padlen=0，会在 trace 两端产生幅度可达信号
%         数倍的滤波瞬态.本函数默认用 MATLAB 自动补边（更稳）.
%         需要严格复现 OADAT 时传 'PadLen', 0.
%     (2) Invert：OADAT 的 cpuBP.reconBP 在滤波后整体乘 -1（配合其
%         reconType 的极性约定）.本函数默认不翻转；需要时传 'Invert', true.
%
%   版本：v1  2026-10-14

opt.PadLen = [];       % [] = 自动补边；0 = OADAT 原样
opt.Invert = false;
opt.LowCut  = [];
opt.HighCut = [];
opt.Order   = [];
opt = parse_opts(opt, varargin{:});

fLow  = pick(opt.LowCut,  cfg.f_low);
fHigh = pick(opt.HighCut, cfg.f_high);
order = pick(opt.Order,   cfg.f_order);

nyq = cfg.fs / 2;
Wn  = [fLow, fHigh] / nyq;

if Wn(1) <= 0 || Wn(2) >= 1
    error('pa_bandpass:range', ...
        '带通 [%.3g, %.3g] Hz 相对 Nyquist(%.3g Hz) 非法.', fLow, fHigh, nyq);
end

[b, a] = butter(order, Wn, 'bandpass');

if isempty(opt.PadLen)
    sigMatF = filtfilt(b, a, sigMat);            % 自动补边（默认）
else
    sigMatF = filtfilt(b, a, sigMat, opt.PadLen); % OADAT 原样用 0
end

if opt.Invert
    sigMatF = -sigMatF;
end

info = struct('f_low', fLow, 'f_high', fHigh, 'order', order, ...
              'padLen', opt.PadLen, 'invert', opt.Invert, ...
              'beta', (fHigh - fLow) / cfg.f0);

end

% ------------------------------------------------------------------
function v = pick(v, fallback)
if isempty(v), v = fallback; end
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
