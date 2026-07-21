# Student guide — Armenia 2020 synthetic control

An economics + data-science project for Luke, Shreyas, and Anirudh.

## What this is

In 2020 Armenia was hit by two things at once: a 44-day war and COVID-19. This
project measures the economic effect using the **synthetic control** method —
you build a "model Armenia" out of a weighted mix of other countries that had
COVID but no war, then compare real Armenia to it.

A finished study already lives in this repo ([paper.pdf](paper.pdf)). It
continues and recreates earlier research on the same question. **Your job: first
recreate it, then extend it.** All three of you do the same steps, each on your
own — then we combine your work into one updated paper you're all authors on.

You each pick *different* variables, so at the end we can see how well the result
holds up across three independent takes. That's why all three of you do the whole
thing instead of splitting it up.

## Rules (short and important)

1. **Don't chase a dramatic result.** The study finds that the war left no clear,
   measurable dent in Armenia's yearly GDP once you account for COVID — and it
   says so honestly. You add variables to *test* that finding, never to
   manufacture a big "war cost X%" number. (Doing the latter is called p-hacking;
   it's bad science.)
2. **Report what you actually get** — even if it's boring, or disagrees with a
   teammate. That's a real result.
3. **Use AI to help, but own your work.** You're expected to use AI tools. But
   anything with your name on it, you must understand and be able to explain
   without the AI in front of you.
4. **The repo is public** (so you can show it off), but **don't publish anything
   externally** — a live dashboard, a Medium post — until Gary says go.
5. **Official data sources only:** World Bank (WDI), IMF, UN, OECD, or official
   Armenian statistics (Armstat). Nothing scraped or from random sites.

## The steps — each of you does all six

Work on your own branch (`git checkout -b analysis-yourname`) and keep everything
you make in your own folder, `analyses/yourname/`.

### Step 1 — Set up and recreate the study
- Install [git](https://git-scm.com/) and Python 3.9+.
- In the repo folder, run:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install "pysyncon==1.5.2" pandas matplotlib
  .venv/bin/python code/analysis.py     # ~25 min; regenerates results/ and figures/
  ```
- Open `results/key_numbers.json` and check your numbers **match what's already
  in the repo**. The analysis is deterministic, so they should match exactly. If
  they don't, find out why before moving on.

**Done when:** you've regenerated the figures and your `key_numbers.json` matches.

### Step 2 — Understand it
- Read [paper.pdf](paper.pdf) all the way through.
- Read [code/analysis.py](code/analysis.py) with the paper open beside it, and
  match each result in the paper to the code that produces it.
- Read [DESIGN.md](DESIGN.md) (the research design) and
  [RECONCILIATION.md](RECONCILIATION.md) (how an earlier version *looked* like it
  found a big war effect that turned out to be a mistake — read this carefully).
- Write **one paragraph**: what did the study find, and why is the jump in
  Armenia's economy after 2022 *not* counted as a war effect? Send it to Gary.

**Done when:** Gary okays your paragraph. (If you can write it, you get it.)

### Step 3 — Add your own economic variables
- Pick **3 economic indicators** you think matter for Armenia — each *different
  from your teammates'* (coordinate first). Good candidates (check the exact WDI
  code and that Armenia + the donor countries have data 2000–2019):
  - Personal remittances, % of GDP — `BX.TRF.PWKR.DT.GD.ZS`
  - Gross savings, % of GDP — `NY.GNS.ICTR.ZS`
  - FDI net inflows, % of GDP — `BX.KLT.DINV.WD.GD.ZS`
  - Government consumption, % of GDP — `NE.CON.GOVT.ZS`
  - (or find your own — say why it matters)
- Add your indicators to [code/fetch_wdi.py](code/fetch_wdi.py), re-pull the data,
  and re-run the model with them included.
- Write a short note (`analyses/yourname/findings.md`): **does the 2020–21 result
  stay the same with your variables? How much does it move?**

**Done when:** `analyses/yourname/` has your code changes and your findings note.

### Step 4 — Explore the data + build a simple dashboard
- Make these plots for your variables and save them in your folder:
  1. A data-completeness check (which countries have missing years).
  2. Armenia vs. the donor countries over time, for each of your variables.
- Build a small **Streamlit** dashboard (`pip install streamlit`) that shows:
  1. the path chart (Armenia vs. model Armenia),
  2. the gap chart, and
  3. a toggle to include/exclude Georgia.
  Read the numbers from the CSV files in `results/` so it runs instantly.

**Done when:** `streamlit run` opens your dashboard locally and the three views work.

### Step 5 — Write a Medium post
- ~800–1,200 words, in plain English, for your own Medium account. Cover: what
  the project is, what you explored, what you found, and be honest about it.
- Save the draft as `analyses/yourname/writeup.md`. **Do not publish it yet** —
  Gary reviews first.

**Done when:** your draft is in your folder.

### Step 6 — Combine (with Gary)
- We put the three of your extensions side by side, note where they agree and
  differ, and add a short section to the paper reporting it.
- You finalize your name and a one-line description of what you did in the paper.

## How you become an author
Your name goes on the paper when your work from Steps 3–5 makes it into the
combined paper. Steps 1–2 (recreating and understanding it) are the starting
point, not the finish line. This is how real research teams work.

## A note on your name in the paper
The repo is public, so keep your name to **first name + last initial** (for
example, `Luke S.`) in the byline. Do **not** put your full name.

## Where things live

| Path | What it is |
|---|---|
| `paper.md` / `paper.pdf` | the paper (source and compiled) |
| `code/analysis.py` | the whole analysis — model, robustness, figures |
| `code/fetch_wdi.py` | pulls the World Bank data |
| `data/` | the data |
| `results/` | every number the paper uses (CSV/JSON) |
| `figures/` | the paper's figures |
| `analyses/yourname/` | **your** work goes here |
| `DESIGN.md` | the research design |
| `RECONCILIATION.md` | the earlier-version cautionary tale — read it |

Questions → Gary. Welcome aboard.
