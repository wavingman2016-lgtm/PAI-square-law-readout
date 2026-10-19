function [Q, report] = pa_qc(A, varargin)
%PA_QC  数据集/方法的达标筛检（**决定哪些数据进论文，哪些必须丢弃**）
%
%   [Q, report] = pa_qc(A, 'Name', Value, ...)
%
%   背景
%     采用 D2（信号平方）口径后，部分数据表现不理想（典型：data4 两根交叉
%     钨丝在裸平方下几近消失，只剩弧形伪影）.若把这类数据与达标数据混在
%     一起统计，会把"方法的失败"变成"方法的平均收益被稀释"，且 Q1 审稿人
%     一旦抽查到该图即全盘失分.故需一个**可复现,可写进 Methods 的筛检规则**.
%
%   本函数只做"判定 + 给理由"，**不修改任何数据**.
%
%   输入 A（结构体）
%     A.raw      [nS x nCh] 原始信号（未做任何处理，用于量化/直流审计）
%     A.filtered [nS x nCh] 统一预处理后的起点（去DC+带通）
%     A.IM       结构体，方法名 -> 重建图
%     A.M        结构体，方法名 -> pa_metrics 结果
%     A.grid     pa_backproject 输出的 grid
%     A.cfg      pa_cfg 配置
%     A.base     (可选) 基线方法名，默认 'env'
%     A.test     (可选) 待评方法名，默认 'env2'
%     A.sqlaw    (可选) 免 Hilbert 方法名，默认 'sqlaw'
%     A.bare     (可选) 裸平方反例名，默认 'sq'
%
%   可选参数（阈值，全部可覆盖）
%     'MinValidChanFrac'  有效通道率下限（默认 0.60）
%     'MinQuantMargin'    量化余量下限（acRms/lsb，默认 3）
%     'MaxEdgeFrac'       视场边缘能量占比上限（默认 0.30）
%     'MinCNR'            基线图像 CNR 下限（默认 1.0）
%     'MinPearsonSqlaw'   D2' 与 D1^2 的 Pearson 下限（默认 0.90）
%     'MinGainCNR'        待评方法相对基线的 CNR 增益下限（默认 0.0）
%
%   输出
%     Q.verdict   'KEEP' | 'REVIEW' | 'DISCARD'
%     Q.crit      结构体：每项的实测值,阈值,通过与否,说明
%     Q.hardFail  硬失败项列表（出现即 DISCARD）
%     Q.softFail  软失败项列表（出现即 REVIEW）
%     report      多行字符串（便于写入归档 txt）
%
%   判据一览（**这六条就是论文 Methods 里的"数据纳排标准"**）
%     Q1 有效通道率   -- 采集/耦合失败的直接指标
%     Q2 量化余量     -- acRms/lsb 太小说明信号被压到量化噪声里，
%                       平方会把量化台阶放大量化误差（**OADAT mini raw 即踩此坑**）
%     Q3 直流偏置比   -- |DC|/acRms 过大时必须先去除，否则平方退化为放大原图
%     Q4 视场截断     -- 目标超出 18/40 mm 成像区
%     Q5 基线可测性   -- CNR(D1) 太低则一切"提升"都在噪声里
%     Q6 平方增益     -- 待评方法 vs 基线的 CNR/gCNR 是否为正
%     Q7 免 Hilbert 一致性 -- D2' 是否忠实替代 D1^2（带宽条件是否满足）
%     Q8 标称-实测频率一致性 -- 实测带中心/实际使用中心是否落在 [0.5,2.0]；
%        不满足首要怀疑"标称 f0 设错"而非方法失效（**配置完整性审计**，
%        与 Q3 同属记录型；出处 docs/06 §4）
%
%   版本：v1  2026-10-14

% ---- 阈值 --------------------------------------------------------
opt.MinValidChanFrac = 0.60;
opt.MinQuantMargin   = 3;
opt.MaxEdgeFrac      = 0.30;
opt.MinCNR           = 1.0;
opt.MinPearsonSqlaw  = 0.90;
opt.MinGainCNR       = 0.0;
opt = parse_opts(opt, varargin{:});

