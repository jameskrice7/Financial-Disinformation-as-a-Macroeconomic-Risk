"""Data acquisition and panel construction.

Sources
-------
* Digital Society Project (DSP) v8, country-year expert-coded indicators of
  the dissemination of false information (Mechkova et al., 2026 release).
* World Bank World Development Indicators (WDI) via the public v2 API.
* Worldwide Governance Indicators (WGI) via the same API.

The output is a single country-year panel, 2000-2025, saved to
``data/processed/panel.csv``.
"""

from __future__ import annotations

import json
import pathlib
import time

import numpy as np
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

WB_API = "https://api.worldbank.org/v2/country/all/indicator/{code}"

#: WDI series used in the panel (read from the bulk WDI_CSV archive).
WB_INDICATORS = {
    # outcome channels  k ∈ {G, N, I, T, F}
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",        # G: real GDP growth, %
    "inv_growth": "NE.GDI.FTOT.KD.ZG",        # N: real gross fixed capital formation growth, %
    "rd_gdp": "GB.XPD.RSDV.GD.ZS",            # N (level): R&D expenditure, % GDP
    "patents": "IP.PAT.RESD",                  # N (alt): resident patent applications
    "gini": "SI.POV.GINI",                     # I: Gini index
    "trade_gdp": "NE.TRD.GNFS.ZS",             # T: trade, % GDP
    "export_growth": "NE.EXP.GNFS.KD.ZG",      # T (outcome): real export growth, %
    "npl": "FB.AST.NPER.ZS",                   # F: bank non-performing loans, % gross loans
    "credit_gdp": "FS.AST.PRVT.GD.ZS",         # F (level): private credit, % GDP
    # controls Z
    "inflation": "FP.CPI.TOTL.ZG",             # CPI inflation, %
    "gdp_pc": "NY.GDP.PCAP.KD",                # GDP per capita, constant USD
    "pop": "SP.POP.TOTL",                      # population
    "fdi_gdp": "BX.KLT.DINV.WD.GD.ZS",         # FDI inflows, % GDP
}

#: WGI sheets (read from wgidataset.xlsx, 2023 update, 1996-2022).
WGI_SHEETS = {
    "gov_eff": "GovernmentEffectiveness",
    "reg_qual": "RegulatoryQuality",
    "voice": "VoiceandAccountability",
}

#: DSP components of the disinformation index.  Each is an expert-coded
#: measurement-model point estimate on an inverted frequency scale
#: (higher = false information disseminated *less* often), so all are
#: multiplied by -1 before aggregation.  Weights fixed ex ante.
DSP_COMPONENTS = {
    "v2smgovdom": 0.25,   # government dissemination of false info, domestic
    "v2smpardom": 0.25,   # major parties dissemination of false info, domestic
    "v2smfordom": 0.25,   # foreign governments dissemination of false info
    "v2smgovab": 0.125,   # government dissemination of false info, abroad
    "v2smparab": 0.125,   # parties dissemination of false info, abroad
}


def fetch_wb_indicator(code: str, start: int = 2000, end: int = 2025,
                       max_retries: int = 6) -> pd.DataFrame:
    """Download one indicator for all countries from the World Bank API.

    Paginated (two pages of 10k) to keep response sizes modest; cached
    per indicator under data/raw/wb_<code>.csv.
    """
    cache = RAW / f"wb_{code}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    url = WB_API.format(code=code)
    payload = None
    all_obs = []
    for page in (1, 2):
        params = {"format": "json", "per_page": 10000, "page": page,
                  "date": f"{start}:{end}"}
        for attempt in range(max_retries):
            try:
                r = requests.get(url, params=params, timeout=120)
                r.raise_for_status()
                payload = r.json()
                break
            except (requests.RequestException, json.JSONDecodeError):
                if attempt == max_retries - 1:
                    raise
                time.sleep(3 * (attempt + 1))
        if len(payload) >= 2 and payload[1]:
            all_obs.extend(payload[1])
        if page >= payload[0].get("pages", 1):
            break
    payload = [payload[0], all_obs]
    if len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["iso3", "year", "value"])
    rows = [
        {
            "iso3": obs["countryiso3code"],
            "year": int(obs["date"]),
            "value": obs["value"],
        }
        for obs in payload[1]
        if obs["countryiso3code"] and obs["value"] is not None
    ]
    df = pd.DataFrame(rows)
    df.to_csv(cache, index=False)
    return df


