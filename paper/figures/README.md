# paper/figures — 正式图库

> **用途**：论文（目标刊 *Photoacoustics*）正文与补充材料的图素材集中地。
> **命名规则**：`<图号>_<内容简写>.png`，与 `docs/13_期刊适配评估与投稿写作大纲.md` §3.4 的映射表一一对应。
> **重要**：本目录是**交付副本**（从 `results/`、`data_ext/`、`archive/` 复制而来）。若要更新图，请改**源头脚本/数据**后重新复制，**不要在此就地编辑**，否则与可复现链脱节。

---

## 一、正文主图（8 张）

| 图号 | 本目录文件 | 内容 | 数据来源（权威） | 状态 |
|---|---|---|---|---|
| **Fig.1** | `Fig01_schematic.png` | 原理示意 + **三臂流程图**：(a) raw → 同一前处理（去 DC + 带通）→ C / M / E 三分支，唯一差别是检测算子；(b) 一条几何补偿规则 $g_m=d_m/R$ 为何足够 | 由 `pipeline/study/_fig1_schematic.py` 生成（矢量友好，可直接转 PDF/SVG） | ✅ **2026-10-14 新绘** |
| **Fig.2** | `Fig02_identity_crossterm.png` | 恒等式与交叉项（六联）：(a) $I_C$、(b) $I_{BS}=I_C^2$、(c) $I_E$、(d) 交叉项 $X=I_{BS}-I_E$、(e) 相干场 $\mu(r)$（对数色标）、(f) 恒等式逐像素残差 | `results/fig2_identity/fig2_identity.mat`（`pipeline/study/pa_study_fig2_identity.m`）+ `paper/figures/_plot_fig2_identity.py` | ✅ **2026-10-15 重绘**（旧 `_draft` 版画的是 D3 保号平方＝非物理量、补偿用 $r^2$，已弃用；残差 $2.2\times10^{-16}$ 为机器精度，恒等式按构造成立） |
| **Fig.3** | `Fig03_resolution_sixpanel.png` | 分辨率判定六联：(a) E1 单点 PSF **各臂域内归一化 dB 剖面**；(b) E1 三臂表观宽度 + gCNR（唯一跨臂量）；(c) E2 双点 Rayleigh 三臂（分辨率结论落此）；(d) E3 对比度阶梯三臂；(e) 单点图像；(f) 判定摘要 | `results/study_resolution/`（`pipeline/study/pa_study_resolution.m`，**Nx=801, Nrep=4, 补偿统一 r**）+ `paper/figures/_plot_fig3_resolution.py` | ✅ **2026-10-15 重绘**（三臂补齐 Arm C；修掉两处口径违规：① 不再把 `sqrt(I_E)` 与 `I_M` 画在同一线性幅值轴 ② 补偿由 `r²` 改为 `r`；MATLAB 侧不再出图，避免两套图并存）｜**2026-10-15 更名** `fourpanel`→`sixpanel`（实为六联，原名误导） |
| **Fig.4** | `Fig04_regime_fourpanel.png` | 四轴稳健性：(a) 波前畸变；(b) SNR；(c) 随机阵元失效（gCNR 实线 + **SSIM 非饱和**虚线）；(d) 相干杂波相图（**警示语义色标**）；(d′) 杂波剖面；(f) 读图纪律 | `results/study_phase/`（SA/SB）、`results/study_audit/study_audit.mat`（axis2）、`results/study_regime_semicircle128/` | ✅ **2026-10-15 重绘**（旧版只有畸变+杂波两轴且把 PSR 跨臂并排，违反"跨臂只比 gCNR"；新版四轴齐、PSR/宽度改为域内纵向读数、相干杂波作为**唯一例外**显式披露） |
| **Fig.5** | `Fig05_delta_gCNR_15of15.png` | **核心证据图**：15/15 场景 $\Delta gCNR>0$ 条形图（均值 **+0.247**） | `results/study_adv_semicircle128/` | ✅ 就绪 |
| **Fig.6** | `Fig06_own6_registry.png` | **自有实测 6 组**四联总览（6/6 KEEP） | `results/registry/registry_overview.png` | ✅ 就绪 |
| **Fig.7** | `Fig07_invivo_tissue.png`（+ `Fig07b_patato_three_arms.png`、`Fig07c_rsom_check.png`、**`Fig07d_3dpact_qualitative.png`**） | **外部在体生物组织**：小鼠在体 / 人皮肤 / 大鼠脑 / 人乳腺 | `data_ext/`；PATATO 已接入统一管线（`results/study_patato/`，corr +0.8434） | ✅ **2026-10-15补齐 (d)**（3D-PACT 大鼠脑 180×250×120 + 左右乳腺 800×800×305，MIP + 分位数显式窗；**仅重建体 ⇒ 明确标注"qualitative display only"，不做三臂对照、不报任何指标**） |
| **Fig.8** | `Fig08_windowing.png` | **窗口技术**：五档窗并排 + 裁黑比例 + 窗不变性 | `results/supp/S2_windowing.png` | ✅ 就绪 |

## 二、补充材料图（Fig. S）

