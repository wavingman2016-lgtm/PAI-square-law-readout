# paper/tables — 表格状态索引

> **用途**：稿件表格的单一状态源。每张表登记「当前文件 / 口径 / 是否可用 / 来源脚本」。
> **纪律**：本目录只放**从源脚本导出**的表，不手工改数。口径不一致时，以 `../results/registry/registry.csv`、
> `../results/wire/_SUMMARY.csv`（批量汇总）与 `../results/wire/_SUMMARY_ablation.csv`（消融表）为准。
> 最后核对：2026-10-16。表号已按**正文首次引用顺序**重编号
> （旧 **5→1**、**4→2**、**3→3**、**1→4**、**2→5**；**6** 与 **Table S1** 不变）。

---

## 一、当前存在

| 表号 | 文件 | 内容 | 口径基准 | 状态 |
|---|---|---|---|---|
| **Table 1** | `Table01_literature_comparison.csv` | 相关方法文献对比（11 篇：逐通道运算 / 是否需解析信号 / 几何补偿 / 输出域 / 报告指标） | 文献整理（核验记录 `../notes/Table1_refcheck_2026-10-15.md`） | **可用**（2026-10-15 新增） |
| **Table 2** | `Table02_ablation_summary.csv` | 预处理链消融（D1 / D1² / D2′ / D2） | **逐组经验证配置** | **可用** |
| **Table 3** | `Table03_registry.csv` | 自有 6 组实测（ΔCNR/ΔgCNR/DR/QC） | **逐组经验证配置** | **可用** |
| **Table 4** | `Table04_datasets.csv` | 数据集总览（自有 6 组 + 外部 4 套，含经验证配置、角色、状态） | `docs/11` + `results/registry` | **可用**（2026-10-14 新增） |
| **Table 5** | `Table05_arms_and_design.csv` | 三臂定义 + 公平约束 F1–F4 + 重复次数/网格规则（Protocol W） | `docs/09` §2、`docs/12` | **可用**（2026-10-14 新增） |
| **Table 6** | `Table06_cost_and_concentration.csv` | 算力成本（0.50×，规范计时）+ DR / 能量集中度 / PSLR 增益 | `pa_study_advantage.m`（docs/09 §3.8.4） | **可用**（2026-10-14 新增） |
| **Table S1** | `TableS1_config_audit.csv` | 配置审计（Q8）：`f0_spec`/`f0_eff`/`f0_meas`/两个比值 + 纳排 verdict | `results/wire/_SUMMARY.csv` | **可用**（2026-10-14 新增） |
| Fig. S1 | `FigS1_equiv_table.csv` | 几何补偿 **EI↔LP** 等价（残差/Pearson） | `pa_supp_equiv.m` 输出 `results/supp/S1_equiv_table.csv` 的**入库副本**（5 列子集） | 可用（刷新见 §一注） |
| Fig. S2 | `FigS2_windowing_table.csv` | 窗口五档量化（完整性/清晰度/可读性） | `_window_demo.py` | 可用 |

**源脚本（单一事实源）**

| 表 | 生成器 | 逐组配置来源 |
|---|---|---|
| Table 3 | `pipeline/wire/pa_wire_run.m`（逐组跑） | `pipeline/wire/pa_wire_manifest.m` |
| Table 2 | **`pipeline/pa_run_wire_all.m`** → `results/wire/_SUMMARY_ablation.csv` | 同上 |
| Table S1 | 同上 → `results/wire/_SUMMARY.csv`（含 Q8 四列） | 同上 |
| Table 1 / 4 / 5 / 6 | 手工整理自上列权威结果；**数字须与 `results/` 逐值一致** | — |

> ⚠ 更正：旧版本文件把 Table 2（消融）的生成器写成 `pipeline/study/pa_study_comp.m`，**有误**。`pa_study_comp.m`
> 只做 **EI↔LP** 的等价性验证（对应 Fig. S1）。Table 2 的正确生成器是 `pa_run_wire_all.m`。

