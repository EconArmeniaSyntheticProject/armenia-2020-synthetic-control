# War and Pandemic as a Compound Shock: Synthetic Control Evidence from Armenia, 2020–2024

Synthetic control study of Armenia's 2020 compound shock — the 44-day Second
Nagorno-Karabakh war layered onto COVID-19 — on real GDP per capita (constant
2015 US$, World Bank WDI), with a 30-country donor pool, in-space placebo
inference, and a full robustness suite (Georgia in/out, leave-one-out, in-time
placebo). An independent project (EconArmeniaSyntheticProject) that builds on
and references an earlier 2021 exploration by the DataPoint Armenia Data &
Economics committee.

**Headline:** in 2020–21 Armenia tracks its synthetic counterfactual almost
exactly (gaps +0.9% / −0.2%; placebo p = 1.00 over that window — the least
deviant unit in the sample). From 2022 Armenia sits 5–8% above the
counterfactual, consistent with the post-2022 Russian relocation inflow, not
with the 2020 treatment; that gap triples without Georgia in the pool, and we
report the fragility as a finding.

> **Status — independent project (2026).** A standalone effort
> (EconArmeniaSyntheticProject), separate from DataPoint Armenia but building on
> and referencing their 2021 exploration: Gary V. with student contributors
> Luke, Shreyas, and Anirudh. The 2021 origin team (Nanneh C., Ruben D., and
> Gary V.) is credited as prior work; they have agreed to this framing. The
> repo is public so the team can show their work; external outputs (a deployed
> dashboard, Medium posts) still get Gary's OK before they go live. Student
> worklist: [ONBOARDING.md](ONBOARDING.md).


## Layout

```
paper.md          # paper source (pandoc markdown), incl. reconciliation appendix
paper.pdf         # compiled paper
ONBOARDING.md     # student worklist (Luke / Shreyas / Anirudh) + setup + guardrails
DESIGN.md         # the locked research design (predictors, donor pool, robustness)
RECONCILIATION.md # full reconciliation with the 2021 DataPoint exploration
code/fetch_wdi.py # pulls the WDI panel (World Bank API v2, ~130 KB total)
code/analysis.py  # fit, placebos, robustness, figures — the whole analysis
code/reconciliation_2021.py  # appendix numbers: 2021 artifact + pool cross-check
data/wdi_panel.csv
data/dpa2021_gdp_per_capita.csv  # verbatim copy of the 2021 exploration's output
                                 # (DataPoint-Armenia/Data-Econ, Synthetic_Control/
                                 # GDP_per_capita.csv, blob 6630f1ab)
data/baltics_gdp_pc.csv          # EST/LVA/LTU series for the pool cross-check
results/          # every number cited in the paper (CSV/JSON + run log)
figures/          # fig1–fig7 (PNG, 200 dpi)
```

## Rebuild

```bash
python3 -m venv .venv
.venv/bin/pip install "pysyncon==1.5.2" pandas matplotlib
.venv/bin/python code/fetch_wdi.py    # refetches WDI (results may shift with vintage)
.venv/bin/python code/analysis.py    # ~25 min: 4-setting optimizer grid × 30 placebos
PATH="/Library/TeX/texbin:$PATH" pandoc paper.md -o paper.pdf \
  --pdf-engine=pdflatex --number-sections
```

Data: World Bank World Development Indicators, retrieved 2026-07-03
(`NY.GDP.PCAP.KD`, `NE.GDI.TOTL.ZS`, `NE.TRD.GNFS.ZS`, `FP.CPI.TOTL.ZG`,
`SP.POP.GROW`, `NV.IND.TOTL.ZS`, `ST.INT.ARVL`), 33 countries × 1994–2024.
The committed `data/wdi_panel.csv` reproduces the paper exactly; a fresh fetch
may differ as the WDI vintage moves.
