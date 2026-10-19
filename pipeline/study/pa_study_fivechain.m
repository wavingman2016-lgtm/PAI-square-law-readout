function R = pa_study_fivechain(varargin)
%PA_STUDY_FIVECHAIN  五链冻结后的最小新实验（A 幅度阶梯 / B 双目标 / C 噪声检测 / D 窗口 / E 计时）
%
%   依据 docs/15_五链冻结与后续实验规划_v0.33.md 第 5 节。
%   全部为**受控仿真**（合成通道数据），物理采集不在本轮范围。
%
%   五链（docs/15 §2.1）
%     C  |sum g z| ; M sum g A ; EH sum g^2 A^2 ; EL sum g^2 (2LPF{x^2}) ; SQ sum g^2 x^2
%
%   实验
%     A 幅度阶梯：x 的幅度 a in {0.25,0.5,1,2,4}，检验 C/M 一次、EH/EL 二次响应
%     B 双目标：间距 x 强弱比（1:1, 2:1, 4:1），弱目标检出概率/峰谷比/定位误差
%     C 噪声检测：暗场 40 次 -> 每链 95 分位阈值（FPR=5%）；弱目标 20 次 -> Pd
%     D 窗口任务：固定窗 / 分位窗 / 双窗；弱目标显示对比、饱和与黑截断
%     E 计时：分环节，预热 3 + 正式 10 次
%
%   输出
%     results/fivechain/fivechain_sim.csv   长表
%     results/fivechain/fivechain_sim.mat
%
%   版本：v1  2026-10-18

opt.Array  = 'semicircle128';
opt.SNR    = 40;          % dB，作用于目标回波峰值
opt.Nx     = 601;
opt.FOV    = 40e-3;
opt.Nrep   = 6;           % 形态/检测轴重复数
opt.Ndark  = 40;          % 暗场重复数（阈值估计）
opt.Ndet   = 20;          % 检测轴重复数
opt.Exps   = {'A','B','C','D','E'};
opt.Cthr   = [];          % 非空则跳过暗场、直接用给定阈值（顺序 C/M/EH/EL/SQ）
                          % 暗场是 C 段最贵的一步（40 次 × 5 链），而它的阈值只依赖种子，
                          % 已归档的阈值可复现；加密幅度网格时没必要重算一遍。
opt.CaList = [];          % 非空则覆盖检测幅度网格
opt.CaLab  = {};          % 与 CaList 一一对应的条件标签（必须显式给出，禁止自动格式化）
opt.Save   = true;
opt.OutDir = '';
opt.Verbose = true;
opt = parse_opts(opt, varargin{:});

root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
if isempty(opt.OutDir), opt.OutDir = fullfile(root,'results','fivechain'); end
if ~exist(opt.OutDir,'dir'), mkdir(opt.OutDir); end

addpath(fullfile(root,'pipeline','config'));
addpath(fullfile(root,'pipeline','preprocess'));
addpath(fullfile(root,'pipeline','recon'));

% ---------------- 仿真参数（与 W1 几何一致）----------------
P = struct();
P.fs = 40e6; P.nSamples = 4096; P.vs = 1478; P.f0 = 5e6;
P.beta_sig = 0.60; P.bw_law = 0.80;
P.R = 55e-3; P.FOV = opt.FOV; P.Nx = opt.Nx; P.SNR = opt.SNR;
switch lower(opt.Array)
    case 'semicircle128', P.arrayType='semicircle128'; P.N=128;
    case 'ring256',       P.arrayType='ring1024';      P.N=256;
    otherwise, error('pa_study_fivechain:array','未知阵列：%s',opt.Array);
end
P.f_low  = P.f0*(1-P.bw_law/2);
P.f_high = P.f0*(1+P.bw_law/2);
cfg = build_cfg(P);
[sx,sy] = sensor_positions(P);

fprintf('\n==== pa_study_fivechain : %s | Nx=%d | Nrep=%d | Exps=%s ====\n', ...
    opt.Array, opt.Nx, opt.Nrep, strjoin(opt.Exps,','));

rows = struct('exp',{},'arm',{},'condition',{},'metric',{},'value',{},'unit',{});

R = struct('P',P,'cfg',cfg,'opt',opt);
R.rows = rows;

