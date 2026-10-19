function [sigMat, meta] = pa_load_signals(srcDir, cfg, varargin)
%PA_LOAD_SIGNALS  统一信号读取入口（替换各脚本里散落的 load / trans_data_128）
%
%   [sigMat, meta] = pa_load_signals(srcDir, cfg, 'Name', Value, ...)
%
%   返回
%     sigMat : [nSamples x nChannels] 双精度矩阵（多帧时已按帧平均）
%     meta   : 结构体 {nSamples, nChannels, nFrames, fs, fileList, rawClass}
%
%   可选参数
%     'MaxFrames'   最多读取的帧/角数（默认 Inf）
%     'FrameAvg'    多帧是否平均（默认 true）
%     'Stride'      旋转扫描抽角步长（默认 1）
%     'H5Key'       HDF5 数据集键名（给定时走 HDF5 分支）
%     'H5WL'        HDF5 4D 数据的波长索引（默认 1；PATATO 有 10 个波长）
%     'Verbose'     打印进度（默认 true）
%
%   支持的数据形态（均为实测确认）
%     (1) .dat   128 通道交织 int16（自有半环阵 data1/data2/data4）
%               ---- 交织约定已逐行核对 trans_data_128.m，等价于
%                  reshape(raw,128,N).'
%     (2) ".xlsx" 旋转扫描：**实为制表符分隔的纯文本**（实测 data3/5/6 均为
%               单行 tab 分隔浮点数），每文件 = 单角度单通道时序.
%               ! 不能用 load / readmatrix（会按真正的 XLSX 解析而失败），
%                 本函数用 fileread + sscanf 稳健解析.
%     (3) .h5    OADAT HDF5（键名由 'H5Key' 指定）
%
%   版本：v2  2026-10-14（修复 ".xlsx" 实为纯文本的读取陷阱）

opt.MaxFrames = Inf;
opt.FrameAvg  = true;
opt.Stride    = 1;
opt.H5Key     = '';
opt.H5WL      = 1;
opt.Verbose   = true;
opt = parse_opts(opt, varargin{:});

meta = struct('nSamples', [], 'nChannels', [], 'nFrames', 1, ...
              'fs', cfg.fs, 'fileList', {{}}, 'rawClass', '', 'srcDir', srcDir, ...
              'sensorPos', []);

if ~exist(srcDir, 'dir') && isempty(opt.H5Key)
    error('pa_load_signals:noDir', '数据目录不存在：%s', srcDir);
end

% ------------------------------------------------------------------
% 分支 1：OADAT HDF5
% ------------------------------------------------------------------
if ~isempty(opt.H5Key)
    h5file = srcDir;
    if exist(srcDir, 'dir')
        d = dir(fullfile(srcDir, '*.h5'));
        if isempty(d)
            error('pa_load_signals:noH5File', '%s 下无 .h5 文件.', srcDir);
        end
        h5file = fullfile(srcDir, d(1).name);
    end
    h5key = opt.H5Key;
    if h5key(1) ~= '/', h5key = ['/' h5key]; end   % h5read 要求以 '/' 开头
    raw = double(h5read(h5file, h5key));
    if ndims(raw) == 4
        % ---- PATATO 型 4D：HDF5 [nFrames, nWL, nCh, nS]
        %      MATLAB h5read 反转维度 -> [nS, nCh, nWL, nFrames]
        wl  = min(max(1, round(opt.H5WL)), size(raw, 3));
        sub = raw(:, :, wl, :);
        sub = reshape(sub, size(sub, 1), size(sub, 2), []);   % [nS, nCh, nFrames]
        if opt.FrameAvg
            sigMat = mean(sub, 3);
        else
            sigMat = sub(:, :, 1);
        end
        meta.rawClass = 'patato-h5-4d';
        if opt.Verbose
            if opt.FrameAvg, sAvg = '帧平均'; else, sAvg = '取首帧'; end
            fprintf('  [load] PATATO 4D：波长 #%d/%d，%s（%d 帧）-> %d 采样 x %d 通道\n', ...
                wl, size(raw, 3), sAvg, size(sub, 3), size(sigMat, 1), size(sigMat, 2));
        end
    elseif ndims(raw) == 3
        % OADAT 约定：[channel, sample, frame] -> [sample, channel]
        sigMat = squash_frames(raw);
        meta.rawClass = 'oadat-h5';
    else
        if size(raw, 1) < size(raw, 2), raw = raw.'; end
        sigMat = raw;
        meta.rawClass = 'h5-2d';
    end

    % ---- 可选：读出阵元坐标（PATATO 的 GEOMETRY；形状不规则，必须显式给定）----
    try
        G   = double(h5read(h5file, '/GEOMETRY'));
        nCh = size(sigMat, 2);
        if size(G, 2) == nCh && size(G, 1) >= 2 && size(G, 1) <= 4
            meta.sensorPos = G(1:2, :);          % (2 x nCh)
        elseif size(G, 1) == nCh && size(G, 2) >= 2 && size(G, 2) <= 4
            meta.sensorPos = G(:, 1:2).';        % (2 x nCh)
        end
        if opt.Verbose && ~isempty(meta.sensorPos)
            fprintf('  [load] 已读取 GEOMETRY -> SensorPos (2 x %d)\n', nCh);
        end
    catch
        % 无 GEOMETRY：沿用 cfg 推断的阵列几何
    end

    meta.nSamples  = size(sigMat, 1);
    meta.nChannels = size(sigMat, 2);
    meta.fileList  = {h5file};
    return;