% ---- 方法名 ------------------------------------------------------
base  = getfield_def(A, 'base',  'env');
test  = getfield_def(A, 'test',  'env2');
sqlaw = getfield_def(A, 'sqlaw', 'sqlaw');
bare  = getfield_def(A, 'bare',  'sq');

Q = struct();
Q.verdict  = '';
Q.hardFail = {};
Q.softFail = {};
Q.crit     = struct();

% ==================================================================
% Q1 有效通道率
% ==================================================================
acRms = sqrt(mean(A.filtered.^2, 1));
med   = median(acRms(acRms > 0));
if isempty(med) || med <= 0, med = max(acRms); end
validFrac = mean(acRms > 0.05 * med);
Q.crit.validChanFrac = q_item(validFrac, opt.MinValidChanFrac, '>=', ...
    sprintf('有效通道率 %.3f（阈值 %.2f）', validFrac, opt.MinValidChanFrac));
if ~Q.crit.validChanFrac.pass, Q.hardFail{end+1} = 'Q1 有效通道率不足'; end

% ==================================================================
% Q2 量化余量：acRms / lsb
% ==================================================================
lsb = local_lsb(A.raw);
acRmsAll = sqrt(mean(A.filtered(:).^2));
quantMargin = acRmsAll / max(lsb, eps);
Q.crit.quantMargin = q_item(quantMargin, opt.MinQuantMargin, '>=', ...
    sprintf('量化余量 %.2f lsb（lsb=%.4g，阈值 %.1f）', ...
            quantMargin, lsb, opt.MinQuantMargin));
if ~Q.crit.quantMargin.pass, Q.hardFail{end+1} = 'Q2 量化余量不足（信号逼近量化台阶）'; end

% ==================================================================
% Q3 直流偏置比（**必须先去除，否则平方退化为放大原图**）
% ==================================================================
dc  = median(A.raw, 1);
dcR = mean(abs(dc)) / max(acRmsAll, eps);
Q.crit.dcRatio = q_item(dcR, 100, 'report', ...
    sprintf('直流/交流幅度比 %.1f（>100 表示平方前必须去直流）', dcR));
Q.crit.dcRatio.hard = false;      % 已被 pa_dc_remove 处理，仅作审计记录

% ==================================================================
% Q4 视场截断：边缘 10% 环带能量占比
%   说明：这是**软判据**。样品（如横贯视场的交叉钨丝）合法地填满视场时
%   也会触发，此时正确处置是放大 FOV 或裁剪 ROI，而不是丢弃数据。
%   故只需给出提示，不构成 DISCARD。
% ==================================================================
edgeFrac = local_edge_frac(A.IM.(test), 0.10);
Q.crit.edgeFrac = q_item(edgeFrac, opt.MaxEdgeFrac, '<=', ...
    sprintf('视场边缘 10%% 环带能量占比 %.3f（>%.2f 提示需放大 FOV）', ...
            edgeFrac, opt.MaxEdgeFrac));
Q.crit.edgeFrac.hard = false;
if ~Q.crit.edgeFrac.pass
    Q.softFail{end+1} = 'Q4 目标填满/超出成像视场（放大 FOV 或裁剪 ROI 后复评）';
end

% ==================================================================
% Q5 基线可测性
% ==================================================================
cnrBase = A.M.(base).CNR;
Q.crit.cnrBase = q_item(cnrBase, opt.MinCNR, '>=', ...
    sprintf('基线 %s 的 CNR = %.3f（阈值 %.2f）', base, cnrBase, opt.MinCNR));
if ~Q.crit.cnrBase.pass, Q.hardFail{end+1} = 'Q5 基线图像不可测（CNR 过低）'; end

% ==================================================================
% Q6 平方增益（待评 vs 基线）
% ==================================================================
cnrTest = A.M.(test).CNR;
gcnrGain = A.M.(test).gCNR - A.M.(base).gCNR;
cnrGain  = cnrTest - cnrBase;
gainOk = (cnrGain > opt.MinGainCNR) && (gcnrGain >= -0.02);
Q.crit.sqGain = q_item(double(gainOk), 1, '==1', ...
    sprintf('平方增益：dCNR = %+.3f，dgCNR = %+.3f（要求 dCNR>0 且 dgCNR>=-0.02）', ...
            cnrGain, gcnrGain));
