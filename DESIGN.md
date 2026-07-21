# Research design (locked)

This design was fixed *before* estimation. Locking it up front is deliberate:
it's the discipline that keeps the analysis honest and stops it drifting into
specification hunting (trying options until a dramatic result appears). Treat any
extension you build as a robustness test of this design, not a license to
redesign until the answer changes.

## Question
The effect of Armenia's 2020 **compound shock** — the Second Nagorno-Karabakh war
*and* COVID-19, treated jointly as one treatment — on real GDP per capita.

## Method
Synthetic control (Abadie and co-authors), via the `pysyncon` Python package.
A "synthetic Armenia" is built as a weighted average of donor countries chosen to
match Armenia's pre-2020 path; the post-2020 gap is the estimated effect.

## Outcome
GDP per capita, constant 2015 US$ (WDI `NY.GDP.PCAP.KD`), 1994–2024.

## Treatment year
2020 (first treated year). Pre-treatment optimization window: 2000–2019.

## Predictors
Pre-period (2000–2019) means of: investment/GDP, trade/GDP, CPI inflation,
population growth, and industry share; plus the lagged outcome at 2000, 2005,
2010, 2015, and 2019. (Industry share enters as its 2012–2019 mean for all units,
because Armenia's WDI industry series only starts in 2012 in the current vintage —
a documented consistency fix.)

## Donor pool
~30 small / lower-middle-income and transition economies. Countries with their
*own* large idiosyncratic 2020–24 shocks are excluded **by design**, so they
don't contaminate the counterfactual: Azerbaijan (same war), Lebanon (2019–20
collapse), Sri Lanka (2022 default), Belarus (2020 crisis), Ukraine & Russia
(2022 war), Myanmar (2021 coup), Turkey (currency crisis). A data-completeness
screen then drops donors with thin series. Georgia stays in the main pool but its
inclusion is treated as a first-order robustness question (it received the same
post-2022 Russian inflow as Armenia).

## Inference
In-space placebos: pretend each donor was "treated" in 2020, fit its own
synthetic control, and rank Armenia's post/pre error ratio against the whole
distribution to get a permutation p-value.

## Robustness (all reported, including the unflattering ones)
1. Georgia in vs. out of the pool.
2. Leave-one-out over positive-weight donors.
3. In-time placebo (a fake 2015 treatment) as a scale bar.
4. Tourism arrivals as a secondary outcome — *if* the data support it.

## Interpretation discipline
Because every donor also lived through COVID, the estimate is the *differential*
effect of Armenia's 2020, not "the war alone." The post-2022 gap is contaminated
by the Russian relocation boom and is **not** attributed to the 2020 treatment.
No "the war cost X%" claim beyond 2021 without heavy caveats.

## Data guidelines
Institutional sources only — World Bank (WDI), IMF, UN, OECD, Eurostat, or
official Armenian statistics (Armstat). Targeted API pulls only; the entire panel
is a few hundred KB. No bulk dumps, no unofficial mirrors or scraped aggregator
sites. Cite source + retrieval date for anything you add.