% ==================================================================
%  A. 幅度阶梯
% ==================================================================
if any(strcmpi(opt.Exps,'A'))
    fprintf('\n---- A 幅度阶梯 ----\n');
    amps = [0.25 0.5 1 2 4];
    arms = {'C','M','EH','EL','SQ'};
    PK = nan(numel(amps), numel(arms), opt.Nrep);
    BG = nan(numel(amps), numel(arms), opt.Nrep);
    for ia = 1:numel(amps)
        for ir = 1:opt.Nrep
            rng(10000 + 100*ia + ir);
            sig = local_synth(P, [0 0], amps(ia), sx, sy, opt.SNR);
            F = local_five(sig, cfg, P);
            for k = 1:numel(arms)
                img = F.(arms{k});
                pk = local_peak_near(img, P);
                PK(ia,k,ir) = pk;
                BG(ia,k,ir) = local_bg_median(img, P);
            end
        end
        fprintf('  a=%.2f 峰值 C/M/EH/EL/SQ = %.3g / %.3g / %.3g / %.3g / %.3g\n', ...
            amps(ia), mean(PK(ia,1,:)), mean(PK(ia,2,:)), mean(PK(ia,3,:)), ...
            mean(PK(ia,4,:)), mean(PK(ia,5,:)));
    end
    % 对数斜率（逐重复拟合后平均）
    S = nan(numel(arms), opt.Nrep);
    for k = 1:numel(arms)
        for ir = 1:opt.Nrep
            y = squeeze(PK(:,k,ir));
            if all(y>0)
                c = polyfit(log(amps(:)), log(y(:)), 1);
                S(k,ir) = c(1);
            end
        end
        add('A',arms{k},sprintf('amp_ladder'),'slope',mean(S(k,:)),'1');
        add('A',arms{k},sprintf('amp_ladder'),'slope_sd',std(S(k,:),0),'1');
        % 动态范围逐幅度单独成行。写成向量会让 fprintf 的格式串错位，
        % 把后续字段整段挤到下一行（v0.33 首跑已踩：A 段 5 行被吞）。
        for ia = 1:numel(amps)
            pkm = mean(PK(ia,k,:));
            bgm = mean(BG(ia,k,:));
            if bgm > 0 && isfinite(bgm) && isfinite(pkm) && pkm > 0
                drv = 20*log10(pkm/bgm);
            else
                drv = NaN;   % 背景中位数为 0/非有限、或峰非正：比值无定义，记 NaN
            end
            add('A',arms{k},sprintf('a=%.2f',amps(ia)),'dr_dB',drv,'dB');
        end
    end
    for ia = 1:numel(amps)
        for k = 1:numel(arms)
            add('A',arms{k},sprintf('a=%.2f',amps(ia)),'peak',mean(PK(ia,k,:)),'a.u.');
            add('A',arms{k},sprintf('a=%.2f',amps(ia)),'noise_floor',mean(BG(ia,k,:)),'a.u.');
        end
    end
    R.A = struct('amps',amps,'arms',{arms},'PK',PK,'BG',BG,'slope',S);
    persist();
end

% ==================================================================
%  B. 等强 / 不等强双目标
% ==================================================================
if any(strcmpi(opt.Exps,'B'))
    fprintf('\n---- B 双目标（等强/不等强）----\n');
    dList = [0.4 0.5 0.6 0.8 1.0 1.5 2.0]*1e-3;
    ratios = [1 2 4];
    arms = {'C','M','EH','EL','SQ'};
    Pd   = nan(numel(ratios), numel(dList), numel(arms), opt.Nrep);
    Dip  = nan(numel(ratios), numel(dList), numel(arms), opt.Nrep);
    DipStr = nan(numel(ratios), numel(dList), numel(arms), opt.Nrep);
    LocE = nan(numel(ratios), numel(dList), numel(arms), opt.Nrep);
    for iq = 1:numel(ratios)
        for id = 1:numel(dList)
            d = dList(id);
            for ir = 1:opt.Nrep
                rng(20000 + 1000*iq + 10*id + ir);
                pts  = [-d/2 0; d/2 0];
                amps = [1, 1/ratios(iq)];
                sig  = local_synth(P, pts, amps, sx, sy, opt.SNR);
                F    = local_five(sig, cfg, P);
                for k = 1:numel(arms)
                    [p, ax] = local_profile(F.(arms{k}), P);
                    bg = p(abs(ax)>5 & abs(ax)<15);
                    mu = median(bg);  sg = std(bg);
                    % 弱目标：真值 +d/2；搜索窗随间距收缩，保证两窗不重叠
                    hw = min(0.3, 0.6*(d/2*1e3));
                    m = abs(ax - d/2*1e3) <= hw;
                    idx = find(m);
                    if isempty(idx), continue; end
                    [pw, jw] = max(p(idx));
                    thr = mu + 3*sg;
                    % 峰谷比：强峰与两峰间谷
                    ms = abs(ax + d/2*1e3) <= hw;
                    msIdx = find(ms);
                    [ps, js] = max(p(ms));
                    xW = ax(idx(jw));
                    xS = ax(msIdx(js));
                    % 两峰间距须接近真值 d，排除把远处旁瓣当成第二个目标
                    sepOK = abs(abs(xW - xS) - d*1e3) <= max(0.15, 0.3*d*1e3);
                    between = (ax > -d/2*1e3) & (ax < d/2*1e3);
                    ib = find(between);
                    if ~isempty(ib)
                        [valley, jb] = min(p(ib));
                        iv = ib(jb);
                    else
                        valley = NaN; iv = 1;
                    end
                    pkmin = min(pw, ps);
                    % 谷必须落在两峰之间且为局部极小；否则是宽单峰的肩部，
                    % 会被人为读成"双峰之间有一个谷"。
                    if iv > 1 && iv < numel(p) && p(iv) <= p(iv-1) && p(iv) <= p(iv+1)
                        dip = (pkmin - valley)/(pkmin + eps);
                    else
                        dip = 0;
                    end
                    % 双峰分辨（形态判据，不问检出）：谷深 > 5% 且两峰间距接近 d。
                    % 检测问题由实验 C 在固定 FPR 下回答，此处不混用检测阈值。
                    Pd(iq,id,k,ir)  = double(dip > 0.05 && sepOK);
                    Dip(iq,id,k,ir) = dip;
                    DipStr(iq,id,k,ir) = double(dip >= 0.20 && sepOK);
                    if pw > thr
                        LocE(iq,id,k,ir) = abs(xW - d/2*1e3);
                    end
                end
            end
            fprintf('  ratio=%d:1 d=%.2f mm  Pd C/M/EH/EL/SQ = %.2f/%.2f/%.2f/%.2f/%.2f\n', ...
                ratios(iq), d*1e3, mean(Pd(iq,id,1,:)), mean(Pd(iq,id,2,:)), ...
                mean(Pd(iq,id,3,:)), mean(Pd(iq,id,4,:)), mean(Pd(iq,id,5,:)));
        end
    end
    for iq = 1:numel(ratios)
        for id = 1:numel(dList)
            for k = 1:numel(arms)
                c = sprintf('r=%d:1,d=%.2fmm',ratios(iq),dList(id)*1e3);
                add('B',arms{k},c,'Pd',mean(Pd(iq,id,k,:)),'1');
                add('B',arms{k},c,'Pd_dip20',mean(DipStr(iq,id,k,:)),'1');
                add('B',arms{k},c,'dip',mean(Dip(iq,id,k,:)),'ratio');
                add('B',arms{k},c,'dip_sd',std(Dip(iq,id,k,:),0),'ratio');
                add('B',arms{k},c,'loc_err',mean(LocE(iq,id,k,:)),'mm');
            end
        end
        % 最小可分辨间距（Pd>=0.5 的最小 d）
        for k = 1:numel(arms)
            pm5 = squeeze(mean(Pd(iq,:,k,:),4));
            pm20 = squeeze(mean(DipStr(iq,:,k,:),4));
            d5 = NaN; d20 = NaN;
            for id = 1:numel(dList)
                if isnan(d5)  && pm5(id)  >= 0.5, d5  = dList(id)*1e3; end
                if isnan(d20) && pm20(id) >= 0.5, d20 = dList(id)*1e3; end
            end
            add('B',arms{k},sprintf('r=%d:1',ratios(iq)),'d_min_mm_dip5',d5,'mm');
            add('B',arms{k},sprintf('r=%d:1',ratios(iq)),'d_min_mm_dip20',d20,'mm');
        end
    end
    R.B = struct('dList',dList,'ratios',ratios,'arms',{arms}, ...
                 'Pd',Pd,'Dip',Dip,'DipStr',DipStr,'LocE',LocE);
    persist();