end

% ------------------------------------------------------------------
% 分支 2：自有 .dat（128 通道交织 int16）
% ------------------------------------------------------------------
dats = dir(fullfile(srcDir, '*.dat'));
if ~isempty(dats)
    names = sort_nat_safe({dats.name});
    use   = 1:min(numel(names), opt.MaxFrames);
    acc = []; nUsed = 0;
    for i = use
        d = read_dat128(fullfile(srcDir, names{i}));
        if isempty(acc), acc = zeros(size(d)); end
        if isequal(size(d), size(acc))
            acc = acc + d;  nUsed = nUsed + 1;
        end
    end
    if opt.FrameAvg && nUsed > 0
        sigMat = acc / nUsed;
    else
        sigMat = acc;
    end
    meta.rawClass  = 'dat128';
    meta.nFrames   = nUsed;
    meta.nSamples  = size(sigMat, 1);
    meta.nChannels = size(sigMat, 2);
    meta.fileList  = names(use);
    if opt.Verbose
        fprintf('  [load] .dat x %d 帧平均 -> %d 采样 x %d 通道\n', ...
            nUsed, meta.nSamples, meta.nChannels);
    end
    return;
end

% ------------------------------------------------------------------
% 分支 3：自有旋转扫描（".xlsx" 实为 tab 分隔纯文本）
% ------------------------------------------------------------------
xls = dir(fullfile(srcDir, '*.xlsx'));
if ~isempty(xls)
    names = sort_nat_safe({xls.name});
    idx   = 1:opt.Stride:min(numel(names), opt.MaxFrames);

    firstV = local_load_ascii(fullfile(srcDir, names{idx(1)}));
    nS = numel(firstV);
    sigMat = zeros(nS, numel(idx));
    for k = 1:numel(idx)
        v = local_load_ascii(fullfile(srcDir, names{idx(k)}));
        if numel(v) ~= nS
            v = v(1:min(numel(v), nS));
            if numel(v) < nS, v(end+1:nS) = 0; end
        end
        sigMat(:, k) = v(:);
    end
    meta.rawClass  = 'xlsx-rotational';
    meta.nFrames   = 1;
    meta.nSamples  = nS;
    meta.nChannels = numel(idx);
    meta.fileList  = names(idx);
    if opt.Verbose
        fprintf('  [load] 旋转扫描 x %d 角度 (stride %d) -> %d 采样 x %d 通道\n', ...
            numel(idx), opt.Stride, meta.nSamples, meta.nChannels);
    end
    return;
end

error('pa_load_signals:noData', '在 %s 下未找到 .dat / .xlsx / .h5 数据.', srcDir);
end

% ==================================================================
function data = read_dat128(fpath)
% 128 通道交织 int16.交织顺序与 trans_data_128.m 逐行核对等价：
%   reshape(raw, 128, dotNum).'
fid = fopen(fpath, 'rb');
if fid < 0, error('read_dat128:open', '无法打开：%s', fpath); end
raw = fread(fid, inf, 'int16');
fclose(fid);

if mod(numel(raw), 128) ~= 0
    warning('read_dat128:len', '%s 长度 %d 非 128 整数倍，已截断.', ...
        fpath, numel(raw));
    raw = raw(1:floor(numel(raw)/128)*128);
end
dotNum = numel(raw) / 128;
data = double(reshape(raw, 128, dotNum).');
end

% ==================================================================
function v = local_load_ascii(fpath)
% 实测：这些 ".xlsx" 是单行 tab 分隔的浮点文本.
% sscanf('%f') 自动跳过空白（空格/制表/换行），最稳健.
txt = fileread(fpath);
v = sscanf(txt, '%f');
if isempty(v)
    % 兜底：万一真的是 XLSX 二进制
    try
        v = readmatrix(fpath);
        v = v(:);
    catch
        error('local_load_ascii:fail', '无法解析：%s', fpath);
    end
end
end

% ==================================================================
function names = sort_nat_safe(names)
try
    names = sort_nat(names);
catch
    % 无 sort_nat 时的自然序兜底：按数字后缀排序
    k = zeros(numel(names), 1);
    for i = 1:numel(names)
        t = regexprep(names{i}, '\D', ' ');
        n = sscanf(t, '%d');
        if isempty(n), k(i) = NaN; else, k(i) = n(end); end
    end
    [~, ord] = sort(k);
    names = names(ord);
end
end

% ==================================================================
function out = squash_frames(raw)
s = size(raw);
out = zeros(s(2), s(1));
nf = min(s(3), 200);
for f = 1:nf
    out = out + squeeze(raw(:, :, f)).';
end
out = out / nf;
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
