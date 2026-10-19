function [IM, grid] = pa_backproject(sigMat, cfg, varargin)
%PA_BACKPROJECT  统一时域反投影（DAS / FBP）
%
%   [IM, grid] = pa_backproject(sigMat, cfg, 'Name', Value, ...)
%
%   输入
%     sigMat : [nSamples x nChannels] 已解调的非负信号（来自 pa_preprocess）
%     cfg    : pa_cfg 配置
%
%   几何补偿（**本函数的关键**）：只有**一条**规则
%     g_m = d_m / R          （第 m 通道、重建点在距离 d_m 处的扩束补偿权重）
%   声压幅值量与声能量量共用这条规则，差别只在"补偿后是否再平方"：
%     · 声压幅值量（线性包络 |z|）  -> 权重 g_m          -> 'r'   【Arm C / Arm M】
%     · 声能量量（|z|^2 / 平方律）  -> 权重 g_m^2        -> 'r2'  【I_E 的 LP 实现；代码别名 direct】
%   二者逐点恒等：  sum_m g_m^2 |z_m|^2  ==  sum_m ( g_m |z_m| )^2.
%   故 'r2' 并非独立的第二条补偿律，而是**同一条 g_m 作用在平方量上**；
%   （命名口径见正文 §2.7：'r2' 配平方律信号 = **LP** 路；'r' 配 PostSquare = **EI** 路。
%    `consist` / `direct` 仅为 pa_wire_run 的 `Epath` 取值，属**代码别名**。）
%   若希望代码里"三路只有一种补偿写法"，令 PostSquare=true、Comp='r' 直接喂线性包络即可
%   （见下方 PostSquare 说明；与 'r2' 路径的差值为**总实现残差**——transition-band leakage、
%   边界处理与"插值—平方"先后三项共同承载，**未分离**，实测 ≤0.53 %（max-rel）、L2 ≤0.62 %，不是单一的"插值残差"）。
%   原脚本在 xr / 1/r / xr^2 之间混用（见 docs/01 P3），此处统一为显式选项.
%
%   可选参数
%     'Nx'         图像像素数（默认 cfg.Nx）
%     'FOV'        视场边长 (m)（默认 cfg.FOV）
%     'Comp'       几何补偿 'r' | 'r2' | 'none'（默认 cfg.comp）；推荐统一写 'r'
%     'PostSquare' 逻辑值。true 时把**单通道贡献**先平方再累加（求和之前），
%                  即 sum_m (w_m * v_m)^2。令 PostSquare=true 且 Comp='r'、
%                  输入线性包络，即得能量域估计量 I_E，且补偿写法与幅度臂完全一致。
%                  （逐点等价于 Comp='r2' + 平方律信号，见文件头说明）
%     'Filt'       时域滤波 'none' | 'ramp'（默认 cfg.filt；'ramp' = 斜坡xHamming）
%     'TakeAbs'    反投影后是否取绝对值（默认 cfg.takeAbs）
%     'Normalize'  'max'（默认，归一到 [0,1]）| 'none'
%     'SensorPos'  [2 x nCh] 显式阵元坐标（m），覆盖 cfg 推断
%
%   输出
%     IM     : [Ny x Nx]，行 = y（向上为正），列 = x（向右为正）
%     grid   : 结构体 {x, y, dx, unit, comp, filt}
%
%   版本：v2  2026-10-14（改用 cfg.FOV/Nx；方位约定改为自然图像约定）

opt.Nx        = [];
opt.FOV       = [];
opt.Comp      = [];
opt.PostSquare = false;   % true: 单通道贡献先平方再累加（通道级平方，非图像域）
opt.Filt      = [];
opt.TakeAbs   = [];
opt.Normalize = 'max';
opt.SensorPos = [];
opt = parse_opts(opt, varargin{:});

if isempty(opt.Nx),      opt.Nx      = cfg.Nx;    end
if isempty(opt.FOV),     opt.FOV     = cfg.FOV;   end
if isempty(opt.Comp),    opt.Comp    = cfg.comp;  end
if isempty(opt.Filt),    opt.Filt    = cfg.filt;  end
if isempty(opt.TakeAbs), opt.TakeAbs = cfg.takeAbs; end