end

% ==================================================================
%  C. 重复噪声与固定虚警率检测
% ==================================================================
if any(strcmpi(opt.Exps,'C'))
    fprintf('\n---- C 暗场噪声与检测 ----\n');
    arms = {'C','M','EH','EL','SQ'};
    % 固定噪声参考幅度：取 a=1 单目标的通道峰值，与目标幅度无关。
    % 必须与暗场共用同一值，否则"同一 SNR"对不同幅度含义不同，Pd 被高估。
    sigRef   = local_synth(P, [0 0], 1, sx, sy, 200);
    noiseRef = max(vecnorm(sigRef, inf, 1));
    fprintf('  噪声参考幅度 noiseRef = %.4g\n', noiseRef);
    % --- 暗场：无目标 ---
    thr = nan(numel(arms),1);
    darkStats = struct();
    if ~isempty(opt.Cthr)
        % 外部给定阈值：跳过暗场，只跑检测曲线。用于在固定阈值下加密幅度网格。
        assert(numel(opt.Cthr) == numel(arms), ...
            'C：Cthr 长度须为 %d（顺序 C/M/EH/EL/SQ），实际 %d', ...
            numel(arms), numel(opt.Cthr));
        thr = opt.Cthr(:);
        warning('fivechain:thrOverride', ...
            'C：使用外部给定阈值，暗场被跳过（不重写 dark 行）');
        fprintf('  暗场跳过（外部阈值）：%s\n', sprintf('%.4g ', thr));
    else
    for k = 1:numel(arms)
        mx = nan(opt.Ndark,1);  bg = nan(opt.Ndark,1);
        for ir = 1:opt.Ndark
            rng(30000 + 1000*k + ir);
            sig = local_noise_only(P, sx, sy, opt.SNR, noiseRef);
            F = local_five(sig, cfg, P);
            img = F.(arms{k});
            pk = local_peak_near(img, P);
            mx(ir) = pk;
            bg(ir) = local_bg_median(img, P);
        end
        thr(k) = prctile(mx, 95);          % 每次检验 FPR=5%
        darkStats.(arms{k}) = struct('max',mx,'bg',bg,'thr',thr(k));
        add('C',arms{k},'dark','thr_p95',thr(k),'a.u.');
        add('C',arms{k},'dark','max_median',median(mx),'a.u.');
        add('C',arms{k},'dark','bg_median',median(bg),'a.u.');
        add('C',arms{k},'dark','bg_sd',std(bg),'a.u.');
        fprintf('  暗场 %s: 阈值(P95)=%.3g  背景中位=%.3g\n', arms{k}, thr(k), median(bg));
    end
    end
    % --- 弱目标检测 ---
    % 幅度档位：v0.33 首跑只有 0.05–0.40，五链在最弱档 a=0.05 就已全部 Pd=1.00，
    % a50 一律卡在搜索下界 —— 这是地板效应，检测轴没有任何区分力，不能作为结论依据。
    % 故向下补 0.005 / 0.01 / 0.02 三档（对应 40+20log10(a) ≈ −6 / −0 / +6 dB 回波 SNR），
    % 使 a50 有落在定义域内部的解。补档只增加数据点，不改判据、不改阈值规则。
    aList = [0.005 0.01 0.02 0.05 0.1 0.2 0.4];
    % 标签与数值分表写死。上一版用 sprintf('a=%.2f',...) 生成条件名，0.005 会被
    % 格式化成 "a=0.01"，与真正的 a=0.01 撞键 —— 两档数据顶着同一个键进表，
    % 表面上只是"少了一行"，实际上是把两个不同实验混成一个。标签不参与计算，
    % 所以直接写字符串，并断言唯一。
    aLab  = {'0.005','0.01','0.02','0.05','0.10','0.20','0.40'};
    if ~isempty(opt.CaList)
        assert(~isempty(opt.CaLab) && numel(opt.CaLab) == numel(opt.CaList), ...
            'C：CaList 与 CaLab 必须同长且都非空');
        aList = opt.CaList;  aLab = opt.CaLab;
    end
    assert(numel(aLab) == numel(aList), 'C：aList 与 aLab 长度不一致');
    assert(numel(unique(aLab)) == numel(aLab), 'C：aLab 存在重复标签，会撞键');
    PdC = nan(numel(aList), numel(arms), opt.Ndet);
    for ia = 1:numel(aList)
        for ir = 1:opt.Ndet
            % 种子按幅度值定标而非按档位序号：这样以后增删档位不会悄悄换掉
            % 已有档位的噪声实现，逐档数字可跨版本对照。
            rng(41000 + round(1e5*aList(ia)) + ir);
            sig = local_synth(P, [0 0], aList(ia), sx, sy, opt.SNR, noiseRef);
            F = local_five(sig, cfg, P);
            for k = 1:numel(arms)
                pk = local_peak_near(F.(arms{k}), P);
                PdC(ia,k,ir) = double(pk > thr(k));
            end
        end
        fprintf('  a=%s  Pd C/M/EH/EL/SQ = %.2f/%.2f/%.2f/%.2f/%.2f\n', aLab{ia}, ...
            mean(PdC(ia,1,:)), mean(PdC(ia,2,:)), mean(PdC(ia,3,:)), ...
            mean(PdC(ia,4,:)), mean(PdC(ia,5,:)));
    end
    for ia = 1:numel(aList)
        for k = 1:numel(arms)
            c = ['a=' aLab{ia}];
            add('C',arms{k},c,'Pd_fpr5',mean(PdC(ia,k,:)),'1');
            add('C',arms{k},c,'Pd_sd',std(PdC(ia,k,:)),'1');
        end
    end
    % a50（Pd 首次 >= 0.5 的幅度；用线性插值）
    for k = 1:numel(arms)
        pm = squeeze(mean(PdC(:,k,:),3));
        a50 = NaN;
        for ia = 1:numel(aList)
            if pm(ia) >= 0.5
                if ia == 1
                    a50 = aList(1);
                else
                    a0 = aList(ia-1); p0 = pm(ia-1); a1 = aList(ia); p1 = pm(ia);
                    a50 = a0 + (0.5-p0)*(a1-a0)/(p1-p0+eps);
                end
                break;
            end
        end
        add('C',arms{k},'all','a50',a50,'rel');
        add('C',arms{k},'all','a50_at_floor',double(a50 <= aList(1)+eps),'1');
    end
    % 地板哨兵：若最弱档五链全部 Pd=1，a50 无信息量，必须显式告警，
    % 否则又会出现"表里有个数、读者以为它有意义"的情况。
    if all(mean(PdC(1,:,:),3) >= 1 - eps)
        warning('fivechain:detFloor', ...
            '最弱幅度 a=%.4g 处五链 Pd 全为 1：检测轴仍处地板，a50 不可解释。', aList(1));
    end
    R.C = struct('aList',aList,'arms',{arms},'thr',thr,'Pd',PdC,'dark',darkStats);
    persist();