| 图号 | 本目录文件 | 内容 | 数据来源 | 状态 |
|---|---|---|---|---|
| **Fig. S0** | `FigS0_data_sinograms.png` | 旋转数据集 sinogram 抽检（数据质量交代） | `results/_sinograms.png` | ✅ |
| **Fig. S1** | `FigS1_equiv_W1/W2/W3.png` | $I_E$ 两条实现 **EI↔LP** 等价证明（4 面板 ×3 数据集） | `results/supp/S1_equiv_*.png` | ✅ **2026-10-16 重绘**（A3：图内 `annotation` 由 "Difference = interpolation order only" 改为**总实现残差**三项清单 transition-band leakage + boundary handling + interpolation order，并注明"未分离"；**R6：图内 title / legend / annotation 与图注由 "(main text)/(Supplement)"、`consist`/`direct` 统一为 **EI**（envelope 包络路，生产默认）/ **LP**（square-and-low-pass，免 Hilbert），与 §2.7 实现命名对齐**；数值未变，`S1_equiv_table.csv` 逐位一致） |
| ↳ 佐证 | `FigS1b_study_comp_W1.png`、`FigS1c_consist_W1_point.png` | 通道向量级验证 + 生产管线 EI 输出 | `results/study_comp/`、`results/compcheck/` | ✅ |
| **Fig. S2** | 见 `paper/tables/FigS2_windowing_table.csv` + `Fig08_windowing.png` | 窗口技术详图与量化表 | `results/supp/window_table.csv` | ✅ |
| **Fig. S3** | `FigS3_speckle_cv.png` | **散斑统计六联**：(a) Part A 前提检验（$CV_{inst}\!\to\!1$、$R_{circ}\!\to\!0$、$K_V$）；(b) Part B 系综分布 vs 闭式；(c) Part D1 合成 i.i.d. 自洽对照；(d) Part D2 有效自由度 $N_{eff}$；(e) Part C 同实现斑图（分析窗 $\pm4$ mm）；(f) 分环包络 CV | `results/study_speckle/speckle.mat`（`pipeline/study/pa_study_speckle.m` v3，Part A/B/C/D）+ `paper/figures/_plot_figS3_speckle.py` | ✅ **2026-10-15 新绘**（$M$=128：闭式 $1/\sqrt{M}$=0.0884；实测 $CV(I_E)$=0.1111（1.26×）、$CV(I_{BS})$=1.4255（1.43×）；D1 合成对照 0.0874/0.9928 **命中闭式** ⇒ 偏差归因于**前提**（$N_{eff}$=80.3/128=0.63、62.5/128=0.49），非公式或代码；去相关长度 0.33 vs 0.13 mm，$\lambda/2$=0.15 mm。**P2 未被否证，不得用实测值替换闭式**） |

## 三、表格

| 表号 | 本目录文件 | 内容 | 状态 |
|---|---|---|---|
| **Table 1** | `paper/tables/Table01_literature_comparison.csv` | 相关方法文献对比（11 篇 ×9 列：逐通道运算 / 是否需解析信号 / 几何补偿 / 输出域 / 报告指标） | ✅ **2026-10-15 新增**（核验记录见 `paper/notes/Table1_refcheck_2026-10-15.md`） |
| **Table 2** | `paper/tables/Table02_ablation_summary.csv` | 预处理链消融（**D1 / D1² / D2′ / D2** 的宽度与对比度 + 两条消融差值） | ✅ **按逐组经验证配置重跑** |
| **Table 3** | `paper/tables/Table03_registry.csv` | 主要结果汇总（6 组自有，逐组经验证配置） | ✅ |
| **Table 4** | `paper/tables/Table04_datasets.csv` | 数据集总览（自有 6 组 + 外部 4 套，含经验证配置与角色） | ✅ **2026-10-14 新增** |
| **Table 5** | `paper/tables/Table05_arms_and_design.csv` | 三臂定义 / 公平约束 F1–F4 / 重复次数与网格规则（Protocol W） | ✅ **2026-10-14 新增** |
| **Table 6** | `paper/tables/Table06_cost_and_concentration.csv` | 算力成本（0.50×）+ DR / 能量集中度 / PSLR 增益 | ✅ **2026-10-14 新增** |
| **Table S1** | `paper/tables/TableS1_config_audit.csv` | 配置审计（Q8）：`f0_spec` / `f0_eff` / `f0_meas` / 两个比值 + 纳排 verdict 列 | ✅ **2026-10-14 新增** |

---

## 四、刷新图库的规范做法

图的**源头**永远在 `results/` 与 `data_ext/`（由 `pipeline/study/*.m` 与 `pipeline/study/_window_demo.py` 生成）。更新流程：

1. 改/跑源头脚本 → 新图落到 `results/…`；
2. 用 `paper/figures/` 的对应文件名**覆盖复制**（保持图号命名不变）；
3. 若图号或内容发生结构性变化，**同步更新本 README 与 `docs/13` §3.4**。

> 复核图号命名是否漂移：`ls paper/figures/` 的每一项都应能在上表查到。
