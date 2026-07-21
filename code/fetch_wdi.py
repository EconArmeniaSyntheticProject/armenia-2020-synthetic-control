"""Fetch World Bank WDI indicators for the Armenia synthetic control study.

Pulls Armenia + a candidate donor pool of comparable small/lower-middle-income
economies, 1994-2024, for the outcome (real GDP per capita) and standard growth
predictors. Writes one tidy CSV: data/wdi_panel.csv.

Donor candidates deliberately EXCLUDE countries with their own large
idiosyncratic shocks in 2020-2024 (Azerbaijan: same war; Lebanon: 2019-20
financial collapse; Sri Lanka: 2022 default; Belarus: 2020 political crisis;
Ukraine/Russia: 2022 war; Myanmar: 2021 coup; Turkey: 2018-23 currency crisis).

World Bank API v2 is public; no key required. The /country/all/ endpoint was
returning 502s, so countries are requested explicitly by ISO3 list.
"""

import json
import time
import urllib.request

import pandas as pd

INDICATORS = {
    "NY.GDP.PCAP.KD": "gdp_pc",          # GDP per capita, constant 2015 US$
    "NE.GDI.TOTL.ZS": "invest_gdp",      # gross capital formation, % GDP
    "NE.TRD.GNFS.ZS": "trade_gdp",       # trade, % GDP
    "FP.CPI.TOTL.ZG": "inflation",       # CPI inflation, annual %
    "SP.POP.GROW": "pop_growth",         # population growth, annual %
    "NV.IND.TOTL.ZS": "industry_gdp",    # industry value added, % GDP
    "ST.INT.ARVL": "tourism_arrivals",   # international tourism, number of arrivals
}

COUNTRIES = [
    "ARM",                                # treated
    # transition / post-Soviet / Balkans
    "GEO", "ALB", "MKD", "BIH", "SRB", "MDA", "KGZ", "TJK", "UZB", "KAZ", "MNG",
    # MENA / South & Southeast Asia
    "JOR", "MAR", "TUN", "EGY", "NPL", "KHM", "VNM", "PHL", "IDN",
    # Latin America
    "BOL", "PRY", "HND", "SLV", "GTM", "DOM", "ECU", "PER",
    # Sub-Saharan Africa
    "SEN", "GHA", "RWA", "KEN",
]

BASE = ("https://api.worldbank.org/v2/country/{codes}/indicator/{ind}"
        "?date=1994:2024&format=json&per_page=5000")


def fetch(indicator: str) -> pd.DataFrame:
    url = BASE.format(codes=";".join(COUNTRIES), ind=indicator)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                payload = json.load(r)
            if len(payload) < 2 or payload[1] is None:
                raise ValueError(f"empty payload for {indicator}")
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
    rows = payload[1]
    return pd.DataFrame(
        {
            "iso3": [r["countryiso3code"] for r in rows],
            "country": [r["country"]["value"] for r in rows],
            "year": [int(r["date"]) for r in rows],
            "value": [r["value"] for r in rows],
        }
    )


def main() -> None:
    merged = None
    for ind, name in INDICATORS.items():
        df = fetch(ind).rename(columns={"value": name})
        print(f"fetched {ind} -> {name}: {len(df)} rows")
        merged = df if merged is None else merged.merge(
            df, on=["iso3", "country", "year"], how="outer"
        )
    merged = merged.sort_values(["country", "year"])
    merged.to_csv("data/wdi_panel.csv", index=False)
    print(f"wrote data/wdi_panel.csv: {len(merged)} rows, "
          f"{merged['country'].nunique()} countries, "
          f"years {merged['year'].min()}-{merged['year'].max()}")


if __name__ == "__main__":
    main()
