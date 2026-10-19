function [IC, grid] = pa_backproject_coherent(sigMat, cfg, varargin)
%PA_BACKPROJECT_COHERENT  相干（解析信号）延时叠加反投影 —— 教科书 DAS/FBP（Arm C）
%
%   [IC, grid] = pa_backproject_coherent(sigMat, cfg, 'Name', Value, ...)
%
%   与 pa_backproject 的**唯一差别**
%     pa_backproject           ：待反投影量是**实、非负**的量（线性包络 / 平方律），
%                                逐通道**非相干**累加             → Arm M / Arm E
%     本函数                    ：待反投影量是**解析信号本身**（复数），
%                                逐通道延时取样后在**复数域**累加、最后取模
%                                       I_C(r) = | sum_m w_m * z_m( tau_m(r) ) |
%                                → **Arm C**，即 k-space / 通用反投影(UBP)的时域口径，
%                                  也是"主流 = Hilbert + 滤波反投影"的实现。
%
%   为什么必须把它单列（不可用包络叠加代替）
%     z_m(tau_m) 携带载波相位 e^{i 2π f0 Δτ_m}：在真目标处同相叠加、偏离处相消，
%     形成**相干积累**，横向分辨率可达 λ/2。包络叠加丢弃了该相位，分辨率差约 5 倍。
%     本项目历史上误把"包络叠加"当主流基线，导致对照过易 —— 详见 docs/09 §1.5。
%
%   输入
%     sigMat : [nSamples x nChannels]
%                · 实数 -> 内部逐通道做 hilbert 取解析信号（"前处理后补 Hilbert"口径）
%                · 复数 -> 直接使用（调用方已算好，避免重复 Hilbert）
%     cfg    : pa_cfg 配置（几何、vs、fs、R 与 pa_backproject 共用）
%
%   几何补偿（与 pa_backproject 同约定，**必须与估计量匹配**）
%     |I_C| 为声压幅值量 -> 默认 'r'（权重 d/R）。
%     ⚠️ 不要用 'r2'：那属能量域估计量。（该规则是 docs/01 P3 的教训）
%
%   可选参数（与 pa_backproject 完全一致）
%     'Nx' 'FOV' 'Comp' 'Filt' 'TakeAbs' 'Normalize' 'SensorPos'
%     另加 'Hilbert' ：true/false，默认按输入是否为复数自动判定
%
%   输出
%     IC   : [Ny x Nx] 非负实矩阵（|sum|），行 = y（向上为正），列 = x（向右为正）
%     grid : 与 pa_backproject 同结构
%
%   版本：v1  2026-10-14

opt.Nx        = [];
opt.FOV       = [];
opt.Comp      = [];
opt.Filt      = [];
opt.TakeAbs   = [];      % 本函数最后必然取模；此参数保留以兼容签名（取模后仍为正值）
opt.Normalize = 'max';
opt.SensorPos = [];
opt.Hilbert   = [];
opt = parse_opts(opt, varargin{:});

if isempty(opt.Nx),      opt.Nx      = cfg.Nx;    end
if isempty(opt.FOV),     opt.FOV     = cfg.FOV;   end
if isempty(opt.Comp),    opt.Comp    = 'r';       end   % 默认与估计量匹配
if isempty(opt.Filt),    opt.Filt    = cfg.filt;  end
if isempty(opt.Hilbert), opt.Hilbert = isreal(sigMat);  end
% 注意方向：**输入是实信号时才需要补 Hilbert**；若调用方已传入解析信号（复数），
% 直接使用。写成 ~isreal 会让复数输入再被 hilbert 一次（虚部被丢弃并告警）。
% 该错误在 real(hilbert(x))==x 的意义下数值上幂等，但会重复计算且掩盖真实误用。

nSamples  = size(sigMat, 1);
nChannels = size(sigMat, 2);

% ---- 取解析信号 --------------------------------------------------
if opt.Hilbert
    Z = complex(zeros(nSamples, nChannels));
    for ch = 1:nChannels
        Z(:, ch) = hilbert(double(sigMat(:, ch)));
    end
