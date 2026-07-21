# Reconciling the 2021 DataPoint exploration with the present paper

Gary's recollection: the original R work in `DataPoint-Armenia/Data-Econ/Synthetic_Control`
"showed something" — a visible 2020 war effect — seemingly contradicting this
paper's 2020–21 null. Investigated July 3, 2026 against the committed files
(commits of July 4 / Nov 1 / Nov 29, 2021). Verdict: **no contradiction — the
two analyses agree on the growth differential; the 2021 visual was an artifact
of a level-infeasible donor pool viewed through a one-year post-window.**

## What the 2021 repo actually contains

| File | Outcome | Shock year | Data end | Could it show a 2020 GDP effect? |
|---|---|---|---|---|
| `debt_synth_control2.R` | debt (`AdCSV`) | 2018 | 2019 | No — data pre-war |
| `synth_control_updated_data_ruben.R` | tourism, debt | 2016 | 2019 | No — data pre-war |
| `debt_synth_control3.R` (GDP block as committed) | GDP p.c. | 2017 | 2019 | No — pre-war window |
| `GDP_per_capita.csv` (committed **output** artifact) | GDP p.c., 2010 US$ | 2020 | 2020 | **Yes — this is the "something"** |
| `Rplot.png` | descriptive neighbors plot | — | ~2020 | Descriptive only |

The debt and tourism panels end in 2019, so no war-era analysis was possible on
those outcomes. The one artifact with 2020 data is `GDP_per_capita.csv`: the
saved output of a tidysynth run with a 15-donor pool of economies far poorer
than Armenia (the script's `top_10` list — Ethiopia, DR Congo, Sierra Leone,
Mozambique, CAR, Malawi, Niger, Madagascar, Rwanda, Nepal — plus Burundi,
Cambodia, Liberia, Myanmar, and Tajikistan), a single predictor (pre-period
outcome mean), and data through 2020. The artifact's fitted weights fall
entirely on **Cambodia (0.70) and Myanmar (0.30)**: its "Synthetic Armenia" row
is exactly 0.7×Cambodia + 0.3×Myanmar.

Two details worth knowing for the co-author conversation: Cambodia is also the
second-largest donor (0.28) in the paper's main specification — the two
analyses converge even on the donor; and Myanmar, 30 percent of the 2021
synthetic, is excluded from the paper's pool for its 2021 coup, which would
have contaminated any post-2020 extension of that run.

## Why that run looked like a war effect

From the committed artifact itself (2010 US$):

- 2019: Armenia 4,350 vs "Synthetic Armenia" **1,416** — the synthetic sits at
  **1/3 of Armenia's level** (fit MSE 40,823). Every donor is far poorer than
  Armenia, so no convex combination can reach its level; the "synthetic" is
  effectively a low-income-country growth index.
- 2020: the Armenia-minus-synthetic gap falls by **−$250**, i.e. −5.7% of
  Armenia's 2019 level. In `plot_differences()` that renders as Armenia falling
  visibly off its synthetic path in 2020 — the remembered result.
- But in **growth terms** the same artifact shows: Armenia −7.8%, synthetic
  −6.3% → a differential of only **−1.5 pp**. The dramatic dollar drop is
  mostly scale: at 3.1× the synthetic's level, a similar percentage fall
  mechanically produces a large absolute-gap drop.
- The window ended at 2020 (single post-year: no 2021 stabilization, no
  2022–24 boom), and no placebo benchmark showed whether a 2020 divergence of
  that size was unusual (in 2020, it was not — nearly every economy diverged
  from its pre-COVID synthetic).

## The punchline: the two analyses agree

| | 2021 exploration (their artifact) | This paper (main spec) |
|---|---|---|
| Armenia 2020 growth | −7.8% (2010 US$ vintage) | −7.2% (2015 US$ vintage) |
| Synthetic 2020 growth | −6.3% | −5.1% |
| **Growth differential** | **−1.5 pp** | **≈ −2.1 pp** |
| Level gap 2020 | −$250 swing (3× level mismatch) | +0.9% (level-feasible fit) |
| Post-window | 2020 only | 2020–2024 |
| Inference | none | 31-unit placebo ranking |

Both say the same thing: Armenia's 2020 was roughly 1.5–2 points worse than a
synthetic comparator in growth terms. The paper's placebo distribution then
shows a differential of that size is indistinguishable from pandemic-era noise
(Armenia is the *least* deviant of 31 units over 2020–21), and the 2021-vintage
data could not yet show the reversal that follows.

A cross-check built here (Baltic/Georgia/Moldova/Albania pool — the
`original_group` from the 2021 scripts — fitted on levels through 2019): the
optimizer puts the weight on Moldova/Georgia/Albania, and the 2020 gap comes
out **+3.0%**, not negative — Moldova fell as hard as Armenia in 2020. Even the
European-pool version of the 2021 exploration does not produce a war-sized loss
once the fit is level-feasible.

One correction to an earlier reading of this episode: the 2021 synthetic was
*not* a mild-pandemic counterfactual — its 2020 fall (−6.3%) was harsher than
the paper's (−5.1%). The remembered loss came from the 3× level mismatch (at
three times the synthetic's level, a similar percentage fall produces a large
absolute-gap drop) and from the window closing at the shock year, not from the
counterfactual's severity. In growth terms, the two analyses agree.

*Files examined: all of `Synthetic_Control/` at DataPoint-Armenia/Data-Econ
(scripts, committed CSVs, Rplot.png); Baltic series fetched from WDI for the
cross-check (~10 KB).*