end

% ==================================================================
%  D. 窗口任务
% ==================================================================
if any(strcmpi(opt.Exps,'D'))
    fprintf('\n---- D 窗口任务 ----\n');
    arms = {'M','EH','EL'};
    rules = {'fixed','percentile','dual'};
    d = 1.0e-3;  ratio = 4;

    % --- D1 仿真：Nrep 次独立噪声实现（2-D 显示模拟）---
    Wc = nan(numel(arms), numel(rules), opt.Nrep);
    Sf = nan(numel(arms), numel(rules), opt.Nrep);
    Bf = nan(numel(arms), numel(rules), opt.Nrep);
    for ir = 1:opt.Nrep
        rng(50000 + ir);
        sig = local_synth(P, [-d/2 0; d/2 0], [1 1/ratio], sx, sy, opt.SNR);
        F = local_five(sig, cfg, P);
        for k = 1:numel(arms)
            img = F.(arms{k});
            for irule = 1:numel(rules)
                v = local_window(img, rules{irule}, cfg);
                [p, ax] = local_profile(v, P);
                mw = abs(ax - d/2*1e3) <= 0.3;
                vw = max(p(mw));
                bg = p(abs(ax)>3 & abs(ax)<6);
                vb = median(bg);
                Wc(k,irule,ir) = (vw-vb)/(vw+vb+eps);
                Sf(k,irule,ir) = mean(v(:) >= 0.999);
                Bf(k,irule,ir) = mean(v(:) <= 0.001);
            end
        end
    end
    for k = 1:numel(arms)
        for irule = 1:numel(rules)
            c = sprintf('r=%d:1,d=1.0mm',ratio);
            add('D',arms{k},[c ',' rules{irule}],'weak_display_contrast', ...
                mean(squeeze(Wc(k,irule,:))),'1');
            add('D',arms{k},[c ',' rules{irule}],'weak_display_contrast_sd', ...
                std(squeeze(Wc(k,irule,:)),0),'1');
            add('D',arms{k},[c ',' rules{irule}],'saturated_frac', ...
                mean(squeeze(Sf(k,irule,:))),'1');
            add('D',arms{k},[c ',' rules{irule}],'black_frac', ...
                mean(squeeze(Bf(k,irule,:))),'1');
            fprintf('  [sim] %s / %-10s: 弱目标显示对比=%.3f±%.3f 饱和=%.3f 黑截断=%.3f\n', ...
                arms{k}, rules{irule}, mean(squeeze(Wc(k,irule,:))), ...
                std(squeeze(Wc(k,irule,:)),0), mean(squeeze(Sf(k,irule,:))), ...
                mean(squeeze(Bf(k,irule,:))));
        end
    end
    R.D = struct('d',d,'ratio',ratio,'arms',{arms},'rules',{rules}, ...
                 'Wc',Wc,'Sf',Sf,'Bf',Bf);

    % --- D2 真实数据：W2/W4 的已归档图像，只报饱和/黑截断（无需坐标）---
    rootD = fileparts(fileparts(fileparts(mfilename('fullpath'))));
    fmat = fullfile(rootD,'results','fivechain','fivechain_data.mat');
    if exist(fmat,'file')
        S2 = load(fmat,'patches','meta');
        rids = fieldnames(S2.patches);
        for ii = 1:numel(rids)
            ds = rids{ii};
            if ~any(strcmp(ds,{'W2','W4'})), continue; end
            for k = 1:numel(arms)
                if ~isfield(S2.patches.(ds), arms{k}), continue; end
                img = double(S2.patches.(ds).(arms{k}));
                for irule = 1:numel(rules)
                    v = local_window(img, rules{irule}, cfg);
                    add('D2',arms{k},sprintf('%s,%s',ds,rules{irule}), ...
                        'saturated_frac',mean(v(:) >= 0.999),'1');
                    add('D2',arms{k},sprintf('%s,%s',ds,rules{irule}), ...
                        'black_frac',mean(v(:) <= 0.001),'1');
                    fprintf('  [real] %s %s / %-10s: 饱和=%.3f 黑截断=%.3f\n', ...
                        ds, arms{k}, rules{irule}, mean(v(:) >= 0.999), mean(v(:) <= 0.001));
                end
            end
        end
        R.D2 = struct('source',fmat);
    else
        fprintf('  [real] 未找到 %s，D2 跳过\n', fmat);
    end
    persist();
