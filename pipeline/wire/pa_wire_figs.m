function pa_wire_figs(R, outDir)
%PA_WIRE_FIGS  钨丝"点图 / 线图 / 剖面图 / 指标图"四件套出图（+ 指标与筛检报告）
%
%   pa_wire_figs(R, outDir)
%
%   输入
%     R       : pa_wire_run 的返回值
%     outDir  : 输出目录
%
%   产出文件（以 spec.id 为前缀）
%     W#_point_<t>.png    点图：四路重建图并排（共用色标 + 峰值标注）
%     W#_profile_<t>.png  剖面曲线：横向 PSF 与 纵向 LSF（四路对照）
%     W#_profiledB_<t>.png 剖面 dB 图：显示旁瓣与伪影底
%     W#_metrics_<t>.png  指标图：aFWHM / CNR / gCNR / PSR / DR 条形对照
%     W#_report_<t>.txt   文字报告：参数、带宽审计、指标表、达标筛检
%     W#_sheet_<t>.csv    指标表（便于直接贴进论文补充材料）
%
%   设计要点（对应"结果呈现与表达策略"）
%     · 四路共用同一色标与同一坐标范围 —— 否则"看起来更好"可能只是显示差异
%     · aFWHM 一律标注为"表观半高宽"，并在图中写明高斯 PSF 下
%       FWHM(g^2)=FWHM(g)/sqrt2（-29.3%）是数学必然，不能当分辨率增益
%     · gCNR 作为主指标（对显示窗不敏感）；CNR/PSR/DR 供对照
%     · 任一出图环节失败都不影响数据生产：各自 try/catch 并打印出错环节
%
%   版本：v1  2026-10-14

if nargin < 2 || isempty(outDir), outDir = R.outDir; end
if ~exist(outDir, 'dir'), mkdir(outDir); end

id    = R.spec.id;
gr    = R.grid;   % 注意：不得命名为 grid，否则会遮蔽内建函数 grid()
meths = {'env', 'env2', 'sqlaw', 'sq'};
names = {'D1  线性包络 |z|', 'D1^2  包络平方（既有主方法）', ...
         'D2p  平方律 LPF(x^2)（免 Hilbert）', 'D2  裸平方 x^2（缺陷对照）'};
cols  = [0.00 0.35 0.80;    % D1   蓝
         0.85 0.10 0.10;    % D1^2 红
         0.00 0.55 0.25;    % D2p  绿
         0.45 0.45 0.45];   % D2   灰

keep = false(size(meths));
for i = 1:numel(meths), keep(i) = isfield(R.IM, meths{i}); end
meths = meths(keep);  names = names(keep);  cols = cols(keep,:);
nm = numel(meths);
tickLbl = {'D1', 'D1^2', 'D2p', 'D2'};
tickLbl = tickLbl(keep);

% ==================================================================
%  (1) 点图 / 线图：四路重建图并排
% ==================================================================
try
    f = figure('Visible', 'off', 'Color', 'w', 'Position', [50 50 300*nm 340]);
    tl = tiledlayout(f, 1, nm, 'TileSpacing', 'compact', 'Padding', 'compact');
    for i = 1:nm
        ax = nexttile(tl);
        imagesc(ax, gr.x, gr.y, R.IM.(meths{i}));
        axis(ax, 'image');  set(ax, 'YDir', 'normal');
        colormap(ax, hot);  clim(ax, [0 1]);
        xlabel(ax, 'x (mm)');  ylabel(ax, 'y (mm)');
        title(ax, names{i}, 'Color', cols(i,:), 'FontSize', 9, 'FontWeight', 'bold');
        hold(ax, 'on');
        [~, li] = max(R.IM.(meths{i})(:));
        [pr, pc] = ind2sub(size(R.IM.(meths{i})), li);
        plot(ax, gr.x(pc), gr.y(pr), 'o', 'MarkerSize', 8, ...
             'MarkerEdgeColor', 'w', 'LineWidth', 1.0);
        hold(ax, 'off');
    end
    sgtitle(f, sprintf('%s  %s', id, R.spec.desc), 'FontWeight', 'bold');
    cb = colorbar(ax);   % colorbar 不接受 TiledLayout 作为入参（实测 R2025b）
    cb.Layout.Tile = 'east';
    cb.Label.String = '归一化强度 (a.u.)';
    exportgraphics(f, fullfile(outDir, sprintf('%s_point.png', id)), 'Resolution', 200);
    close(f);
catch e
    fprintf('  [fig] 点/线图失败：%s\n', e.message);
    try, close all; catch, end %#ok<CTCH>
end