def fetch_wb_countries() -> pd.DataFrame:
    """Country metadata: region and income group (drops aggregates)."""
    r = requests.get(
        "https://api.worldbank.org/v2/country",
        params={"format": "json", "per_page": 400},
        timeout=60,
    )
    r.raise_for_status()
    rows = []
    for c in r.json()[1]:
        if c["region"]["id"] == "NA":  # aggregates
            continue
        rows.append(
            {
                "iso3": c["id"],
                "country": c["name"],
                "region": c["region"]["value"].strip(),
                "income": c["incomeLevel"]["value"].strip(),
            }
        )
    return pd.DataFrame(rows)


def load_wdi_bulk(start: int = 2000, end: int = 2025) -> pd.DataFrame:
    """Read the required indicators from the bulk WDI_CSV archive."""
    cache = RAW / "worldbank.csv"
    if cache.exists():
        return pd.read_csv(cache)
    codes = set(WB_INDICATORS.values())
    name_of = {v: k for k, v in WB_INDICATORS.items()}
    chunks = []
    for chunk in pd.read_csv(RAW / "WDI" / "WDICSV.csv", chunksize=50_000):
        sel = chunk[chunk["Indicator Code"].isin(codes)]
        if len(sel):
            chunks.append(sel)
    raw = pd.concat(chunks)
    years = [str(y) for y in range(start, end + 1) if str(y) in raw.columns]
    long = raw.melt(
        id_vars=["Country Code", "Indicator Code"], value_vars=years,
        var_name="year", value_name="value").dropna(subset=["value"])
    long["year"] = long["year"].astype(int)
    long["name"] = long["Indicator Code"].map(name_of)
    wide = long.pivot_table(index=["Country Code", "year"], columns="name",
                            values="value").reset_index()
    wide = wide.rename(columns={"Country Code": "iso3"})
    wide.columns.name = None
    wide.to_csv(cache, index=False)
    return wide


def load_wgi() -> pd.DataFrame:
    """Parse the WGI Excel file (wide layout: years x fields from row 15)."""
    cache = RAW / "wgi.csv"
    if cache.exists():
        return pd.read_csv(cache)
    xl = pd.ExcelFile(RAW / "wgidataset.xlsx")
    out = None
    for name, sheet in WGI_SHEETS.items():
        raw = xl.parse(sheet, header=None, skiprows=13)
        years = raw.iloc[0].ffill()
        fields = raw.iloc[1]
        data = raw.iloc[2:]
        recs = []
        for j in range(2, raw.shape[1]):
            if str(fields.iloc[j]).strip() == "Estimate":
                yr = int(years.iloc[j])
                block = pd.DataFrame({
                    "iso3": data.iloc[:, 1].astype(str).str.strip(),
                    "year": yr,
                    name: pd.to_numeric(data.iloc[:, j], errors="coerce"),
                })
                recs.append(block)
        sheet_df = pd.concat(recs).dropna(subset=[name])
        out = sheet_df if out is None else out.merge(
            sheet_df, on=["iso3", "year"], how="outer")
    # WGI uses a few non-ISO3 codes (e.g. ADO for Andorra); harmonize majors
    fix = {"ADO": "AND", "ZAR": "COD", "ROM": "ROU", "TMP": "TLS",
           "WBG": "PSE", "KSV": "XKX"}
    out["iso3"] = out["iso3"].replace(fix)
    out.to_csv(cache, index=False)
    return out