> ⚠ **Fig. S1 溯源（2026-10-16 更正，登记项 R9）**：`FigS1_equiv_table.csv` **不是**本目录直接生成的，
> 而是 `pipeline/study/pa_supp_equiv.m` 输出（`results/supp/S1_equiv_table.csv`，**9 列**）的
> **入库副本**（只取前 5 列：`spec,relmax,relL2,pearson,oneMinusRelSE_vs_img2`）。
> 链路：`pa_supp_equiv.m` → `results/supp/S1_equiv_table.csv` →【**手工复制**】→ `paper/tables/FigS1_equiv_table.csv`
> → `_normalize_tables.py` → `FigS1_equiv_readable.csv`（4 列可读视图）→ 装配为 **Table S2**。
> - **一致性核对（2026-10-16）**：入库副本前 5 列与 `results/supp/S1_equiv_table.csv` 前 5 列**逐位一致**，
>   故印刷表数值**不受影响**。
> - ⚠ 两者可**静默分叉**（无脚本生成入库副本）：**重跑 `pa_supp_equiv.m` 后，必须重新复制**该副本。
> - **本目录纪律不破**：入库副本**不手工改数**；如与源不一致，以 `results/supp/S1_equiv_table.csv` 为准并重新复制。

---

## 二、Table 2 的内容与口径（重要）

### 2.1 四路定义（消融对象）

| 记号 | 通道域信号 | 几何补偿 | 说明 |
|---|---|---|---|
| **D1** (`env`) | `abs(hilbert(x))` | `r` | 线性包络叠加 = 基线 $I_M$ |
| **D1²** (`env2`) | `abs(hilbert(x)).^2` | `r2` | **通道级**平方（Hilbert 路） |
| **D2′** (`sqlaw`) | `LPF(x.^2)` | `r` + `PostSquare` | **通道级**平方（**免-Hilbert** 路，正文主方法） |
| **D2** (`sq`) | `x.^2` | `r2` | 裸平方（缺低通/去直流 → 反例） |

> `PostSquare` 的语义：把**单通道贡献先平方再累加**，即 $\sum_m (w_m v_m)^2$ ——属**通道级**平方，**不是**图像域平方。

### 2.2 两条消融的读法

| 列 | 比较 | 期望 | 结论 |
|---|---|---|---|
| `dgCNR_D2p_vs_D1sq` | D2′ vs D1² | ≈ 0 | **免-Hilbert 等价性**：平方律检波 `LPF(x²)=½|z|²` 与 Hilbert 包络平方给出同一张图 |
| `dgCNR_D2p_vs_D2` | D2′ vs D2 | > 0 | **前置必要性**：不先做（逐通道去直流 +）窄带滤波就平方，对比度系统性下降 |

**实测（6 组，逐组经验证配置）**

- `dgCNR_D2p_vs_D1sq = 0.00000 × 6`；`pearson_sqlaw ≥ 0.9994`；`aFWHM_D2p` 与 `aFWHM_D1sq` 差 ≤ 0.4%
  → 免-Hilbert 实现与 Hilbert 参考**数值等价**（Lemma A 在自有数据上的验证）。
- `dgCNR_D2p_vs_D2` = **+0.0033 / +0.0083 / +0.0547 / +0.0828 / +0.2353 / +0.0747**（W1…W6，**六组全正**，均值 ≈ **+0.077**）
  → 低通（把分析带收到 $\beta_\text{law}=0.80<1$）**必要**；裸平方在本组数据上无一例外地损失对比度。
- 附注：D2 的 `aFWHM` 系统性**偏小**（如 W1 0.243 vs 0.542 mm）。这是**多峰分裂导致的假性收窄**，
  **不得**读作"分辨率提升"（见 `docs/08` 的分辨率定案）。

### 2.3 范围声明（避免越界引用）

1. **本条消融不含 D3**（保号平方 `sign(x)·x²`）。D3 是**非物理量**，统一管线不实现，仅存于归档的 A 族脚本
   （`archive/`），故不出现在 Table 2。
2. **图像域平方（$I_{BS}=I_C^2$）不在本表**。它是"单调双射、不构成方法贡献"的**对照**，其证据由
   `pa_study_comp.m`、`pa_patato_check.m` 与 **Fig. S1** 承担，不混入预处理链消融。
3. **本表不含任何 verdict / hardFail / softFail 列**。纳排判定是 **Table S1** 的职责；消融表只报指标。

### 2.4 两套 verdict 词汇（务必区分，勿混用）