else
    Z = double(sigMat);
end

% ---- 坐标网格（行 = y 向上，列 = x 向右；与 pa_backproject 逐行一致）----
dx = opt.FOV / (opt.Nx - 1);
qv = ((1:opt.Nx) - opt.Nx/2) * dx;
[XC, YC] = meshgrid(qv, qv);

% ---- 阵元位置 ----------------------------------------------------
if isempty(opt.SensorPos)
    [sx, sy] = local_sensor_positions(cfg, nChannels);
else
    sx = opt.SensorPos(1, :);  sy = opt.SensorPos(2, :);
    assert(numel(sx) == nChannels, 'SensorPos 列数与通道数不符.');
end

% ---- 可选：时域斜坡滤波（FBP）----------------------------------
% 注意：解析信号的斜坡滤波需同时作用于实部与虚部，故直接在 Z 上做同一滤波。
if strcmpi(opt.Filt, 'ramp')
    Nfft  = 2^nextpow2(nSamples);
    fAxis = (0:Nfft-1)' * cfg.fs / Nfft;
    H     = abs(fAxis) .* hamming(Nfft);
    H     = H / (max(H) + eps);
    Zf    = zeros(Nfft, nChannels);
    for ch = 1:nChannels
        zf = fft(Z(:, ch), Nfft);
        Zf(:, ch) = ifft(zf .* H, Nfft);        % 保留复数
    end
    Z = Zf(1:nSamples, :);
end

% ---- 相干反投影 --------------------------------------------------
switch lower(opt.Comp)
    case 'r',    compMode = 1;
    case 'r2',   compMode = 2;
    case 'none', compMode = 0;
    otherwise,   error('pa_backproject_coherent:comp', '未知补偿方式：%s', opt.Comp);
end

ACC = complex(zeros(opt.Nx, opt.Nx));
for ch = 1:nChannels
    d = sqrt((XC - sx(ch)).^2 + (YC - sy(ch)).^2);
    tidx  = d / cfg.vs * cfg.fs + 1;
    valid = (tidx >= 1) & (tidx <= nSamples);

    vr = interp1(1:nSamples, real(Z(:, ch)), tidx(:), 'linear', 0);
    vi = interp1(1:nSamples, imag(Z(:, ch)), tidx(:), 'linear', 0);
    v  = reshape(vr + 1i*vi, opt.Nx, opt.Nx);

    switch compMode
        case 1,  w = (d + 1e-6) / cfg.R;
        case 2,  w = ((d + 1e-6) / cfg.R).^2;
        otherwise, w = ones(size(d));
    end

    ACC = ACC + v .* w .* valid;      % ← 复数域累加（相干）
end

IC = abs(ACC);                        % ← 求和后取模

if strcmpi(opt.Normalize, 'max')
    IC = IC / (max(IC(:)) + eps);
end

grid = struct('x', qv*1e3, 'y', qv*1e3, 'dx', dx*1e3, 'unit', 'mm', ...
              'comp', opt.Comp, 'filt', opt.Filt, 'FOV', opt.FOV);

end

% ==================================================================
function [sx, sy] = local_sensor_positions(cfg, nChannels)
% 与 pa_backproject.local_sensor_positions 逐行一致（半环 -pi..0；环/旋转 0..2pi）
N = nChannels;
if isfield(cfg, 'N') && cfg.N ~= nChannels
    warning('pa_backproject_coherent:N', ...
        'cfg.N = %d 与实际通道数 %d 不符，按实际通道数重建.', cfg.N, nChannels);
end
switch lower(cfg.arrayType)
    case {'semicircle128', 'semicircle256'}
        ang = (0:N-1) * (pi/(N-1)) - pi;
    case {'rotational', 'multisegment', 'ring1024'}
        ang = (0:N-1) * (2*pi/N);
    otherwise
        error('pa_backproject_coherent:array', '未知阵列类型：%s', cfg.arrayType);
end
sx = cfg.R * cos(ang);
sy = cfg.R * sin(ang);
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
