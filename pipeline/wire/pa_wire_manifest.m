function M = pa_wire_manifest(varargin)
%PA_WIRE_MANIFEST  钨丝点/线图的数据集清单（**本轮"提取并整理"的核心产物之一**）
%
%   M = pa_wire_manifest()
%   M = pa_wire_manifest('Root', '<repo root>')
%
%   返回结构体数组，每个元素描述一张待产出的钨丝点/线图及其数据来源。
%   字段
%     id       短标识（用于文件名前缀）
%     cfgName  pa_cfg 的数据源标识
%     dataDir  数据目录（绝对或相对 Root）
%     kind     'point' 点状（横断面）/ 'line' 线状（纵断面）/ 'ring' 环形
%     desc     中文描述
%     figure   对应论文草图里的图号
%     outSub   相对 results/wire 的输出子目录名
%     notes    需要提醒的处理要点
%     F0        【经验证配置】**实测带中心**(Hz)，覆盖 cfg 标称 f0；[] = 用标称值
%     FOV       【经验证配置】成像视场边长(m)，覆盖 cfg.FOV；   [] = 用 cfg 默认
%     Nx        【经验证配置】图像像素数，覆盖调用方的 Nx；      [] = 用调用方默认
%
%   ⚠ 为什么清单里要带"经验证配置"
%     6 组数据的**采集装置标称频率**(cfg.f0=5 MHz)对其中 3 组并不成立：
%     data6 实测带中心 1.16 MHz、data3 2.00 MHz、data5 0.35 MHz。按标称值跑，
%     带通会把真信号整段滤掉，结论被误判为"该方法无增益"——那是**配置错误**，
%     不是方法失效（详见 results/registry/README.md 的"反例"节）。
%     故把**逐组的经验证配置**写进清单，作为唯一事实源；`pa_run_wire_all`
%     据此逐组覆盖，避免"一处默认值管全部"的系统性错误。
%     ⚠ data4 另有视场问题：FOV=40 mm 会截断目标(Q4)，须放到 60 mm 并加密网格。
%
%   ⚠ 构型判定依据（逐图核验归档结果，非推测）
%     data1 → image1/Figure_1_Comparison_V3.png   单根细钨丝，图心处单亮点 → 点图
%     data2 → image3/PAI_Figure1_ImageComparison.png 两个并排亮点 → 双点图
%     data4 → image4/PAI_Figure1_LinearVsEnergy.png  两根交叉长丝（X 形）→ **线图**
%             且该图正是"裸平方 D2 失败"的实例：线性图能看到两根丝，
%             裸平方图里两根丝几乎消失、只剩弧形伪影 → 必须单列为缺陷对照
%     data6 → image7/DAS_Detector_Fig1_LinearVsSquared.png 两根不同深度丝（V 形）→ **线图**
%     data5 → image5/PAI_DAS_EXCEL_Figure1_ImageComparison.png 环形/管状仿体 → 补充组
%     data3 → 无归档结果（200 步旋转，r=16.02 mm）→ 待判定，列在最后
%
%   版本：v1  2026-10-14

opt.Root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
opt = parse_opts(opt, varargin{:});

R = opt.Root;

M = struct('id', {}, 'cfgName', {}, 'dataDir', {}, 'kind', {}, ...
           'desc', {}, 'figure', {}, 'outSub', {}, 'notes', {}, ...
           'F0', {}, 'FOV', {}, 'Nx', {});

M(end+1) = mk('W1', 'own1', fullfile(R,'data1'), 'point', ...
    '单根细长钨丝的横断面（点状吸收体）', '图3.1 / 3.2', 'W1_single', ...
    '点图主样本；PSF 由横断面剖面给出', []);

M(end+1) = mk('W2', 'own2', fullfile(R,'data2'), 'point', ...
    '两根并排细长钨丝的横断面（双点）', '图4.1 / 4.2', 'W2_double', ...
    '双点图；可用于双点 Rayleigh 可分辨性判据', []);

M(end+1) = mk('W3', 'own4', fullfile(R,'data4'), 'line', ...
    '两根交叉细长钨丝（X 形，丝在成像平面内）', '补充 / 缺陷对照', 'W3_cross', ...
    '⚠ 裸平方 D2 在本样本上失败（两根丝几乎消失），是"必须先低通"的直接证据', ...
    ovr('FOV', 60e-3, 'Nx', 1501));   % 40 mm 视场会截断目标 → 放大到 60 mm

M(end+1) = mk('W4', 'own6', fullfile(R,'data6'), 'line', ...
    '两根不同深度的细钨丝（V 形，r=54.28 mm 旋转扫描）', '图5.1 / 5.2', 'W4_depth', ...
    '线图主样本；深度方向像素消失现象在此复核', ...
    ovr('F0', 1.16e6));               % 实测带中心（标称 5 MHz 会把信号滤掉）

M(end+1) = mk('W5', 'own5', fullfile(R,'data5'), 'ring', ...
    '环形/管状仿体（r=17.49 mm 旋转扫描）', '补充组', 'W5_ring', ...
    '与 W4 半径差 3.1 倍，属两套装置；成像区同为 18 mm', ...
    ovr('F0', 0.35e6));               % 实测带中心

M(end+1) = mk('W6', 'own3', fullfile(R,'data3'), 'unknown', ...
    '旋转 200 步数据（r=16.02 mm，无归档结果）', '待判定', 'W6_rot200', ...
    '首次运行后据图像判定构型；原脚本 PAI_FBP_3.m / rec_code_fu.m 无输出归档', ...
    ovr('F0', 2.00e6));               % 实测带中心

end

% ==================================================================
function s = mk(id, cfgName, dataDir, kind, desc, figure, outSub, notes, o)
if nargin < 9 || isempty(o), o = struct([]); end
s = struct('id', id, 'cfgName', cfgName, 'dataDir', dataDir, 'kind', kind, ...
           'desc', desc, 'figure', figure, 'outSub', outSub, 'notes', notes, ...
           'F0', ovr_get(o,'F0'), 'FOV', ovr_get(o,'FOV'), 'Nx', ovr_get(o,'Nx'));
end

% ==================================================================
function o = ovr(varargin)
%OVR  构造"经验证配置覆盖"结构体（只含给定字段）
o = struct(varargin{:});
end

% ==================================================================
function v = ovr_get(o, k)
if isempty(o) || ~isfield(o, k), v = []; else, v = o.(k); end
end

% ==================================================================
function o = parse_opts(o, varargin)
if mod(numel(varargin), 2) ~= 0
    error('parse_opts:pair', '参数必须成对出现。');
end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o, k), error('parse_opts:unknown', '未知参数：%s', k); end
    o.(k) = varargin{i+1};
end
end