% ==================================================================
%  (2) 剖面曲线：横向 PSF 与 纵向 LSF
% ==================================================================
try
    f = figure('Visible', 'off', 'Color', 'w', 'Position', [50 50 1000 380]);
    for k = 1:2
        ax = subplot(1, 2, k);
        if k == 1
            P = R.profRow;  axx = R.axRow;  ttl = '横向剖面（过峰值行）';
        else
            P = R.profCol;  axx = R.axCol;  ttl = '纵向剖面（过峰值列）';
        end
        hold(ax, 'on');
        for i = 1:nm
            plot(ax, axx, P.(meths{i}), '-', 'Color', cols(i,:), ...
                 'LineWidth', 1.4, 'DisplayName', names{i});
        end
        hold(ax, 'off');
        grid(ax, 'on');  box(ax, 'on');
        xlabel(ax, '位置 (mm)');  ylabel(ax, '归一化强度');
        title(ax, ttl);
        legend(ax, 'Location', 'northeast', 'FontSize', 7);
        xlim(ax, [min(axx) max(axx)]);
    end
    sgtitle(f, sprintf(['%s 剖面曲线；aFWHM 为表观量，高斯 PSF 下 ' ...
        'FWHM(g^2)=FWHM(g)/sqrt2（-29.3%%）'], id));
    exportgraphics(f, fullfile(outDir, sprintf('%s_profile.png', id)), 'Resolution', 200);
    close(f);
catch e
    fprintf('  [fig] 剖面曲线失败：%s\n', e.message);
    try, close all; catch, end %#ok<CTCH>
end

% ==================================================================
%  (3) 线性图 + dB 图
% ==================================================================
try
    f = figure('Visible', 'off', 'Color', 'w', 'Position', [50 50 1000 380]);
    ax = subplot(1,2,1); hold(ax,'on');
    for i = 1:nm
        plot(ax, R.axRow, R.profRow.(meths{i}), '-', 'Color', cols(i,:), 'LineWidth', 1.4);
    end
    hold(ax,'off'); grid(ax,'on'); box(ax,'on');
    xlabel(ax,'位置 (mm)'); ylabel(ax,'归一化强度');
    title(ax,'横向剖面（线性）');
    ax2 = subplot(1,2,2); hold(ax2,'on');
    for i = 1:nm
        plot(ax2, R.axRow, 20*log10(R.profRow.(meths{i}) + 1e-4), '-', ...
             'Color', cols(i,:), 'LineWidth', 1.4);
    end
    hold(ax2,'off'); grid(ax2,'on'); box(ax2,'on');
    xlabel(ax2,'位置 (mm)'); ylabel(ax2,'强度 (dB)');
    title(ax2,'横向剖面（dB，显示旁瓣与伪影底）');
    exportgraphics(f, fullfile(outDir, sprintf('%s_profiledB.png', id)), 'Resolution', 200);
    close(f);
catch e
    fprintf('  [fig] dB 图失败：%s\n', e.message);
    try, close all; catch, end %#ok<CTCH>
end

% ==================================================================
%  (4) 指标图
% ==================================================================
try
    fields = {'aFWHM', 'CNR', 'gCNR', 'PSR', 'DR'};
    tits   = {'aFWHM (mm，表观量)', 'CNR', 'gCNR（主指标）', 'PSR', 'DR (dB)'};
    f = figure('Visible', 'off', 'Color', 'w', 'Position', [50 50 1280 300]);
    for j = 1:numel(fields)
        ax = subplot(1, numel(fields), j);
        v = zeros(nm, 1);
        for i = 1:nm, v(i) = R.Mrow.(meths{i}).(fields{j}); end
        b = bar(ax, v, 0.6, 'FaceColor', 'flat');
        for i = 1:nm, b.CData(i,:) = cols(i,:); end
        set(ax, 'XTick', 1:nm, 'XTickLabel', tickLbl, 'FontSize', 7);
        title(ax, tits{j}, 'FontSize', 8);
        grid(ax, 'on');  box(ax, 'on');
        for i = 1:nm
            text(ax, i, v(i), sprintf('%.3g', v(i)), ...
                 'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom', ...
                 'FontSize', 6);
        end
    end
    sgtitle(f, sprintf('%s 指标对照（均取自过峰值的横向剖面）', id));
    exportgraphics(f, fullfile(outDir, sprintf('%s_metrics.png', id)), 'Resolution', 200);
    close(f);
catch e
    fprintf('  [fig] 指标图失败：%s\n', e.message);
    try, close all; catch, end %#ok<CTCH>
end

% ==================================================================
%  (5) 文字报告 + 指标表
% ==================================================================
L = {};
L{end+1} = repmat('=', 1, 74);
L{end+1} = sprintf('  钨丝点/线图生产报告  %s', id);
L{end+1} = sprintf('  描述   : %s', R.spec.desc);
L{end+1} = sprintf('  对应图 : %s', R.spec.figure);
L{end+1} = sprintf('  数据源 : %s   (cfg=%s, preset=%s)', ...
    R.spec.dataDir, R.spec.cfgName, R.cfg.preset);
L{end+1} = sprintf('  矩阵   : %d 采样 x %d 通道', R.meta.nSamples, R.meta.nChannels);
L{end+1} = repmat('-', 1, 74);
L{end+1} = '  [几何 / 采集]';
L{end+1} = sprintf('    阵列 %s, N=%d, R=%.2f mm, vs=%d m/s, fs=%.1f MHz', ...
    R.cfg.arrayType, R.cfg.N, R.cfg.R*1e3, R.cfg.vs, R.cfg.fs/1e6);