| 词汇 | 出处 | 含义 | 用在 |
|---|---|---|---|
| `KEEP` / `REVIEW`（**G1–G4 纳排**） | `docs/08` §裁定 | G1 ΔCNR>0；G2 ΔgCNR≥−0.02；G3 满足前提 N 与 β<1；G4 Pearson≥0.90 | **Table 3 / Table S1** |
| `KEEP` / `REVIEW`（**`pa_qc` 报告**） | `pipeline/qc/pa_qc.m` | 硬失败 Q1/Q2/Q5 一票否决；软失败 Q4/Q6/Q7 只记 `REVIEW` | `results/wire/*_report.txt` |

> 二者**口径不同、可并存**。例：W3（data4）在 `pa_qc` 下为 `REVIEW`（Q4 视场**软**失败，边缘能量占比 0.347），
> 但在 G1–G4 纳排下 `KEEP`（ΔCNR +7.855、ΔgCNR +0.033、分析带 β=0.80、Pearson 1.0000）。
> **凡引用 verdict 必先声明是哪一套词汇。** 消融表（Table 2）通过"不含 verdict"彻底回避该歧义。

### 2.5 `beta` 列的口径

`beta` = **实测** −6 dB 带宽 ÷ **实测谱峰**（数据属性），**不是**分析带的 β。
分析带的合法性由 `D2p_exact` 列承载（`BandMode='spec'` 下按 $\beta_\text{law}=0.80$ 重建，故六组均为 1）。
故 `beta > 1` 与 `D2p_exact = 1` 并不矛盾，切勿互读。

---

## 三、待建（投稿前闭合）

| 表号 | 内容 | 依赖 | 状态 |
|---|---|---|---|
| ~~Table 1~~ | ~~与相关方法对比~~ | 文献整理 | ✅ **已闭合**（2026-10-15，见下） |

> 已建：**Table 1 / 4 / 5 / 6** 与 **Table S1**（Table 1 于 2026-10-15）。

### 3.1 Table 1 的口径（重要）

- **分组轴 =「每通道在求和之前被施加了什么运算」**，与正文 §2.1 的分类轴（`a_m = g_m z_m(τ_m)` 之后如何
  塌缩为标量）**同轴**。因此 Table 1 不是文献流水账，而是把正文的三臂放到同一坐标系里。
- **不做跨文献数值排名。** 跨论文的 PSNR / SSIM / gCNR 因真值定义、归一化、网格、噪声模型不同而不可比 ——
  这是 **F4 铁律在文献层面的延伸**。每行的 `reported_metrics` 只回答「该文报告了什么量」，不回答「谁更好」。
- 起草阶段的 `position_ours` 列**已从表中移除**（其内容留档于 `_Table01_moved_notes.md`，待改写进 §1.2 正文）；
  定位措辞**不写 superiority 形容词**。
- `geom_compensation` 只填该文明确声明的规则；未声明者写 `not stated`，**不填 `—`**（避免读作「无补偿」）。
- ⚠ **本表对本稿 claim 的收紧作用**：行 T1-05/T1-06 记录了 pDAS / DMAS 这两个**逐通道非线性先例**
  （`prakash2024tenalgo`）。因此正文 §1.2 已改写为「逐通道非线性本身并非新，本文的主张是
  **免 Hilbert** + **环阵断层几何** + **对两个参照臂的定量定价**」。**后续不得再写「首次逐通道非线性」。**
- ⚠ `zhang2021dudounet` 的 DOI / 页码 / 作者在 2026-10-15 修正过一次（`9433949` / `1522--1526` /
  第四作者 `Lyu T`）。**引用前请看 `../notes/Table1_refcheck_2026-10-15.md` 的核验来源。**

> ⚠ **编号冲突提示**：`docs/12` §4 曾把窗口量化表记作「Table 4a」。稿件中**不存在** Table 4a —— 窗口量化的
> 交付物是 **`FigS2_windowing_table.csv`（Fig. S2）**。为避免与本文档的 Table 2（消融）撞号，稿件引用窗口
> 量化时一律用 **Fig. S2**，不得写 "Table 4a"。

> ⚠ **Table S1 的双重身份**：`TableS1_config_audit.csv` 是 `results/wire/_SUMMARY.csv` 的副本，
> 因此**同时含 Q8 四列与纳排 verdict 列**。它在稿件中的定位是「配置审计表」；若最终排版需要一张纯纳排表，
> 从该文件裁列即可（**勿手工改数**）。