end

% ==================================================================
%  E. 五链公平计时
% ==================================================================
if any(strcmpi(opt.Exps,'E'))
    fprintf('\n---- E 五链计时 ----\n');
    Nwarm = 3; Nrep = 10;
    rng(60001);
    sig = local_synth(P, [0 0], 1, sx, sy, opt.SNR);
    for w = 1:Nwarm, local_timing_pass(sig,cfg,P); end
    names = {'tHilbert','tEnv','tEnv2','tSquare','tLPF','tBP_real','tBP_complex'};
    % 按名字取索引，不用硬编号。上一版写成 T(6) 取复值反投影，跑出来 e2eC 与 e2eM
    % 只差一个 tEnv（即 C 与 M 同价），整条计时结论都是错的。硬编号一旦错位不会报错，
    % 只会安静地给出一个看似合理的数——所以这里彻底不写数字下标。
    idx = @(nm) find(strcmp(names, nm), 1);
    T = zeros(numel(names), Nrep);
    Tpre = zeros(1,Nrep);
    for ir = 1:Nrep
        v = local_timing_pass(sig,cfg,P);
        for k = 1:numel(names), T(k,ir) = v.(names{k}); end
        Tpre(ir) = v.tPre;
    end
    add('E','all','timing','tPre',mean(Tpre),'s');
    add('E','all','timing','tPre_sd',std(Tpre,0),'s');
    for k = 1:numel(names)
        add('E','all','timing',names{k},mean(T(k,:)),'s');
        add('E','all','timing',[names{k} '_sd'],std(T(k,:),0),'s');
        fprintf('  %-12s %.4f ± %.4f s\n', names{k}, mean(T(k,:)), std(T(k,:),0));
    end
    % 端到端（逐次求和的比值）
    tPre = mean(Tpre);                          % 预处理为五链共同项
    e2eC = tPre+T(idx('tHilbert'),:)+T(idx('tBP_complex'),:);   % 预处理 + Hilbert + 复值 BP
    e2eM = tPre+T(idx('tHilbert'),:)+T(idx('tEnv'),:)+T(idx('tBP_real'),:);   % + 包络 + 实值 BP
    e2eEH= tPre+T(idx('tHilbert'),:)+T(idx('tEnv2'),:)+T(idx('tBP_real'),:);  % + 平方包络 + 实值 BP
    e2eEL= tPre+T(idx('tSquare'),:)+T(idx('tLPF'),:)+T(idx('tBP_real'),:);    % 平方 + 低通 + 实值 BP
    % 哨兵：复值反投影必然明显贵于实值（约 2 倍）。若这条不过，说明 T 的行取错了，
    % 计时结论一律不可信——宁可在这里炸掉，也不要交出一个"看起来合理"的比值。
    bpRatio = mean(T(idx('tBP_complex'),:)./T(idx('tBP_real'),:));
    assert(bpRatio > 1.2, ...
        'E：复值/实值反投影耗时比仅 %.2f，疑似取错行，计时结论不可用', bpRatio);
    fprintf('  复值/实值 BP 耗时比 = %.2f\n', bpRatio);
    add('E','EL','timing','e2e_mean',mean(e2eEL),'s');
    add('E','M','timing','e2e_mean',mean(e2eM),'s');
    add('E','EH','timing','e2e_mean',mean(e2eEH),'s');
    add('E','C','timing','e2e_mean',mean(e2eC),'s');
    add('E','EL','timing','ratio_EL_over_M',mean(e2eEL./e2eM),'1');
    add('E','EL','timing','ratio_EL_over_C',mean(e2eEL./e2eC),'1');
    add('E','EH','timing','ratio_EH_over_M',mean(e2eEH./e2eM),'1');
    add('E','EL','timing','bp_ratio_EL_over_C',mean(T(idx('tBP_real'),:)./T(idx('tBP_complex'),:)),'1');
    % 检波级（前置到反投影之前）的净开销：EL 省掉 Hilbert+包络，但付一次平方+低通。
    % 这一项才是"算力收益"真正的落点，端到端比值会被反投影主导而稀释掉。
    add('E','EL','timing','env_stage_ratio_EL_over_M', ...
        mean((T(idx('tSquare'),:)+T(idx('tLPF'),:))./ ...
             (T(idx('tHilbert'),:)+T(idx('tEnv'),:))),'1');
    add('E','EL','timing','bp_share_of_e2e',mean(T(idx('tBP_real'),:)./e2eEL),'1');
    fprintf('  端到端 EL/M = %.3f, EL/C = %.3f\n', ...
        mean(e2eEL./e2eM), mean(e2eEL./e2eC));
    R.E = struct('names',{names},'T',T,'Nwarm',Nwarm,'Nrep',Nrep);
    persist();
