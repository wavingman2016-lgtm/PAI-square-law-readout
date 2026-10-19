# Table 1 删掉的 `position_ours` 起草注（待改写进 §1.2 正文）

> **存档**：`position_ours` 列在表规范化时从 `Table01_literature_comparison.csv` 移除，
> 内容留档于此，供 §1.2 正文改写时取用。编号已按 2026-10-16 的表号重编
> （旧 **T5-xx → T1-xx**，与正文 Table 1 对齐）。
>
> ⚠ **数值口径已更新，引用前务必核对正文**：T1-01 原写「C 比 E 锐 ~4–7×」，
> 现定为 **≈6.5×**（全文三处已改，见 §5.2 与 Fig. 3）；一切宽度类说法以 §5.2 为准。
> （2026-10-16 修复：本文件曾被 `_normalize_tables.py` 的幂等缺陷清空，现由
> `_rollback/PAI-thesis-round-v13/.../Table05_literature_comparison.csv` 找回重建。）

- **T1-01** (Xu & Wang 2005 (UBP); Kruger et al. 1995 (PAUS); Beard 2011 (review)) — Textbook default and the primary baseline C. The coherent sum keeps a cross term, so its transverse point spread is ~5x sharper than M and ~4-7x sharper than E - and it is the arm whose cost E reduces to 0.50x (canonical timing, Table 6)
- **T1-02** (Pramanik 2014) — A refinement of the coherent sum (apodisation). It changes the kernel, not the aggregation statistics, so it does not remove the cross term.
- **T1-03** (Rosenthal et al. 2010) — Out of scope by construction (see manuscript 5.4): it targets quantitative inversion rather than a detection-domain image. Listed to mark the boundary of the compared family, not as a competitor.
- **T1-04** (Xu et al. 2004) — The reference handling of missing angular span. Our E arm does not regularise the view; it prices the estimator under the same truncated geometry and reports the span dependence additively (bandwidth x view separation).
- **T1-05** (Prakash et al. 2024) — IMPORTANT: precedent for per-channel nonlinear operation. This work does not claim to introduce per-channel nonlinearity; its claim is a Hilbert-free channel-wise square with one analytic scale factor, a single geometric rule, and a priced comparison against two reference arms.
- **T1-06** (Prakash et al. 2024) — Second precedent for per-channel nonlinearity in the same survey. Multiplicative rather than quadratic, and evaluated on a linear array rather than a tomographic ring - so neither of our two claims (Hilbert-free energy domain, tomographic geometry) is covered by it.
- **T1-07** (Prakash et al. 2024 (MV, EIGMV, SLSC, GSC)) — A linear post-weighting family. Grouped here at family level - the four mechanisms differ and are not compared individually in our experiments.
- **T1-08** (Yang et al. 2021 (review); Grohl et al. 2021 (review); Zhang et al. 2021 (DuDoUNet)) — No learned baseline is claimed or run. We cite this family to delimit it: its reported numbers are not comparable to ours because truth definitions, normalisation, grids and noise models differ (F4 at the literature level).
- **T1-09** (Lin et al. 2021; 3D-PACT) — Cited as compute context for our 0.50x canonical timing claim, and as the reason our timing protocol states warm-up count, repetition count, mean +/- SD and hardware metadata.
- **T1-10** (Omar et al. 2019) — Cited for the in-vivo evidence route (PATATO mouse, RSOM human skin). Acquisition geometry is not the object of this comparison; our in-vivo numbers are reported with per-dataset verified configuration.
- **T1-11** (squared envelope with band-limiting) — Position: Hilbert-free energy-domain back-projection, priced against two reference arms. Buys separability and computation against C; buys dynamic range and energy concentration against M at unchanged separability; pays a broader transverse point spread and 6-8 dB SNR, and fails first under strong coherent clutter.
