"""Reconcile the 2021 DataPoint Armenia exploration with the present paper.

Computes every number cited in the paper's Appendix ("Reconciling the 2021
DataPoint Armenia exploration") and in RECONCILIATION.md:

1. From the 2021 exploration's committed output artifact
   (data/dpa2021_gdp_per_capita.csv — copied verbatim from
   DataPoint-Armenia/Data-Econ, Synthetic_Control/GDP_per_capita.csv,
   blob 6630f1ab5189f43b58dc7575b618a82d2b971ee5, committed November 2021):
   the 2020 level-gap drop, the growth differential, and the
   Armenia-to-synthetic level ratio implied by that run's own numbers.

2. A cross-check refit of the 2021 scripts' `original_group` donor pool
   (Georgia, Estonia, Latvia, Lithuania, Moldova, Albania) with the same
   single-predictor specification those scripts used, on current WDI data.
   Baltic series are read from data/baltics_gdp_pc.csv (fetched from the
   World Bank API; re-fetched here if the file is missing).

Writes results/reconciliation.json.
"""

import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from pysyncon import Dataprep, Synth

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

# ---- 1. The 2021 committed artifact, read on its own terms -----------------

art = pd.read_csv(DATA / "dpa2021_gdp_per_capita.csv")
arm = art[art.country == "Armenia"].iloc[0]
syn = art[art.country == "Synthetic Armenia"].iloc[0]
col = "GDP_per_capita_2010_USD.{}"

a19, a20 = float(arm[col.format(2019)]), float(arm[col.format(2020)])
s19, s20 = float(syn[col.format(2019)]), float(syn[col.format(2020)])

# Donor pool and fitted weights as committed in the artifact itself
donor_rows = art[~art.country.isin(["Armenia", "Synthetic Armenia", "MSE"])]
donor_rows = donor_rows.dropna(subset=["country"])
weights_2021 = {
    r.country: float(r.Weights)
    for r in donor_rows.itertuples()
    if pd.notna(r.Weights) and float(r.Weights) > 0.001
}

artifact = {
    "n_donors": int(len(donor_rows)),
    "weights": weights_2021,
    "armenia_2019": a19,
    "armenia_2020": a20,
    "synthetic_2019": s19,
    "synthetic_2020": s20,
    "level_ratio_2019": a19 / s19,
    "gap_change_2020_usd": (a20 - s20) - (a19 - s19),
    "gap_change_pct_of_armenia_2019": 100 * ((a20 - s20) - (a19 - s19)) / a19,
    "armenia_growth_2020_pct": 100 * (a20 / a19 - 1),
    "synthetic_growth_2020_pct": 100 * (s20 / s19 - 1),
    "growth_differential_pp": 100 * (a20 / a19 - s20 / s19),
}
print("2021 artifact:",
      json.dumps({k: round(v, 2) if isinstance(v, float) else v
                  for k, v in artifact.items()}, indent=2))

# ---- 2. Cross-check: their original_group pool, their spec, current data ---

BALTICS = DATA / "baltics_gdp_pc.csv"
if not BALTICS.exists():
    url = ("https://api.worldbank.org/v2/country/EST;LVA;LTU/indicator/"
           "NY.GDP.PCAP.KD?date=1994:2024&format=json&per_page=500")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                payload = json.load(r)
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(4 * (attempt + 1))
    rows = payload[1]
    pd.DataFrame(
        {
            "country": [x["country"]["value"] for x in rows],
            "year": [int(x["date"]) for x in rows],
            "gdp_pc": [x["value"] for x in rows],
        }
    ).to_csv(BALTICS, index=False)

panel = pd.read_csv(DATA / "wdi_panel.csv")[["country", "year", "gdp_pc"]]
balt = pd.read_csv(BALTICS)
df = pd.concat([panel, balt], ignore_index=True)

DONORS = ["Georgia", "Estonia", "Latvia", "Lithuania", "Moldova", "Albania"]
df = df[df.country.isin(DONORS + ["Armenia"]) & df.year.between(1996, 2024)]
df = df.dropna()

dp = Dataprep(
    foo=df,
    predictors=["gdp_pc"],
    predictors_op="mean",
    dependent="gdp_pc",
    unit_variable="country",
    time_variable="year",
    treatment_identifier="Armenia",
    controls_identifier=DONORS,
    time_predictors_prior=range(1996, 2020),
    time_optimize_ssr=range(1996, 2020),
)
s = Synth()
s.fit(dataprep=dp)

w = s.weights()
wide = df.pivot_table(index="year", columns="country", values="gdp_pc")
syn_path = wide[DONORS] @ w.reindex(DONORS)
gap = wide["Armenia"] - syn_path
pre = gap.loc[1996:2019]

crosscheck = {
    "weights": {c: round(float(x), 3) for c, x in w[w >= 0.005].items()},
    "pre_rmspe": float(np.sqrt((pre**2).mean())),
    "pre_rmspe_pct_of_mean": float(
        100 * np.sqrt((pre**2).mean()) / wide["Armenia"].loc[1996:2019].mean()
    ),
    "residual_2019_pct": float(100 * gap[2019] / syn_path[2019]),
    "gaps_pct": {
        int(y): float(round(100 * gap[y] / syn_path[y], 2)) for y in range(2020, 2025)
    },
}
print("\noriginal_group cross-check:", json.dumps(crosscheck, indent=2))

with open(RESULTS / "reconciliation.json", "w") as f:
    json.dump({"artifact_2021": artifact, "original_group_crosscheck": crosscheck},
              f, indent=2)
print("\nwrote results/reconciliation.json")
