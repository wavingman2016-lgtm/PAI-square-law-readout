function [IMs, grid] = pa_backproject_multi(sigMap, cfg, varargin)
%PA_BACKPROJECT_MULTI  多解调方式共用一次几何计算的批量反投影
%
%   [IMs, grid] = pa_backproject_multi(sigMap, cfg, 'Name', Value, ...)
%
%   为什么需要这个函数
%     钨丝点/线图要对同一数据集出 4 路（D1 / D1^2 / D2' / D2）结果.
%     若各自调用 pa_backproject，距离矩阵与飞行时间会被重复计算 4 次.
%     本函数按通道循环一次，同时累加全部方法，约省 3/4 时间.
%
%   输入
%     sigMap : 结构体，字段名 = 方法名，值为 [nSamples x nChannels] 非负信号
%              约定字段名与 pa_preprocess 的输出字段一致：
%              'env'(D1) / 'env2'(D1^2) / 'sqlaw'(D2') / 'sq'(D2)
%     cfg    : pa_cfg 配置
%
%   可选参数
%     'Nx','FOV','Filt','TakeAbs','Normalize'   同 pa_backproject
%     'CompMap'     结构体，指定每个方法的几何补偿；
%                   默认自动：'env' -> 'r'，其余 -> 'r2'（能量域）
%     'Comp'        单一补偿，覆盖上面全部（用于消融实验）
%     'SensorPos'   [2 x nCh] 显式阵元坐标（m），覆盖 cfg 推断
%                   （外部数据集如 PATATO 的阵列形状不规则，必须显式给定）
%     'PostSquareMap' 结构体，指定每个方法是否"通道级平方后再求和"；
%                   默认全 false。若某方法设为 true，则用 Comp='r' 配平方律/包络信号
%                   也能得到能量域估计量（与 Comp='r2' 路径等价，见 pa_backproject 文件头）
%
%   输出
%     IMs  : 结构体，字段名与 sigMap 一致，值为 [Nx x Nx] 重建图
%     grid : 同 pa_backproject
%
%   版本：v1  2026-10-14

opt.Nx        = [];
opt.FOV       = [];
opt.Filt      = [];
opt.TakeAbs   = [];
opt.Normalize = 'max';
opt.CompMap   = [];
opt.Comp      = [];
opt.PostSquareMap = [];
opt.SensorPos = [];      % [2 x nCh] 显式阵元坐标（m），覆盖 cfg 推断
opt = parse_opts(opt, varargin{:});

if isempty(opt.Nx),      opt.Nx      = cfg.Nx;   end
if isempty(opt.FOV),     opt.FOV     = cfg.FOV;  end
if isempty(opt.Filt),    opt.Filt    = cfg.filt; end
if isempty(opt.TakeAbs), opt.TakeAbs = cfg.takeAbs; end

methods = fieldnames(sigMap);
assert(~isempty(methods), 'pa_backproject_multi:empty', 'sigMap 为空.');

% 自动补偿规则：相干反投影配 r，能量域配 r^2
compMap = struct();
for i = 1:numel(methods)
    m = methods{i};
    if strcmpi(m, 'env')
        compMap.(m) = 'r';
    else
        compMap.(m) = 'r2';
    end
end
if ~isempty(opt.CompMap)
    fn = fieldnames(opt.CompMap);
    for i = 1:numel(fn), compMap.(fn{i}) = opt.CompMap.(fn{i}); end
end
if ~isempty(opt.Comp)
    for i = 1:numel(methods), compMap.(methods{i}) = opt.Comp; end
end

% 自动平方规则：默认全 false（不改变既有口径）
psMap = struct();
for i = 1:numel(methods), psMap.(methods{i}) = false; end
if ~isempty(opt.PostSquareMap)
    fn = fieldnames(opt.PostSquareMap);
    for i = 1:numel(fn), psMap.(fn{i}) = logical(opt.PostSquareMap.(fn{i})); end
end

nSamples  = size(sigMap.(methods{1}), 1);
nChannels = size(sigMap.(methods{1}), 2);

% ---- 网格（行 = y 向上，列 = x 向右）----------------------------
dx = opt.FOV / (opt.Nx - 1);
qv = ((1:opt.Nx) - opt.Nx/2) * dx;
[XC, YC] = meshgrid(qv, qv);
nPix = opt.Nx * opt.Nx;

% ---- 阵元位置 ----------------------------------------------------
if isempty(opt.SensorPos)
    [sx, sy] = local_sensor_positions(cfg, nChannels);
else
    sx = opt.SensorPos(1, :);  sy = opt.SensorPos(2, :);
    assert(numel(sx) == nChannels, 'SensorPos 列数与通道数不符.');
end

% ---- 可选斜坡滤波（FBP）-----------------------------------------
Smap = struct();
if strcmpi(opt.Filt, 'ramp')
    Nfft  = 2^nextpow2(nSamples);
    fAxis = (0:Nfft-1)' * cfg.fs / Nfft;
    H     = abs(fAxis) .* hamming(Nfft);
    H     = H / (max(H) + eps);
    for i = 1:numel(methods)
        m = methods{i};
        X = sigMap.(m);
        Xf = zeros(Nfft, nChannels);
        for ch = 1:nChannels
            Xf(:, ch) = real(ifft(fft(X(:, ch), Nfft) .* H, Nfft));
        end
        Smap.(m) = Xf(1:nSamples, :);
    end
else
    Smap = sigMap;
end

% ---- 一次循环累加全部方法 ---------------------------------------
IMs = struct();
for i = 1:numel(methods), IMs.(methods{i}) = zeros(opt.Nx); end

t0 = tic;
for ch = 1:nChannels
    d   = sqrt((XC - sx(ch)).^2 + (YC - sy(ch)).^2);
    tidx  = d / cfg.vs * cfg.fs + 1;
    valid = (tidx >= 1) & (tidx <= nSamples);
    tq = tidx(:);

    wR  = (d + 1e-6) / cfg.R;
    wR2 = wR.^2;

    for i = 1:numel(methods)
        m = methods{i};
        switch lower(compMap.(m))
            case 'r',    w = wR;
            case 'r2',   w = wR2;
            case 'none', w = ones(opt.Nx);
            otherwise
                error('pa_backproject_multi:comp', '未知补偿：%s', compMap.(m));
        end
        v = interp1(1:nSamples, Smap.(m)(:, ch), tq, 'linear', 0);
        contrib = reshape(v, opt.Nx, opt.Nx) .* w .* valid;
        if psMap.(m)
            contrib = contrib .^ 2;   % 通道级平方（求和之前）
        end
        IMs.(m) = IMs.(m) + contrib;
    end

    if mod(ch, 200) == 0
        fprintf('    [bp] %d/%d 通道  (%.1f s)\n', ch, nChannels, toc(t0));
    end
end

% ---- 收尾 --------------------------------------------------------
for i = 1:numel(methods)
    m = methods{i};
    if opt.TakeAbs, IMs.(m) = abs(IMs.(m)); end
    if strcmpi(opt.Normalize, 'max')
        IMs.(m) = IMs.(m) / (max(IMs.(m)(:)) + eps);
    end
end

grid = struct('x', qv*1e3, 'y', qv*1e3, 'dx', dx*1e3, 'unit', 'mm', ...
              'comp', compMap, 'filt', opt.Filt, 'FOV', opt.FOV, ...
              'nPix', nPix);
end

% ==================================================================
function [sx, sy] = local_sensor_positions(cfg, nChannels)
N = nChannels;
if isfield(cfg, 'N') && cfg.N ~= nChannels
    warning('pa_backproject_multi:N', ...
        'cfg.N = %d 与实际通道数 %d 不符，按实际通道数重建.', cfg.N, nChannels);
end
switch lower(cfg.arrayType)
    case {'semicircle128', 'semicircle256'}
        ang = (0:N-1) * (pi/(N-1)) - pi;
    case {'rotational', 'multisegment', 'ring1024'}
        ang = (0:N-1) * (2*pi/N);
    otherwise
        error('pa_backproject_multi:array', '未知阵列类型：%s', cfg.arrayType);
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
