"""Synthetic control analysis: Armenia's 2020 compound shock (war + COVID-19).

Implements the locked design in PLAN.md:
  - Outcome: GDP per capita, constant 2015 US$ (WDI NY.GDP.PCAP.KD), 2000-2024.
  - Treatment year: 2020 (first treated year); pre-period 2000-2019.
  - Predictors: pre-period means of investment/GDP, trade/GDP, CPI inflation,
    population growth, industry share + lagged outcome at 2000/2005/2010/2015/2019.
  - Inference: in-space placebos, post/pre RMSPE-ratio permutation p-value.
  - Robustness: Georgia in/out, leave-one-out, in-time placebo (2015),
    tourism arrivals as secondary outcome if the data supports it.

Reads data/wdi_panel.csv (from code/fetch_wdi.py). Writes numbers to results/
and figures to figures/. Every number cited in the paper is saved here.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pysyncon import Dataprep, Synth

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "wdi_panel.csv"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
RESULTS.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)

TREAT_YEAR = 2020
PRE_YEARS = range(2000, 2020)
POST_YEARS = range(2020, 2025)
ALL_YEARS = range(2000, 2025)
OUTCOME = "gdp_pc"
# Armenia's industry-share series (NV.IND.TOTL.ZS) only starts in 2012 in the
# current WDI vintage, so industry share enters as a special predictor averaged
# over the consistent window 2012-2019 for ALL units; the other predictors are
# 2000-2019 means as planned.
PREDICTORS = ["invest_gdp", "trade_gdp", "inflation", "pop_growth"]
INDUSTRY_START = 2012
LAG_YEARS = [2000, 2005, 2010, 2015, 2019]

LOG_LINES = []


def log(msg: str) -> None:
    print(msg)
    LOG_LINES.append(str(msg))


# ---------------------------------------------------------------- EDA / donor screen


def load_and_screen():
    df = pd.read_csv(DATA)
    df = df[df["year"].isin(ALL_YEARS)].copy()

    rows = []
    for c, g in df.groupby("country"):
        g = g.set_index("year")
        outcome_missing = [
            y for y in ALL_YEARS if y not in g.index or pd.isna(g.loc[y, OUTCOME])
        ]
        pred_cover = {
            p: int(g.loc[g.index.isin(PRE_YEARS), p].notna().sum()) for p in PREDICTORS
        }
        pred_cover["industry_gdp"] = int(
            g.loc[g.index.isin(range(INDUSTRY_START, 2020)), "industry_gdp"]
            .notna()
            .sum()
        )
        rows.append(
            {
                "country": c,
                "outcome_missing_2000_2024": len(outcome_missing),
                "outcome_missing_years": ",".join(map(str, outcome_missing)),
                **{f"{p}_n_pre": n for p, n in pred_cover.items()},
                "tourism_n_pre": int(
                    g.loc[g.index.isin(PRE_YEARS), "tourism_arrivals"].notna().sum()
                )
                if "tourism_arrivals" in g.columns
                else 0,
                "tourism_last_year": int(g.loc[g["tourism_arrivals"].notna()].index.max())
                if "tourism_arrivals" in g.columns
                and g["tourism_arrivals"].notna().any()
                else np.nan,
            }
        )
    eda = pd.DataFrame(rows).sort_values("country")
    eda.to_csv(RESULTS / "eda_completeness.csv", index=False)

    # Screen: complete outcome 2000-2024; every predictor >= 10 of 20 pre-years.
    keep, dropped = [], []
    for _, r in eda.iterrows():
        c = r["country"]
        if r["outcome_missing_2000_2024"] > 0:
            dropped.append((c, f"outcome gaps: {r['outcome_missing_years']}"))
            continue
        thin = [p for p in PREDICTORS if r[f"{p}_n_pre"] < 10]
        if r["industry_gdp_n_pre"] < 6:
            thin.append("industry_gdp")
        if thin:
            dropped.append(
                (c, "thin predictors (<10 pre-years): "
                    + ", ".join(f"{p}={r[f'{p}_n_pre']}" for p in thin))
            )
            continue
        keep.append(c)

    log(f"EDA: {len(keep)} countries pass screen; {len(dropped)} dropped:")
    for c, why in dropped:
        log(f"  dropped {c}: {why}")
    if "Armenia" not in keep:
        sys.exit("FATAL: Armenia fails the completeness screen")

    # Sanity: Armenia 2020 dip visible in raw data.
    arm = df[df["country"] == "Armenia"].set_index("year")[OUTCOME]
    dip = 100 * (arm[2020] / arm[2019] - 1)
    log(f"Sanity: Armenia raw gdp_pc 2019={arm[2019]:.1f}, 2020={arm[2020]:.1f} "
        f"({dip:+.2f}%), 2024={arm[2024]:.1f}")
    if dip > -2:
        sys.exit("FATAL: expected clear 2020 dip in Armenia's raw series")

    donors = sorted(c for c in keep if c != "Armenia")
    return df, donors


# ---------------------------------------------------------------- fitting helpers


def make_dataprep(df, treated, controls, treat_year, lag_years=None):
    pre = range(2000, treat_year)
    lags = lag_years if lag_years is not None else LAG_YEARS
    industry_window = range(INDUSTRY_START, treat_year)
    return Dataprep(
        foo=df,
        predictors=PREDICTORS,
        predictors_op="mean",
        dependent=OUTCOME,
        unit_variable="country",
        time_variable="year",
        treatment_identifier=treated,
        controls_identifier=list(controls),
        time_predictors_prior=pre,
        time_optimize_ssr=pre,
        special_predictors=[("industry_gdp", industry_window, "mean")]
        + [(OUTCOME, [y], "mean") for y in lags if y < treat_year],
    )


def fit_best(dataprep):
    """Fit over a small grid of optimizer settings; keep the lowest pre-treatment
    RMSPE of the outcome (computed directly from the outcome matrices)."""
    Z0, Z1 = dataprep.make_outcome_mats()
    best, best_loss, best_tag = None, np.inf, None
    for method in ("Nelder-Mead", "BFGS"):
        for initial in ("equal", "ols"):
            try:
                s = Synth()
                s.fit(dataprep=dataprep, optim_method=method, optim_initial=initial)
                pre_rmspe = float(np.sqrt(np.mean(np.square(Z1 - Z0 @ s.W))))
                if pre_rmspe < best_loss:
                    best, best_loss, best_tag = s, pre_rmspe, f"{method}/{initial}"
            except Exception as e:  # noqa: BLE001 - log and try next setting
                log(f"  optimizer {method}/{initial} failed: {e}")
    if best is None:
        raise RuntimeError("all optimizer settings failed")
    return best, best_tag


def series_and_gap(df, synth, treated, donors_used):
    """Return (treated series, synthetic series, gap) over 2000-2024."""
    years = list(ALL_YEARS)
    wide = df.pivot_table(index="year", columns="country", values=OUTCOME).loc[years]
    w = synth.weights()
    w = w[w.index.isin(donors_used)]
    synth_path = wide[w.index] @ w
    treated_path = wide[treated]
    return treated_path, synth_path, treated_path - synth_path


def rmspe(gap, years):
    g = gap.loc[list(years)]
    return float(np.sqrt(np.mean(np.square(g))))


# ---------------------------------------------------------------- main


def main():
    import importlib.metadata

    log(f"pysyncon {importlib.metadata.version('pysyncon')}, "
        f"pandas {pd.__version__}, numpy {np.__version__}")
    df, donors = load_and_screen()
    log(f"Donor pool (main spec, Georgia included): {len(donors)} donors")
    log(", ".join(donors))

    # ---- main fit
    dp = make_dataprep(df, "Armenia", donors, TREAT_YEAR)
    synth, tag = fit_best(dp)
    log(f"Main fit: best optimizer setting {tag}, loss_W={synth.loss_W:.6f}")

    arm, syn, gap = series_and_gap(df, synth, "Armenia", donors)
    pre_r = rmspe(gap, PRE_YEARS)
    post_r = rmspe(gap, POST_YEARS)
    log(f"Main pre-RMSPE (2000-19): {pre_r:.2f} | post-RMSPE (2020-24): {post_r:.2f} "
        f"| ratio: {post_r / pre_r:.2f}")
    log(f"Armenia mean gdp_pc 2000-19: {arm.loc[list(PRE_YEARS)].mean():.1f} "
        f"(pre-RMSPE is {100 * pre_r / arm.loc[list(PRE_YEARS)].mean():.2f}% of it)")

    weights = synth.weights().sort_values(ascending=False)
    weights.to_csv(RESULTS / "weights.csv", header=["weight"])
    log("Weights (>=0.01):")
    for c, w in weights[weights >= 0.01].items():
        log(f"  {c}: {w:.3f}")

    # Donor-level 2020 per-capita growth (cited in the paper's war-years and
    # discussion paragraphs; saved so every paper number traces to results/)
    wide_g = df.pivot_table(index="year", columns="country", values=OUTCOME)
    g2020 = (100 * (wide_g.loc[2020] / wide_g.loc[2019] - 1)).rename("growth_2020_pct")
    g2020[["Armenia"] + donors].round(2).to_csv(RESULTS / "growth_2020.csv")
    donor_g = g2020[donors]
    log(f"2020 pc growth: Armenia {g2020['Armenia']:+.2f}%, donor mean "
        f"{donor_g.mean():+.2f}%, min {donor_g.min():+.2f}% ({donor_g.idxmin()}), "
        f"max {donor_g.max():+.2f}% ({donor_g.idxmax()})")

    # Predictor balance table
    X0, X1 = dp.make_covariate_mats()
    balance = pd.DataFrame(
        {
            "Armenia": X1,
            "Synthetic": X0 @ synth.W,
            "Donor mean": X0.mean(axis=1),
        }
    )
    balance.to_csv(RESULTS / "balance.csv")
    log("Predictor balance:\n" + balance.to_string())

    # Gap table with percent
    out = pd.DataFrame(
        {"armenia": arm, "synthetic": syn, "gap": gap, "gap_pct": 100 * gap / syn}
    )
    out.to_csv(RESULTS / "main_series.csv")
    for y in [2020, 2021, 2022, 2023, 2024]:
        log(f"  {y}: Armenia={arm[y]:.1f} synth={syn[y]:.1f} "
            f"gap={gap[y]:+.1f} ({100 * gap[y] / syn[y]:+.2f}%)")
    att_2021 = float(gap.loc[[2020, 2021]].mean())
    att_full = float(gap.loc[list(POST_YEARS)].mean())
    cum_loss_21 = float(gap.loc[[2020, 2021]].sum())
    log(f"ATT 2020-21: {att_2021:+.1f} | ATT 2020-24: {att_full:+.1f} "
        f"| cumulative 2020-21 gap: {cum_loss_21:+.1f}")

    # ---- in-space placebos (own loop: per-donor ratios + windowed p-values)
    log("\nIn-space placebos:")
    placebo_gaps = {}
    ratios = []
    for d in donors:
        try:
            controls = [c for c in donors if c != d]
            dpd = make_dataprep(df, d, controls, TREAT_YEAR)
            sd, _ = fit_best(dpd)
            _, _, g = series_and_gap(df, sd, d, controls)
            placebo_gaps[d] = g
            ratios.append(
                {
                    "unit": d,
                    "pre_rmspe": rmspe(g, PRE_YEARS),
                    "post_rmspe": rmspe(g, POST_YEARS),
                    "post_rmspe_2021": rmspe(g, [2020, 2021]),
                }
            )
            log(f"  placebo {d}: pre={ratios[-1]['pre_rmspe']:.1f} "
                f"post={ratios[-1]['post_rmspe']:.1f}")
        except Exception as e:  # noqa: BLE001
            log(f"  placebo {d} FAILED: {e}")

    ratios.append(
        {
            "unit": "Armenia",
            "pre_rmspe": pre_r,
            "post_rmspe": post_r,
            "post_rmspe_2021": rmspe(gap, [2020, 2021]),
        }
    )
    rat = pd.DataFrame(ratios)
    rat["ratio"] = rat["post_rmspe"] / rat["pre_rmspe"]
    rat["ratio_2021"] = rat["post_rmspe_2021"] / rat["pre_rmspe"]
    rat = rat.sort_values("ratio", ascending=False).reset_index(drop=True)
    rat.to_csv(RESULTS / "placebo_ratios.csv", index=False)

    n_units = len(rat)
    rank_full = int((rat["ratio"] >= rat.loc[rat.unit == "Armenia", "ratio"].iloc[0]).sum())
    rank_2021 = int(
        (rat["ratio_2021"] >= rat.loc[rat.unit == "Armenia", "ratio_2021"].iloc[0]).sum()
    )
    p_full = rank_full / n_units
    p_2021 = rank_2021 / n_units
    log(f"Placebo p-values ({n_units} units incl. Armenia): "
        f"full post 2020-24 p={p_full:.3f} (rank {rank_full}); "
        f"2020-21 window p={p_2021:.3f} (rank {rank_2021})")

    pd.DataFrame(placebo_gaps).to_csv(RESULTS / "placebo_gaps.csv")

    # ---- robustness 1: Georgia out
    log("\nRobustness: Georgia excluded")
    donors_nog = [d for d in donors if d != "Georgia"]
    dp_nog = make_dataprep(df, "Armenia", donors_nog, TREAT_YEAR)
    synth_nog, tag_nog = fit_best(dp_nog)
    arm2, syn_nog, gap_nog = series_and_gap(df, synth_nog, "Armenia", donors_nog)
    pre_nog = rmspe(gap_nog, PRE_YEARS)
    log(f"  optimizer {tag_nog}; pre-RMSPE={pre_nog:.2f}")
    for y in [2020, 2021, 2022, 2023, 2024]:
        log(f"  {y}: gap={gap_nog[y]:+.1f} ({100 * gap_nog[y] / syn_nog[y]:+.2f}%)")
    wn = synth_nog.weights().sort_values(ascending=False)
    wn.to_csv(RESULTS / "weights_no_georgia.csv", header=["weight"])
    log("  weights (>=0.01): "
        + ", ".join(f"{c}={w:.3f}" for c, w in wn[wn >= 0.01].items()))
    pd.DataFrame(
        {"synthetic_no_georgia": syn_nog, "gap_no_georgia": gap_nog,
         "gap_pct_no_georgia": 100 * gap_nog / syn_nog}
    ).to_csv(RESULTS / "series_no_georgia.csv")

    # ---- robustness 2: leave-one-out over positive-weight donors
    log("\nRobustness: leave-one-out (donors with weight >= 0.01)")
    loo_paths = {}
    for d in weights[weights >= 0.01].index:
        try:
            controls = [c for c in donors if c != d]
            dpl = make_dataprep(df, "Armenia", controls, TREAT_YEAR)
            sl, _ = fit_best(dpl)
            _, syn_l, gap_l = series_and_gap(df, sl, "Armenia", controls)
            loo_paths[d] = syn_l
            log(f"  without {d}: pre-RMSPE={rmspe(gap_l, PRE_YEARS):.2f}, "
                f"gap2020={gap_l[2020]:+.1f}, gap2021={gap_l[2021]:+.1f}")
        except Exception as e:  # noqa: BLE001
            log(f"  LOO without {d} FAILED: {e}")
    pd.DataFrame(loo_paths).to_csv(RESULTS / "loo_paths.csv")

    # ---- robustness 3: in-time placebo, fake treatment 2015
    log("\nRobustness: in-time placebo (fake treatment 2015, fit 2000-2014)")
    dp_t = make_dataprep(df, "Armenia", donors, 2015, lag_years=[2000, 2005, 2010, 2014])
    synth_t, tag_t = fit_best(dp_t)
    _, syn_t, gap_t = series_and_gap(df, synth_t, "Armenia", donors)
    pre_t = rmspe(gap_t, range(2000, 2015))
    fake_post = rmspe(gap_t, range(2015, 2020))
    log(f"  optimizer {tag_t}; pre-RMSPE(2000-14)={pre_t:.2f}, "
        f"fake-post RMSPE(2015-19)={fake_post:.2f}, ratio={fake_post / pre_t:.2f}")
    for y in range(2015, 2020):
        log(f"  {y}: gap={gap_t[y]:+.1f} ({100 * gap_t[y] / syn_t[y]:+.2f}%)")
    pd.DataFrame({"synthetic_2015": syn_t, "gap_2015": gap_t}).to_csv(
        RESULTS / "series_intime2015.csv"
    )

    # ---- robustness 4: tourism arrivals as secondary outcome (if data supports)
    tourism_ok = False
    t = df.pivot_table(index="year", columns="country", values="tourism_arrivals")
    arm_t = t.get("Armenia")
    if arm_t is not None:
        arm_cover_pre = arm_t.reindex(list(PRE_YEARS)).notna().sum()
        arm_post_years = [y for y in POST_YEARS if y in arm_t.index and pd.notna(arm_t.get(y))]
        good_donors = [
            d for d in donors
            if d in t.columns
            and t[d].reindex(list(PRE_YEARS)).notna().sum() >= 18
            and all(pd.notna(t[d].get(y)) for y in arm_post_years)
        ]
        log(f"\nTourism check: Armenia pre-coverage {arm_cover_pre}/20, "
            f"post years available {arm_post_years}, qualifying donors {len(good_donors)}")
        if arm_cover_pre >= 18 and len(arm_post_years) >= 2 and len(good_donors) >= 15:
            tourism_ok = True
            years_t = [y for y in ALL_YEARS if y < TREAT_YEAR or y in arm_post_years]
            df_t = df[df["country"].isin(good_donors + ["Armenia"])].copy()
            df_t = df_t[df_t["year"].isin(years_t)]
            df_t["log_tourism"] = np.log(df_t["tourism_arrivals"])
            dp_tour = Dataprep(
                foo=df_t.dropna(subset=["log_tourism"]),
                predictors=["log_tourism"],
                predictors_op="mean",
                dependent="log_tourism",
                unit_variable="country",
                time_variable="year",
                treatment_identifier="Armenia",
                controls_identifier=good_donors,
                time_predictors_prior=range(2000, 2020),
                time_optimize_ssr=range(2000, 2020),
                special_predictors=[
                    ("log_tourism", [y], "mean") for y in [2005, 2010, 2015, 2019]
                ],
            )
            synth_tour, tag_tour = fit_best(dp_tour)
            wt = t.loc[[y for y in years_t]][good_donors]
            wlog = np.log(wt)
            w_tour = synth_tour.weights()
            w_tour = w_tour[w_tour.index.isin(good_donors)]
            syn_tour = wlog[w_tour.index] @ w_tour
            arm_tour = np.log(arm_t.reindex(years_t))
            gap_tour = arm_tour - syn_tour
            pd.DataFrame(
                {"log_arm": arm_tour, "log_synth": syn_tour, "gap_log": gap_tour}
            ).to_csv(RESULTS / "series_tourism.csv")
            log(f"  tourism fit ({tag_tour}); pre-RMSPE(log)="
                f"{rmspe(gap_tour.dropna(), [y for y in PRE_YEARS if y in gap_tour.dropna().index]):.3f}")
            for y in arm_post_years:
                log(f"  {y}: log-gap={gap_tour[y]:+.3f} (~{100 * (np.exp(gap_tour[y]) - 1):+.1f}%)")
        else:
            log("  tourism data does NOT support a credible secondary fit -> skipped")
    else:
        log("\nTourism check: no Armenia series -> skipped")

    # ---------------------------------------------------------------- figures
    plt.rcParams.update({"figure.dpi": 200, "font.size": 10})
    years = list(ALL_YEARS)

    # Fig 1: path
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(years, arm.loc[years], "k-", lw=1.8, label="Armenia")
    ax.plot(years, syn.loc[years], "k--", lw=1.6, label="Synthetic Armenia")
    ax.axvline(2019.5, color="gray", ls=":", lw=1)
    ax.text(2019.2, ax.get_ylim()[0] + 100, "2020 shock", fontsize=9,
            color="gray", ha="right")
    ax.set_xlabel("Year")
    ax.set_ylabel("GDP per capita (constant 2015 US$)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig1_path.png")
    plt.close(fig)

    # Fig 2: gap
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(years, gap.loc[years], "k-", lw=1.8)
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(2019.5, color="gray", ls=":", lw=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Gap: Armenia − synthetic (constant 2015 US$)")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig2_gap.png")
    plt.close(fig)

    # Fig 3: placebo gaps (exclude placebos with pre-RMSPE > 5x Armenia's)
    cutoff = 5 * pre_r
    shown, excluded = [], []
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for d, g in placebo_gaps.items():
        if rmspe(g, PRE_YEARS) > cutoff:
            excluded.append(d)
            continue
        shown.append(d)
        ax.plot(years, g.loc[years], color="0.75", lw=0.8)
    ax.plot(years, gap.loc[years], "k-", lw=2.0, label="Armenia")
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(2019.5, color="gray", ls=":", lw=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Gap: unit − its synthetic control (constant 2015 US$)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig3_placebo_gaps.png")
    plt.close(fig)
    log(f"\nPlacebo figure: {len(shown)} placebos shown, "
        f"{len(excluded)} excluded (pre-RMSPE > 5x Armenia's): {excluded}")

    # Fig 4: Georgia in vs out (gap overlay)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(years, gap.loc[years], "k-", lw=1.8, label="Main (Georgia in pool)")
    ax.plot(years, gap_nog.loc[years], "k--", lw=1.6, label="Georgia excluded")
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(2019.5, color="gray", ls=":", lw=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Gap: Armenia − synthetic (constant 2015 US$)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig4_georgia.png")
    plt.close(fig)

    # Fig 5: leave-one-out paths
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(years, arm.loc[years], "k-", lw=1.8, label="Armenia")
    ax.plot(years, syn.loc[years], "k--", lw=1.6, label="Synthetic (main)")
    first = True
    for d, sp in loo_paths.items():
        ax.plot(years, sp.loc[years], color="0.7", lw=0.8,
                label="Leave-one-out synthetics" if first else None)
        first = False
    ax.axvline(2019.5, color="gray", ls=":", lw=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("GDP per capita (constant 2015 US$)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig5_loo.png")
    plt.close(fig)

    # Fig 6: in-time placebo (plot only to 2019 to keep it clean of the real shock)
    yrs_t = list(range(2000, 2020))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(yrs_t, arm.loc[yrs_t], "k-", lw=1.8, label="Armenia")
    ax.plot(yrs_t, syn_t.loc[yrs_t], "k--", lw=1.6,
            label="Synthetic (fit 2000–2014)")
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(5))
    ax.axvline(2014.5, color="gray", ls=":", lw=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("GDP per capita (constant 2015 US$)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig6_intime2015.png")
    plt.close(fig)

    # Fig 7: donor weights, main specification (repo artifact; weights are
    # reported in prose and results/weights.csv in the paper itself)
    wpos = weights[weights >= 0.005].sort_values()
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.barh(wpos.index, wpos.values, color="0.4")
    ax.set_xlabel("Donor weight (main specification)")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig7_weights.png")
    plt.close(fig)

    # Fig 8: tourism (only if fit)
    if tourism_ok:
        yrs_tour = [y for y in years_t]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(yrs_tour, arm_tour.loc[yrs_tour], "k-", lw=1.8, label="Armenia")
        ax.plot(yrs_tour, syn_tour.loc[yrs_tour], "k--", lw=1.6, label="Synthetic Armenia")
        ax.axvline(2019.5, color="gray", ls=":", lw=1)
        ax.set_xlabel("Year")
        ax.set_ylabel("log international tourist arrivals")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(FIGURES / "fig8_tourism.png")
        plt.close(fig)

    # ---------------------------------------------------------------- key numbers
    key = {
        "n_donors_main": len(donors),
        "optimizer_main": tag,
        "pre_rmspe": pre_r,
        "pre_rmspe_pct_of_mean": 100 * pre_r / float(arm.loc[list(PRE_YEARS)].mean()),
        "post_rmspe": post_r,
        "rmspe_ratio": post_r / pre_r,
        "gap_2020": float(gap[2020]),
        "gap_2020_pct": float(100 * gap[2020] / syn[2020]),
        "gap_2021": float(gap[2021]),
        "gap_2021_pct": float(100 * gap[2021] / syn[2021]),
        "gap_2022": float(gap[2022]),
        "gap_2022_pct": float(100 * gap[2022] / syn[2022]),
        "gap_2023": float(gap[2023]),
        "gap_2023_pct": float(100 * gap[2023] / syn[2023]),
        "gap_2024": float(gap[2024]),
        "gap_2024_pct": float(100 * gap[2024] / syn[2024]),
        "att_2020_21": att_2021,
        "att_2020_24": att_full,
        "cum_gap_2020_21": cum_loss_21,
        "p_full_post": p_full,
        "p_2020_21": p_2021,
        "n_placebo_units": n_units,
        "placebo_rank_full": rank_full,
        "placebo_rank_2021": rank_2021,
        "placebo_fig_shown": len(shown),
        "placebo_fig_excluded": excluded,
        "weights_main": {c: round(float(w), 4) for c, w in weights[weights >= 0.005].items()},
        "weights_no_georgia": {c: round(float(w), 4) for c, w in wn[wn >= 0.005].items()},
        "pre_rmspe_no_georgia": pre_nog,
        "gap_2020_no_georgia": float(gap_nog[2020]),
        "gap_2020_pct_no_georgia": float(100 * gap_nog[2020] / syn_nog[2020]),
        "gap_2021_no_georgia": float(gap_nog[2021]),
        "gap_2021_pct_no_georgia": float(100 * gap_nog[2021] / syn_nog[2021]),
        "intime_pre_rmspe": pre_t,
        "intime_fake_post_rmspe": fake_post,
        "intime_ratio": fake_post / pre_t,
        "tourism_fitted": tourism_ok,
    }
    with open(RESULTS / "key_numbers.json", "w") as f:
        json.dump(key, f, indent=2)

    (RESULTS / "run_log.txt").write_text("\n".join(LOG_LINES) + "\n")
    log("\nDONE. Outputs in results/ and figures/.")


if __name__ == "__main__":
    main()
