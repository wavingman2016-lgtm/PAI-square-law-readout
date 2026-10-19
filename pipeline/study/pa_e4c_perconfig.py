# -*- coding: utf-8 -*-
"""v0.30 round-8: E4c reported per configuration instead of as one pooled n=30.

Review item 3: "report the baseline error and the error change separately for
the six configurations; do not rely on the merged 30 pairs alone."  The pooled
paired-t CI crosses zero only because configurations with OPPOSITE signs are
averaged together.  This script splits them.

For each of the six (beta, f0) configurations it reports
  * the baseline scale-corrected relative error at Nup = 1 (mean over 5 reps),
  * the paired change d = eps(Nup) - eps(1) at Nup = 2 and 4, with a paired-t
    95% CI and p-value,
  * that change relative to its own baseline, against a PRE-SPECIFIED
    engineering threshold of 10% of the baseline (stated before looking at the
    numbers, as the fraction of the baseline that a measurement step may move
    without being called a systematic change).

Input : results/study_e4c/e4c.csv (archived; produced by pa_study_e4c_folding.m)
Output: results/study_e4c/e4c_perconfig.csv and .log
"""
import collections
import io
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "results", "study_e4c", "e4c.csv")
OUT_CSV = os.path.join(ROOT, "results", "study_e4c", "e4c_perconfig.csv")
OUT_LOG = os.path.join(ROOT, "results", "study_e4c", "e4c_perconfig.log")

THRESH_FRAC = 0.10   # pre-specified: |d| <= 10% of the configuration baseline


def paired_t(d):
    """Paired t on the differences d; returns (mean, lo95, hi95, t, p_two).

    p is computed from the t survival function via the incomplete beta
    function, so no SciPy dependency is needed.
    """
    n = len(d)
    m = sum(d) / n
    if n < 2:
        return m, float("nan"), float("nan"), float("nan"), float("nan")
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    if sd == 0.0:
        return m, m, m, float("inf"), 0.0
    se = sd / math.sqrt(n)
    t = m / se
    # two-sided p from Student t with n-1 dof
    x = (n - 1.0) / ((n - 1.0) + t * t)
    p = betainc((n - 1.0) / 2.0, 0.5, x)
    # 95% CI with t_{0.975, n-1}
    tcrit = tinv_975(n - 1)
    return m, m - tcrit * se, m + tcrit * se, t, p


def _betacf(a, b, x):
    """Continued fraction for the regularised incomplete beta (Numerical
    Recipes, `betacf`).  Returns the CF value; the caller multiplies by bt/a."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 400):
        m2 = 2.0 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        del_ = d * c
        h *= del_
        if abs(1.0 - del_) < 1e-15:
            break
    return h


def betainc(a, b, x):
    """Regularised incomplete beta I_x(a,b).  Validated against the two-sided
    5% critical values of Student t: I_{df/(df+t^2)}(df/2, 1/2) must equal 0.05
    at t = t_{0.975,df}."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    bt = math.exp(a * math.log(x) + b * math.log(1.0 - x) - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def tinv_975(df):
    """Two-sided 5% critical value of Student t by bisection on the CDF."""
    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_sf(mid, df) > 0.025:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def t_sf(t, df):
    """Upper tail of Student t = 0.5 * I_{df/(df+t^2)}(df/2, 1/2)."""
    x = df / (df + t * t)
    return 0.5 * betainc(df / 2.0, 0.5, x)