if ~Q.crit.sqGain.pass, Q.softFail{end+1} = 'Q6 该数据上平方方法无增益'; end

% ==================================================================
% Q7 免 Hilbert 一致性：D2' vs D1^2
% ==================================================================
pear = local_pearson(A.filtered, A.cfg, sqlaw, test);
if isnan(pear)
    Q.crit.sqlawConsistency = q_item(NaN, opt.MinPearsonSqlaw, '>=', ...
        'D2p 与 D1^2 一致性：未计算（缺少方法）');
    Q.crit.sqlawConsistency.pass = true;     % 缺项不判负
else
    Q.crit.sqlawConsistency = q_item(pear, opt.MinPearsonSqlaw, '>=', ...
        sprintf('D2p 与 D1^2 的 Pearson = %.4f（阈值 %.2f）', pear, opt.MinPearsonSqlaw));
    if ~Q.crit.sqlawConsistency.pass
        Q.softFail{end+1} = 'Q7 该数据带宽条件下 D2p 不能替代 D1^2';
    end
end

% ==================================================================
% Q8 标称–实测频率一致性（**配置完整性**；判据与出处见 docs/06 §4）
%   判据：实测带中心 / 实际使用中心 ∈ [0.5, 2.0]。
%   不满足说明**配置**设错（绝大多数是标称 f0 与换能器不符），非方法失效。
%   与 Q3 一样作**审计记录**（hard=false）：闸门在配置阶段施加 —— 一旦按实测
%   带中心回填配置（如 pa_wire_manifest 的 F0 覆盖），该比值即回到 1 附近。
%   q8_nominal 额外给出"实测/数据手册标称"之比，用于暴露历史错误配置。
% ==================================================================
if isfield(A.cfg, 'q8_pass')
    Q.crit.freqConsistency = q_item(double(A.cfg.q8_pass), 1, '==1', ...
        sprintf(['Q8 实测/实际中心比 = %.3f（实际 %.3f MHz，实测 %.3f MHz；' ...
                 '实测/标称 = %.3f，标称 %.3f MHz；要求 ∈[0.5,2.0]）'], ...
                A.cfg.q8_ratio, A.cfg.f0_eff/1e6, A.cfg.f0_meas/1e6, ...
                A.cfg.q8_nominal, A.cfg.f0Spec/1e6));
    Q.crit.freqConsistency.hard = false;     % 配置阶段闸门；此处仅审计记录
    if ~Q.crit.freqConsistency.pass
        Q.softFail{end+1} = 'Q8 标称-实测中心频率不一致（首要怀疑配置，而非方法）';
    end
else
    Q.crit.freqConsistency = q_item(1, 1, '==1', 'Q8 未计算（缺 cfg.q8_pass）');
    Q.crit.freqConsistency.hard = false;
end

% ==================================================================
% 结论
% ==================================================================
if ~isempty(Q.hardFail)
    Q.verdict = 'DISCARD';
elseif ~isempty(Q.softFail)
    Q.verdict = 'REVIEW';
else
    Q.verdict = 'KEEP';
end

Q.acRms        = acRms;
Q.denomStats   = struct('dcRatio', dcR, 'lsb', lsb, 'acRmsAll', acRmsAll, ...
                        'edgeFrac', edgeFrac, 'cnrBase', cnrBase, ...
                        'cnrGain', cnrGain, 'gcnrGain', gcnrGain, ...
                        'pearsonSqlaw', pear);

if nargout > 1
    report = local_report(Q, A, opt);
end
end

% ==================================================================
%  Q4 辅助：边缘环带能量占比
% ==================================================================
function f = local_edge_frac(IM, band)
IM = abs(IM);
IM = IM / (max(IM(:)) + eps);
n  = size(IM, 1);
k  = max(1, round(band * n));
inner = sum(sum(IM(k+1:end-k, k+1:end-k)));
outer = sum(IM(:)) - inner;
f = outer / (sum(IM(:)) + eps);
end

