function [y, info] = pa_demodulate(x, cfg, method, varargin)
%PA_DEMODULATE  解调（预处理链第 3 步）：把射频信号转成成像用的非负包络量
%
%   [y, info] = pa_demodulate(x, cfg, method, 'Name', Value, ...)
%
%   输入
%     x      : [nSamples x nChannels] **已完成去 DC + 带通**的信号
%     cfg    : pa_cfg 返回的配置（用于 fs / f0 / sqlaw 判据）
%     method : 'env'    D1  = |hilbert(x)|            线性包络（论文基线 I_C）
%              'env2'   D1^2 = |hilbert(x)|.^2         包络平方（现有主方法）
%              'sqlaw'  D2' = LPF(x.^2)               平方律检波（免 Hilbert）
%              'sq'     D2  = x.^2                    裸平方（**仅作缺陷对照**）
%
%   为什么 'sqlaw' 才是"免 Hilbert 的信号平方"
%     对窄带信号 x(t)=a(t)cos(2*pi*f0*t)，有恒等式
%         x^2(t) = a^2/2 + (a^2/2)cos(4*pi*f0*t) = 1/2|z(t)|^2 + 2f0 分量
%     用一个截止落在 (f_high-f_low, 2*f_low) 内的低通滤掉 2f0 分量，即得
%         LPF(x^2) = 1/2|z(t)|^2 = 1/2 D1^2
%     故 D2' 与 D1^2 只差一个常数因子 2，**无需 Hilbert 变换**.
%     受控仿真实测该等价性 Pearson > 0.998（见 docs/04 #3）.
%
%   ! 裸平方 'sq' 为什么必须作为反例单列
%     x^2 含不可分离的 2f0 项，主峰会被劈成双峰,过零点处出现伪暗带，
%     这正是 PAI_FBP_4.m / image4（双钨丝）图像退化的机制.
%     ---- 'sq' 只用于在论文里"证明不带低通的平方是错的".
%
%   可选参数
%     'LP'          低通截止 (Hz)，默认 cfg.lp_cutoff（= f0）
%     'LPOrder'     低通阶数（默认 4）
%     'Narrowband'  是否先窄带化到 cfg.sqlaw_narrowband（默认 false）
%     'Ref'         参考信号（如 D1^2），用于输出一致性诊断
%
%   输出
%     y      : 解调结果 [nSamples x nChannels]，非负
%     info   : 结构体，含 beta / 等价性诊断
%
%   版本：v1  2026-10-14

% ---- 选项 --------------------------------------------------------
opt.LP         = [];
opt.LPOrder    = 6;
opt.Narrowband = false;
opt.Ref        = [];
opt = parse_opts(opt, varargin{:});

if isempty(opt.LP), opt.LP = cfg.lp_cutoff; end

info = struct('method', method, 'beta', (cfg.f_high - cfg.f_low)/cfg.f0, ...
              'lp_cutoff', opt.LP, 'sqlaw_ok', cfg.sqlaw_ok, ...
              'pearson_vs_ref', NaN, 'amp_ratio_vs_ref', NaN);

% ---- 平移到非负 --------------------------------------------------
switch lower(method)

    case 'env'                                   % D1：线性包络
        y = abs(hilbert(x));

    case 'env2'                                  % D1^2：包络平方
        e = abs(hilbert(x));
        y = e.^2;

    case 'sqlaw'                                 % D2'：平方 + 低通
        xw = x;
        if opt.Narrowband && ~cfg.sqlaw_ok
            % 宽带信号（beta>=1）必须先窄带化，否则 (f_high-f_low, 2*f_low) 为空集
            xw = pa_bandpass(x, cfg, 'LowCut',  cfg.sqlaw_narrowband(1), ...
                                      'HighCut', cfg.sqlaw_narrowband(2));
            info.narrowbanded = true;
        else
            info.narrowbanded = false;
        end

        xs = xw.^2;

        % 零相位低通：滤除 2f0 分量，保留包络
        wn = opt.LP / (cfg.fs/2);
        if wn >= 1
            error('pa_demodulate:lp', ...
                '低通截止 %.3g Hz 超过 Nyquist（%.3g Hz）.', opt.LP, cfg.fs/2);
        end
        [bl, al] = butter(opt.LPOrder, wn, 'low');
        y = filtfilt(bl, al, xs);
        y = max(y, 0);                           % 理论上非负，数值上兜底

    case 'sq'                                    % D2：裸平方（反例）
        y = x.^2;

    otherwise
        error('pa_demodulate:method', '未知解调方式：%s', method);
end

% ---- 一致性诊断（用于论文里证明 D2'~=D1^2 而 D2!=D1^2）------------
if ~isempty(opt.Ref)
    a1 = y(:);   a2 = opt.Ref(:);
    if numel(a1) == numel(a2) && std(a1) > 0 && std(a2) > 0
        c = corrcoef(a1, a2);
        info.pearson_vs_ref = c(1, 2);
        m1 = mean(a1);  m2 = mean(a2);
        if m2 > 0
            info.amp_ratio_vs_ref = m1 / m2;
        end
    end
end

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