NxUsed  = size(R.IM.(meths{1}), 1);
fovUsed = R.grid.FOV;                       % 实际成像视场（可能被运行时覆盖）
if abs(fovUsed - R.cfg.FOV) > 1e-9
    % 运行时覆盖了视场：必须打印**实际值**，否则复现者会按 cfg 默认值误读
    L{end+1} = sprintf('    视场 %.1f mm（实际，Nx=%d x dx=%.4f mm；cfg.FOV=%.1f mm 被覆盖）', ...
        fovUsed*1e3, NxUsed, R.grid.dx, R.cfg.FOV*1e3);
    L{end+1} = sprintf('    像素 %d^2, dx=%.4f mm', NxUsed, R.grid.dx);
else
    L{end+1} = sprintf('    视场 %.1f mm, 像素 %d^2, dx=%.4f mm', ...
        fovUsed*1e3, NxUsed, R.grid.dx);
end
L{end+1} = '  [统一预处理链] 哨兵修复 -> 去直流 -> 带通 -> 解调 -> 平滑';
L{end+1} = sprintf('    去直流 %s ; 带通 %.2f-%.2f MHz order %d ; 解调后平滑 %d ; 时域滤波 %s', ...
    R.cfg.dcMethod, R.cfg.f_low/1e6, R.cfg.f_high/1e6, R.cfg.f_order, ...
    R.cfg.smooth, R.cfg.filt);
L{end+1} = '  [带宽审计]';
L{end+1} = sprintf('    谱峰 %.2f MHz ; -6dB 带 [%.2f %.2f] MHz ; B6=%.2f MHz', ...
    R.band.f_peak/1e6, R.band.f_lo6/1e6, R.band.f_hi6/1e6, R.band.B6/1e6);
L{end+1} = sprintf('    累积5-95%% 带 [%.2f %.2f] MHz ; Bcum=%.2f MHz ; 尖峰标记=%d', ...
    R.band.f05/1e6, R.band.f95/1e6, R.band.Bcum/1e6, R.band.spurFlag);
L{end+1} = sprintf('    判据采用 %s : 真实带 [%.2f %.2f] MHz ; B=%.2f MHz ; beta=%.2f', ...
    R.band.bandSrc, R.band.f_lo/1e6, R.band.f_hi/1e6, R.band.B_used/1e6, R.band.beta_used);
L{end+1} = sprintf('    最终分析带 [%.2f %.2f] MHz ; 低通截止 %.2f MHz ; 合法区间 [%.2f %.2f] MHz', ...
    R.cfg.f_low/1e6, R.cfg.f_high/1e6, R.cfg.lp_cutoff/1e6, ...
    R.cfg.lp_range(1)/1e6, R.cfg.lp_range(2)/1e6);
L{end+1} = sprintf('    D2p(BandMode=%s) 精确成立 = %d  （判据 B < 2*f_low <=> f_high < 3*f_low）', ...
    R.cfg.bandMode, R.cfg.sqlaw_ok);
L{end+1} = sprintf('    D2p 与 D1^2 的 Pearson = %.4f ; 幅度比 = %.4f（理论 0.5）', ...
    R.D.info.sqlaw.pearson_vs_ref, R.D.info.sqlaw.amp_ratio_vs_ref);
L{end+1} = repmat('-', 1, 74);
L{end+1} = '  [指标表]（横向剖面）';
L{end+1} = sprintf('    %-8s %10s %10s %10s %10s %10s', '方法', 'aFWHM', 'CNR', 'gCNR', 'PSR', 'DR');
for i = 1:nm
    m = R.Mrow.(meths{i});
    L{end+1} = sprintf('    %-8s %10.4g %10.4g %10.4g %10.4g %10.4g', ...
        meths{i}, m.aFWHM, m.CNR, m.gCNR, m.PSR, m.DR);
end
L{end+1} = repmat('-', 1, 74);
L{end+1} = '  达标筛检（pa_qc）';
L{end+1} = R.qcReport;
txt = strjoin(L, newline);

fid = fopen(fullfile(outDir, sprintf('%s_report.txt', id)), 'w', 'n', 'UTF-8');
fwrite(fid, txt, 'char');  fclose(fid);

fid = fopen(fullfile(outDir, sprintf('%s_sheet.csv', id)), 'w', 'n', 'UTF-8');
fprintf(fid, 'dataset,method,aFWHM_mm,CNR,gCNR,PSR,DR_dB,peakPos_mm,Concentration\n');
for i = 1:nm
    m  = R.Mrow.(meths{i});
    mc = R.Mcol.(meths{i});
    fprintf(fid, '%s,%s,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g\n', ...
        id, meths{i}, m.aFWHM, m.CNR, m.gCNR, m.PSR, m.DR, m.peakPos_mm, mc.Conc);
end
fclose(fid);
end