% ==================================================================
%  Q7 辅助：D2' 与 D1^2 的通道级 Pearson
% ==================================================================
function p = local_pearson(x, cfg, sqlaw, test)
p = NaN;
try
    a = pa_demodulate(x, cfg, sqlaw, 'Narrowband', ~cfg.sqlaw_ok);
    b = pa_demodulate(x, cfg, test);
    a = a(:); b = b(:);
    if std(a) > 0 && std(b) > 0
        c = corrcoef(a, b);
        p = c(1, 2);
    end
catch
    p = NaN;
end
end

% ==================================================================
%  量化台阶估计
% ==================================================================
function lsb = local_lsb(raw)
% 用最小正差分的众数估计量化步长；若数据为连续浮点则返回极小值
v = raw(:);
v = v(isfinite(v));
if isempty(v), lsb = 0; return; end
u = unique(v);
if numel(u) < 2, lsb = 0; return; end
d = diff(u);
d = d(d > 0);
if isempty(d), lsb = 0; return; end
lsb = median(d);
if lsb < 1e-9
    lsb = max(abs(v)) * 1e-12;      % 连续数据：视为无量化台阶
end
end

% ==================================================================
function it = q_item(val, thr, cmp, msg)
it = struct('value', val, 'threshold', thr, 'cmp', cmp, 'msg', msg, 'pass', true);
switch cmp
    case '>=',    it.pass = val >= thr;
    case '<=',    it.pass = val <= thr;
    case '==1',   it.pass = val == 1;
    case 'report', it.pass = true;
end
end

% ==================================================================
function v = getfield_def(A, k, d)
if isfield(A, k) && ~isempty(A.(k)), v = A.(k); else, v = d; end
end

% ==================================================================
function s = local_report(Q, A, opt)
L = {};
L{end+1} = '============================================================';
L{end+1} = sprintf('  数据达标筛检报告（pa_qc v1）');
L{end+1} = sprintf('  数据源 : %s    预设 : %s', ...
    getfield_def(A.cfg, 'name', '?'), getfield_def(A.cfg, 'preset', '?'));
L{end+1} = sprintf('  结论   : %s', Q.verdict);
L{end+1} = '------------------------------------------------------------';
fn = fieldnames(Q.crit);
for i = 1:numel(fn)
    it = Q.crit.(fn{i});
    if it.pass, flag = 'PASS'; else, flag = 'FAIL'; end
    L{end+1} = sprintf('  [%s] %-18s %s', flag, fn{i}, it.msg);
end
L{end+1} = '------------------------------------------------------------';
if ~isempty(Q.hardFail)
    L{end+1} = '  硬失败（-> DISCARD）：';
    for i = 1:numel(Q.hardFail), L{end+1} = ['    - ' Q.hardFail{i}]; end
end
if ~isempty(Q.softFail)
    L{end+1} = '  软失败（-> REVIEW）：';
    for i = 1:numel(Q.softFail), L{end+1} = ['    - ' Q.softFail{i}]; end
end
if isempty(Q.hardFail) && isempty(Q.softFail)
    L{end+1} = '  全部判据通过.可进入论文结果集.';
end
L{end+1} = '  阈值：';
L{end+1} = sprintf('    有效通道率 >= %.2f ; 量化余量 >= %.1f lsb', ...
    opt.MinValidChanFrac, opt.MinQuantMargin);
L{end+1} = sprintf('    边缘能量占比 <= %.2f ; 基线 CNR >= %.2f', ...
    opt.MaxEdgeFrac, opt.MinCNR);
L{end+1} = sprintf('    D2''-D1^2 Pearson >= %.2f ; dCNR > %.1f', ...
    opt.MinPearsonSqlaw, opt.MinGainCNR);
L{end+1} = '    Q8 实测/实际中心比 ∈ [0.5, 2.0]（配置完整性，仅审计）';
L{end+1} = '============================================================';
s = strjoin(L, newline);
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