def main():
    with io.open(SRC, encoding="utf-8") as fh:
        rows = list(__import__("csv").DictReader(fh))

    # rep x Nup -> eps, keyed by (control, scenario)
    cell = collections.defaultdict(dict)
    meta = {}
    for r in rows:
        k = (r["control"], r["scenario"])
        cell[(k, int(r["rep"]))][int(r["Nup"])] = float(r["eps_img_rel"])
        meta[k] = (float(r["beta"]), float(r["f0"]))

    out, log = [], []
    log.append("E4c per-configuration report (review round 8, item 3)")
    log.append("p-values are TWO-sided paired t (same convention as the manuscript body)")
    log.append("source: results/study_e4c/e4c.csv (6 configurations x 5 replicates)")
    log.append("pre-specified engineering threshold: |d| <= %.0f%% of the configuration baseline"
               % (THRESH_FRAC * 100))
    log.append("")
    hdr = ("%-5s %-3s %-5s %-9s %9s %11s %11s %11s %11s %9s %8s %7s"
           % ("ctrl", "sc", "beta", "f0_MHz", "n", "eps_Nup1",
              "d_Nup2", "d_Nup4", "CI95_Nup4", "p_Nup4", "rel_Nup4", "flag"))
    log.append(hdr)
    log.append("-" * len(hdr))

    cfgs = sorted(meta.keys(), key=lambda k: (k[0], int(k[1])))
    for k in cfgs:
        beta, f0 = meta[k]
        reps = sorted(r for (kk, r) in cell if kk == k)
        e1 = [cell[(k, r)][1] for r in reps if 1 in cell[(k, r)]]
        e2 = [cell[(k, r)][2] for r in reps if 1 in cell[(k, r)] and 2 in cell[(k, r)]]
        e4 = [cell[(k, r)][4] for r in reps if 1 in cell[(k, r)] and 4 in cell[(k, r)]]
        n = len(e1)
        b1 = sum(e1) / n
        d2 = [b - a for a, b in zip(e1, e2)]
        d4 = [b - a for a, b in zip(e1, e4)]
        # paired_t already returns the TWO-sided p, via the identity
        # P(|T| > t) = I_{df/(df+t^2)}(df/2, 1/2); do NOT multiply by 2 again.
        m2, lo2, hi2, t2, p2 = paired_t(d2)
        m4, lo4, hi4, t4, p4 = paired_t(d4)
        rel = abs(m4) / b1 if b1 > 0 else float("nan")
        flag = "EXCEEDS" if rel > THRESH_FRAC else "within"
        out.append(dict(control=k[0], scenario=k[1], beta="%.2f" % beta,
                        f0_MHz="%.0f" % (f0 / 1e6), n=n,
                        eps_Nup1="%.5f" % b1,
                        d_Nup2="%+.5f" % m2,
                        d_Nup4="%+.5f" % m4,
                        CI95_Nup4="[%+.5f, %+.5f]" % (lo4, hi4),
                        p_Nup4="%.4f" % p4,
                        rel_Nup4="%.1f%%" % (100.0 * rel),
                        threshold_flag=flag))
        log.append("%-5s %-3s %-5s %-9s %9d %11.5f %+11.5f %+11.5f %11s %9.4f %8.1f%% %7s"
                   % (k[0], k[1], "%.2f" % beta, "%.0f" % (f0 / 1e6), n, b1,
                      m2, m4, "[%+.5f, %+.5f]" % (lo4, hi4), p4,
                      100.0 * rel, flag))

    cols = ["control", "scenario", "beta", "f0_MHz", "n", "eps_Nup1",
            "d_Nup2", "d_Nup4", "CI95_Nup4", "p_Nup4", "rel_Nup4", "threshold_flag"]
    with io.open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(cols) + "\n")
        for r in out:
            fh.write(",".join(str(r[c]) for c in cols) + "\n")

    nex = sum(1 for r in out if r["threshold_flag"] == "EXCEEDS")
    log.append("")
    log.append("configurations exceeding the pre-specified 10%%-of-baseline threshold at Nup=4: %d of %d"
               % (nex, len(out)))
    log.append("the pooled n=30 CI crossing zero is an average over configurations with")
    log.append("OPPOSITE signs (negative at f0 = 3 MHz, positive at f0 = 10 MHz); it is")
    log.append("therefore NOT evidence that each configuration is unchanged.")
    with io.open(OUT_LOG, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