nSamples  = size(sigMat, 1);
nChannels = size(sigMat, 2);

% ---- 坐标网格（行 = y 向上，列 = x 向右）-------------------------
dx = opt.FOV / (opt.Nx - 1);
qv = ((1:opt.Nx) - opt.Nx/2) * dx;         % -FOV/2 .. +FOV/2
[XC, YC] = meshgrid(qv, qv);               % XC 沿列变化，YC 沿行变化

% ---- 阵元位置 ----------------------------------------------------
if isempty(opt.SensorPos)
    [sx, sy] = local_sensor_positions(cfg, nChannels);
else
    sx = opt.SensorPos(1, :);  sy = opt.SensorPos(2, :);
    assert(numel(sx) == nChannels, 'SensorPos 列数与通道数不符.');
end

% ---- 可选：时域斜坡滤波（FBP）----------------------------------
S = sigMat;
if strcmpi(opt.Filt, 'ramp')
    Nfft  = 2^nextpow2(nSamples);
    fAxis = (0:Nfft-1)' * cfg.fs / Nfft;
    H     = abs(fAxis) .* hamming(Nfft);
    H     = H / (max(H) + eps);
    Sf    = zeros(Nfft, nChannels);
    for ch = 1:nChannels
        sf = fft(sigMat(:, ch), Nfft);
        Sf(:, ch) = real(ifft(sf .* H, Nfft));
    end
    S = Sf(1:nSamples, :);
end

% ---- 反投影 ------------------------------------------------------
IM = zeros(opt.Nx, opt.Nx);

for ch = 1:nChannels
    d = sqrt((XC - sx(ch)).^2 + (YC - sy(ch)).^2);

    % 飞行时间 -> 采样索引（+1 因 MATLAB 从 1 开始）
    tidx  = d / cfg.vs * cfg.fs + 1;
    valid = (tidx >= 1) & (tidx <= nSamples);

    vals = interp1(1:nSamples, S(:, ch), tidx(:), 'linear', 0);
    vals = reshape(vals, opt.Nx, opt.Nx);

    switch lower(opt.Comp)
        case 'r',    w = (d + 1e-6) / cfg.R;
        case 'r2',   w = ((d + 1e-6) / cfg.R).^2;
        case 'none', w = ones(size(d));
        otherwise
            error('pa_backproject:comp', '未知补偿方式：%s', opt.Comp);
    end

    contrib = vals .* w .* valid;
    if opt.PostSquare
        contrib = contrib .^ 2;    % 通道级平方（通道求和之前）；与图像域平方 I_M^2 不同
    end
    IM = IM + contrib;
end

if opt.TakeAbs
    IM = abs(IM);
end

if strcmpi(opt.Normalize, 'max')
    IM = IM / (max(IM(:)) + eps);
end

grid = struct('x', qv*1e3, 'y', qv*1e3, 'dx', dx*1e3, 'unit', 'mm', ...
              'comp', opt.Comp, 'filt', opt.Filt, 'FOV', opt.FOV);

end

% ==================================================================
function [sx, sy] = local_sensor_positions(cfg, nChannels)
% 方位约定与原脚本逐行一致：
%   半环阵  Fhb_code.m L58 / PAI_FBP_1_V2.m L~138:
%       angle = ch*step - pi, step = pi/(N-1)  -> ch=1..N 对应 -pi .. 0
%   旋转阵  单探测器绕旋转中心一周：angle = (k-1)*2*pi/N
N = nChannels;
if isfield(cfg, 'N') && cfg.N ~= nChannels
    warning('pa_backproject:N', ...
        'cfg.N = %d 与实际通道数 %d 不符，按实际通道数重建.', cfg.N, nChannels);
end

switch lower(cfg.arrayType)
    case {'semicircle128', 'semicircle256'}
        ang = (0:N-1) * (pi/(N-1)) - pi;     % -pi .. 0（下半圆）
    case {'rotational', 'multisegment', 'ring1024'}
        ang = (0:N-1) * (2*pi/N);
    otherwise
        error('pa_backproject:array', '未知阵列类型：%s', cfg.arrayType);
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