end

% ---------------- 存盘 ----------------
persist();
fprintf('\n  [out] %s\n', opt.OutDir);

% ---- 嵌套：长表追加（与父工作区共享 rows）----
    function add(exp_, arm, cond, metric, val, unit)
        rows(end+1) = struct('exp',exp_,'arm',arm,'condition',cond, ...
                             'metric',metric,'value',val,'unit',unit);
    end

    function persist()
        % 增量保存：每个实验结束后立即落盘，避免长跑中途丢失。
        if ~opt.Save, return; end
        if ~exist(opt.OutDir,'dir'), mkdir(opt.OutDir); end
        % 断言：每行必须是标量值 + 非空单位。向量值会让 fprintf 错位而不报错，
        % 静默毁掉后续若干行，必须在落盘前拦住。
        for ii = 1:numel(rows)
            v = rows(ii).value;
            assert(isscalar(v) && isnumeric(v), ...
                'persist：第 %d 行 value 非标量（exp=%s, arm=%s, metric=%s）', ...
                ii, rows(ii).exp, rows(ii).arm, rows(ii).metric);
            assert(ischar(rows(ii).unit) && ~isempty(rows(ii).unit), ...
                'persist：第 %d 行 unit 为空（exp=%s, metric=%s）', ...
                ii, rows(ii).exp, rows(ii).metric);
        end
        % 断言：四元键唯一。条件名由格式化字符串生成时，不同数值可能压成同一个名
        % （0.005 与 0.01 都写成 "a=0.01"），结果是两个实验共用一行、图表照常出图。
        % 这种错在数值层看不出来，只能靠键唯一性拦住。
        key = cell(numel(rows),1);
        for ii = 1:numel(rows)
            key{ii} = sprintf('%s|%s|%s|%s', rows(ii).exp, rows(ii).arm, ...
                              rows(ii).condition, rows(ii).metric);
        end
        [uk, ~, ic] = unique(key);
        assert(numel(uk) == numel(key), ...
            'persist：键重复 -> %s', strjoin(uk(accumarray(ic,1) > 1), '; '));
        R.rows = rows;
        fid = fopen(fullfile(opt.OutDir,'fivechain_sim.csv'),'w');
        fprintf(fid,'exp,arm,condition,metric,value,unit\n');
        for ii = 1:numel(rows)
            fprintf(fid,'%s,%s,"%s",%s,%.6g,%s\n', rows(ii).exp, rows(ii).arm, ...
                    rows(ii).condition, rows(ii).metric, rows(ii).value, rows(ii).unit);
        end
        fclose(fid);
        save(fullfile(opt.OutDir,'fivechain_sim.mat'),'-struct','R','-v7.3');
        fprintf('    [saved %d rows]\n', numel(rows));
    end
