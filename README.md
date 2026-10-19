# Reproduction archive: squared-amplitude read-out in photoacoustic imaging

Version tag: `PAI-v0.48`

This archive accompanies the manuscript *Square-law detection before back-projection in
photoacoustic imaging: squared-amplitude read-out, apparent profile narrowing and
computational trade-offs* (submitted to **Photoacoustics**).

The directory layout mirrors the table and figure numbering of the manuscript, so that
every number, table and figure can be traced to the script that produced it.

```
paper/manuscript/   build pipeline, probes and the manuscript source
paper/tables/       table sources (*.csv) and the script that writes them
paper/figures/      figure scripts and the rendered *.png files
paper/analysis/     standalone analyses (threshold interval, order statistics)
pipeline/           MATLAB acquisition / reconstruction code (pa_run_wire_all entry point)
results/            derived CSV and JSON summaries read by the tables and figures
```

## Entry points

| what | command |
|---|---|
| rebuild every table, the assembled manuscript and the DOCX | `python paper/manuscript/_round.py` |
| run the full delivery self-check | `python paper/manuscript/_submission_check_v048.py` |
| regenerate one figure | `python paper/figures/_plot_fig_v033_sim.py` |
| acquisition-to-image pipeline (MATLAB R2025b) | `pa_run_wire_all` (see `pipeline/wire/pa_wire_manifest.m`) |

## What is *not* in this archive

* The six in-house acquisitions (W1-W6) and the external datasets. They are not
  redistributed here; see the Data availability statement of the manuscript.
* The manuscript text itself, including the assembled markdown. Keeping it out makes the
  commit hash quoted in the manuscript stable: the code tree does not change when the
  prose does.
* The one-off `_patch*.py` scripts under `pipeline/study/`. They edited internal working
  notes and produce no number, table or figure.

## Paths

No absolute path is hard-coded. Every script resolves the repository root from its own
location (`__file__` in Python, `mfilename('fullpath')` in MATLAB), so a fresh clone runs
from wherever it is unpacked. Folders that are not in this archive (`docs/`, the raw
acquisitions) are still referenced by the historical scripts; those scripts are kept for
traceability, not as entry points.

## Note on the commit identity

The commits in this archive were made with a neutral builder identity
(`PAI archive <archive@localhost>`) and a fixed commit date, so that the commit hash
quoted in the manuscript is reproducible from the deposited tree. Re-committing with a
personal identity will change the hash.

## Licence

MIT -- see `LICENSE`. The derived data deposit that accompanies this archive is
released separately under CC BY 4.0.
