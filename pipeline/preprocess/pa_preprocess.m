function D = pa_preprocess(sigMat, cfg, varargin)
%PA_PREPROCESS  统一预处理链（单一入口，全项目所有成像脚本必须走这里）
%
%   D = pa_preprocess(sigMat, cfg, 'Name', Value, ...)
%
%   流程（对齐 OADAT，见 docs/06 #2）
%     (1) 哨兵修复   pa_fix_sentinel   整行全 0 的无效起始样本
%     (2) 去直流     pa_dc_remove      逐通道减中位/均值（**平方之前必须做**）
%     (3) 带通       pa_bandpass       Butterworth 零相位（默认阶 3）
%     (4) 解调       pa_demodulate     四种口径并行输出，便于同图对照
%     (5) 平滑       movmean           窗长 cfg.smooth（OADAT 不做，设 1 即关闭）
%
%   输出 D（结构体）
%     D.raw        原始信号（未改动，供审计）
%     D.sentinel   哨兵修复后的信号
%     D.dcRemoved  去直流后
%     D.filtered   带通后（**这是后续成像与重算的共同起点**）
%     D.env        D1  = |hilbert|            线性包络
%     D.env2       D1^2 = |hilbert|^2           包络平方（现有主方法）
%     D.sqlaw      D2' = LPF(x^2)              平方律检波（免 Hilbert）
%     D.sq         D2  = x^2                   裸平方（反例）
%     D.info       各步骤诊断
%
%   可选参数
%     'Methods'      需要输出的解调方式（默认 {'env','env2','sqlaw','sq'}）
%     'FixSentinel'  是否做哨兵修复（默认 true）
%     'Smooth'       平滑窗长（默认 cfg.smooth）
%     'DcMethod'     覆盖 cfg.dcMethod
%     'PadLen'       传给 pa_bandpass（默认自动补边）
%
%   版本：v1  2026-10-14

opt.Methods     = {'env', 'env2', 'sqlaw', 'sq'};
opt.FixSentinel = true;
opt.Smooth      = [];
opt.DcMethod    = [];
opt.DcFirstN    = [];
opt.PadLen      = [];
opt = parse_opts(opt, varargin{:});

if isempty(opt.Smooth),   opt.Smooth   = cfg.smooth; end
if isempty(opt.DcMethod), opt.DcMethod = cfg.dcMethod; end
if isempty(opt.DcFirstN), opt.DcFirstN = cfg.dcFirstN; end

D = struct();
D.cfg  = cfg;
D.raw  = double(sigMat);
D.info = struct();

% (1) 哨兵修复
if opt.FixSentinel
    [D.sentinel, D.info.sentinel] = pa_fix_sentinel(D.raw);
else
    D.sentinel = D.raw;
    D.info.sentinel = struct('nFixedSamples', 0, 'fixedIndex', []);
end

% (2) 去直流
[D.dcRemoved, D.info.dc] = pa_dc_remove(D.sentinel, opt.DcMethod, opt.DcFirstN);

% (3) 带通
[D.filtered, D.info.bandpass] = pa_bandpass(D.dcRemoved, cfg, 'PadLen', opt.PadLen);

% (4)+(5) 解调 + 平滑
keys = {'env', 'env2', 'sqlaw', 'sq'};
for k = keys
    m = k{1};
    if ~any(strcmpi(opt.Methods, m))
        continue;
    end
    ref = [];
    extra = {};
    if strcmpi(m, 'sqlaw')
        % 以 D1^2 为参考，输出等价性诊断（供论文引用）
        [ref, ~] = pa_demodulate(D.filtered, cfg, 'env2');
        % 分析带过宽时必须先窄带化，否则 (B/2, 2f0-B/2) 为空集
        if ~cfg.sqlaw_ok
            extra = {'Narrowband', true};
        end
    end
    [y, info] = pa_demodulate(D.filtered, cfg, m, 'Ref', ref, extra{:});
    if opt.Smooth > 1
        y = movmean(y, opt.Smooth, 1);
    end
    D.(m) = y;
    D.info.(m) = info;
end

% 记录有效性
D.info.nSamples  = size(D.filtered, 1);
D.info.nChannels = size(D.filtered, 2);

end

% ------------------------------------------------------------------
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