end

% ==================================================================
%  五链核心
% ==================================================================
function F = local_five(sig, cfg, P)
D = pa_preprocess(sig, cfg, 'Methods', {'env','env2','sqlaw','sq'});
Z = complex(zeros(size(D.filtered)));
for ch = 1:size(D.filtered,2)
    Z(:,ch) = hilbert(D.filtered(:,ch));
end
IC  = pa_backproject_coherent(Z, cfg, 'Nx',P.Nx,'FOV',P.FOV, ...
                              'Comp','r','Normalize','none');
IM  = pa_backproject(D.env,   cfg,'Nx',P.Nx,'FOV',P.FOV,'Comp','r', 'Normalize','none');
IEH = pa_backproject(D.env2,  cfg,'Nx',P.Nx,'FOV',P.FOV,'Comp','r2','Normalize','none');
IEL = pa_backproject(D.sqlaw, cfg,'Nx',P.Nx,'FOV',P.FOV,'Comp','r2','Normalize','none');
ISQ = pa_backproject(D.sq,    cfg,'Nx',P.Nx,'FOV',P.FOV,'Comp','r2','Normalize','none');
F = struct('C',IC,'M',IM,'EH',IEH,'EL',IEL,'SQ',ISQ, ...
           'pearson_sqlaw_env2', D.info.sqlaw.pearson_vs_ref);
end

function v = local_timing_pass(sig, cfg, P)
t = tic;
D0 = pa_preprocess(sig, cfg, 'Methods', {'filtered'});
tPre = toc(t);

t = tic;
Z = complex(zeros(size(D0.filtered)));
for ch = 1:size(D0.filtered,2), Z(:,ch) = hilbert(D0.filtered(:,ch)); end
tH = toc(t);

t = tic; E1 = abs(Z); tEnv = toc(t);
t = tic; E2 = E1.^2;  tEnv2 = toc(t);
t = tic; S2 = D0.filtered.^2; tSq = toc(t);

t = tic;
wn = cfg.lp_cutoff/(cfg.fs/2);
[bl,al] = butter(6, wn, 'low');
Q = filtfilt(bl, al, S2);
tLP = toc(t);

t = tic;
pa_backproject(E1, cfg,'Nx',P.Nx,'FOV',P.FOV,'Comp','r','Normalize','none');
tBPr = toc(t);
t = tic;
pa_backproject_coherent(Z, cfg,'Nx',P.Nx,'FOV',P.FOV,'Comp','r','Normalize','none');
tBPc = toc(t);

v = struct('tHilbert',tH,'tEnv',tEnv,'tEnv2',tEnv2,'tSquare',tSq, ...
           'tLPF',tLP,'tBP_real',tBPr,'tBP_complex',tBPc,'tPre',tPre);
end

% ==================================================================
%  剖面与指标
% ==================================================================
function [p, ax] = local_profile(img, P, iy)
% 剖面固定过几何中心行（目标 y=0），不随各链最大值漂移：
% 否则 C 的最大值落在杂波处时，测到的是杂波剖面而非目标剖面。
if nargin < 3 || isempty(iy), iy = round(P.Nx/2); end
ax = ((1:P.Nx) - P.Nx/2) * (P.FOV/(P.Nx-1)) * 1e3;
iy = min(max(iy,1), P.Nx);
p = img(iy,:).';
end

function pk = local_peak_near(img, P)
ax = ((1:P.Nx) - P.Nx/2) * (P.FOV/(P.Nx-1)) * 1e3;
mask = abs(ax) <= 2.0;
imgm = img;
imgm(:, ~mask) = -inf;
imgm(~mask, :) = -inf;
pk = max(imgm(:));
end

function v = local_bg_median(img, P)
ax = ((1:P.Nx) - P.Nx/2) * (P.FOV/(P.Nx-1)) * 1e3;
[XC,YC] = meshgrid(ax,ax);
rr = hypot(XC,YC);
v = median(img(rr>=5 & rr<=12));
end