def load_wdi_country_meta() -> pd.DataFrame:
    """Region/income metadata from the bulk archive (drops aggregates)."""
    c = pd.read_csv(RAW / "WDI" / "WDICountry.csv")
    c = c[c["Region"].notna()][["Country Code", "Short Name", "Region",
                                "Income Group"]]
    return c.rename(columns={"Country Code": "iso3", "Short Name": "country",
                             "Region": "region", "Income Group": "income"})


def load_dsp() -> pd.DataFrame:
    """Load DSP v8 country-year file and keep index components."""
    path = RAW / "DigitalSocietyProject-v8-CSV" / "DSP_CY_v8.csv"
    df = pd.read_csv(path, low_memory=False)
    keep = ["country_name", "country_text_id", "year"] + list(DSP_COMPONENTS)
    df = df[keep].rename(columns={"country_text_id": "iso3",
                                  "country_name": "country_dsp"})
    return df


def build_m_index(dsp: pd.DataFrame) -> pd.DataFrame:
    """Construct the disinformation intensity index M in (0,1).

    Steps (fixed ex ante, Section 4 of the paper):
    1. invert each DSP component so that higher = more disinformation;
    2. z-score each component over the full panel;
    3. weighted average with fixed simplex weights;
    4. map to (0,1) by the probability integral transform (empirical CDF),
       shrunk to [1/(2n), 1-1/(2n)] so logit(M) is finite.
    """
    out = dsp[["iso3", "country_dsp", "year"]].copy()
    z = pd.DataFrame(index=dsp.index)
    for comp, w in DSP_COMPONENTS.items():
        x = -dsp[comp]                        # invert: higher = more disinfo
        z[comp] = w * (x - x.mean()) / x.std()
    score = z.sum(axis=1, skipna=False)
    out["disinfo_score"] = score
    n = score.notna().sum()
    ranks = score.rank(method="average")
    out["M"] = (ranks - 0.5) / n              # in (0,1) strictly
    out["logitM"] = np.log(out["M"] / (1 - out["M"]))
    return out


def build_panel(force: bool = False) -> pd.DataFrame:
    """Merge DSP index, WDI/WGI, and metadata into the estimation panel."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    cache = PROCESSED / "panel.csv"
    if cache.exists() and not force:
        return pd.read_csv(cache)

    wb = load_wdi_bulk()
    wgi = load_wgi()
    meta = load_wdi_country_meta()
    m = build_m_index(load_dsp())

    panel = m.merge(wb, on=["iso3", "year"], how="inner")
    panel = panel.merge(wgi, on=["iso3", "year"], how="left")
    panel = panel.merge(meta, on="iso3", how="left")
    panel = panel[panel["region"].notna()]
    # extend slow-moving governance scores through the panel end
    panel = panel.sort_values(["iso3", "year"])
    for col in ["gov_eff", "reg_qual", "voice"]:
        panel[col] = panel.groupby("iso3")[col].ffill()
    panel = panel.sort_values(["iso3", "year"]).reset_index(drop=True)

    # spillover: leave-one-out regional mean of logit(M), same year
    g = panel.groupby(["region", "year"])["logitM"]
    panel["spill"] = (g.transform("sum") - panel["logitM"]) / (
        g.transform("count") - 1
    )

    # interpolate slow-moving series within country (levels used as
    # conditioning states, never as outcomes)
    for col in ["gini", "rd_gdp", "credit_gdp", "npl"]:
        panel[col + "_i"] = (
            panel.groupby("iso3")[col].transform(
                lambda s: s.interpolate(limit_direction="both")
            )
        )

    panel.to_csv(cache, index=False)
    return panel


if __name__ == "__main__":
    p = build_panel(force=True)
    print(p.shape)
    print(p[["M", "gdp_growth", "trade_gdp", "npl", "gov_eff"]].describe())