% ==================================================================
%  窗口映射
% ==================================================================
function v = local_window(img, rule, cfg)
img = max(img, 0);
switch lower(rule)
    case 'fixed'
        v = (img - cfg.WL) / cfg.WW;
        v = min(max(v,0),1);          % CT 式窗：窗内线性、窗外截断
    case 'percentile'
        p1 = prctile(img(:), 1);  p99 = prctile(img(:), 99);
        v = (img - p1) / (p99 - p1 + eps);
    case 'dual'
        p1  = prctile(img(:), 1);
        p50 = prctile(img(:), 50);
        p99 = prctile(img(:), 99);
        v = zeros(size(img));
        lo = img < p50;
        v(lo)  = 0.5 * (img(lo) - p1) / (p50 - p1 + eps);
        v(~lo) = 0.5 + 0.5 * (img(~lo) - p50) / (p99 - p50 + eps);
    otherwise
        error('local_window:rule','未知窗口规则：%s', rule);
end
v = min(max(v, 0), 1);
end

% ==================================================================
%  仿真
% ==================================================================
function sig = local_synth(P, pts, amps, sx, sy, snr_dB, noiseRef)
% 第 7 参数 noiseRef（可选）：固定的噪声参考幅度。
% 不给则用当前目标信号的峰值作参考（SNR 相对于当前目标）；
% 给了则噪声绝对水平固定，不随目标幅度变化 —— 固定虚警率检测必须用后者，
% 否则 a=0.05 的噪声比 a=1 低 26 dB，Pd 会被严重高估。
t = (0:P.nSamples-1).'/P.fs;
sig = zeros(P.nSamples, numel(sx));
for k = 1:size(pts,1)
    for m = 1:numel(sx)
        rr  = hypot(pts(k,1)-sx(m), pts(k,2)-sy(m));
        tau = rr/P.vs;
        a   = amps(k)/rr;
        g   = exp(-((t-tau)/(1/(2*pi*(P.beta_sig*P.f0/2.355)))).^2) ...
              .* cos(2*pi*P.f0*(t-tau));
        sig(:,m) = sig(:,m) + a*g;
    end
end
refAmp = max(vecnorm(sig, inf, 1));
if nargin >= 7 && ~isempty(noiseRef), refAmp = noiseRef; end
sig = sig + refAmp*10^(-snr_dB/20)*randn(size(sig));
end

function sig = local_noise_only(P, sx, sy, snr_dB, noiseRef)
% 暗场：只有噪声。noiseRef 应由调用方给出，与检测时同值，保证同一噪声水平。
t = (0:P.nSamples-1).'/P.fs;
ref = zeros(P.nSamples, numel(sx));
for m = 1:numel(sx)
    rr  = hypot(sx(m), sy(m));
    g   = exp(-((t-rr/P.vs)/(1/(2*pi*(P.beta_sig*P.f0/2.355)))).^2) ...
          .* cos(2*pi*P.f0*(t-rr/P.vs));
    ref(:,m) = g/rr;
end
refAmp = max(vecnorm(ref, inf, 1));
if nargin >= 5 && ~isempty(noiseRef), refAmp = noiseRef; end
sig = refAmp*10^(-snr_dB/20)*randn(P.nSamples, numel(sx));
end

function [sx,sy] = sensor_positions(P)
switch lower(P.arrayType)
    case 'semicircle128', ang = (0:P.N-1)*(pi/(P.N-1)) - pi;
    otherwise,            ang = (0:P.N-1)*(2*pi/P.N);
end
sx = P.R*cos(ang);  sy = P.R*sin(ang);
end

function cfg = build_cfg(P)
cfg = struct();
cfg.name='fivechain'; cfg.arrayType=P.arrayType; cfg.N=P.N; cfg.R=P.R;
cfg.vs=P.vs; cfg.fs=P.fs; cfg.nSamples=P.nSamples; cfg.FOV=P.FOV; cfg.Nx=P.Nx;
cfg.f0=P.f0; cfg.f_low=P.f_low; cfg.f_high=P.f_high; cfg.f_order=3;
cfg.smooth=1; cfg.dcMethod='median'; cfg.dcFirstN=100; cfg.padLen=[];
cfg.filt='none'; cfg.takeAbs=false; cfg.comp='r'; cfg.bw_law=P.bw_law;
cfg.WL=0.15; cfg.WW=0.70; cfg.nyquist=cfg.fs/2;
B_rf = cfg.f_high - cfg.f_low;  cfg.beta_rf = B_rf/cfg.f0;
cfg.sqlaw_lo_cut = B_rf;  cfg.sqlaw_hi_cut = 2*cfg.f_low;
cfg.sqlaw_ok = cfg.sqlaw_hi_cut > cfg.sqlaw_lo_cut;
if cfg.sqlaw_ok, cfg.lp_cutoff = 0.5*(cfg.sqlaw_lo_cut+cfg.sqlaw_hi_cut);
else,            cfg.lp_cutoff = cfg.f0; end
cfg.sqlaw_narrowband = [cfg.f_low, cfg.f_high];
end

function o = parse_opts(o, varargin)
if mod(numel(varargin),2) ~= 0, error('parse_opts:pair','参数必须成对。'); end
for i = 1:2:numel(varargin)
    k = varargin{i};
    if ~isfield(o,k), error('parse_opts:unknown','未知参数：%s',k); end
    o.(k) = varargin{i+1};
end
end
