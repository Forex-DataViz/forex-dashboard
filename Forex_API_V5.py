import os
import json
import time
import requests
import pandas as pd
from datetime import date, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

start_time = time.perf_counter()

# ─────────────────────────────────────────
# API KEYS
# ─────────────────────────────────────────
EIA_KEY = os.environ.get("EIA_API_KEY") or "8TLbbSy091BfkECZ90zw25x5sYX0E5KC1HDoMPox"
FRED_KEY = os.environ.get("FRED_API_KEY") or "ceb305d9fe791b51a084d4f62a6c1e95"

if not EIA_KEY:
    raise Exception("Missing EIA_API_KEY environment variable.")
if not FRED_KEY:
    raise Exception("Missing FRED_API_KEY environment variable.")

# ─────────────────────────────────────────
# GET LATEST FOREX DATE
# ─────────────────────────────────────────
def get_latest_date():
    for i in range(5):
        check_date = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        url = f"https://api.frankfurter.app/{check_date}?from=USD&to=PHP"
        response = requests.get(url).json()
        if "rates" in response:
            return check_date
    return None

latest = get_latest_date()

if latest is None:
    raise Exception("No latest forex data available.")

# ─────────────────────────────────────────
# FOREX - Daily USD/PHP only
# ─────────────────────────────────────────
print("Fetching Daily Forex...")

url_usd = f"https://api.frankfurter.app/2000-01-01..{latest}?from=USD&to=PHP"

df_usd = pd.DataFrame.from_dict(
    requests.get(url_usd).json()["rates"], orient="index"
).rename(columns={"PHP": "USD_to_PHP"})

df_fx = df_usd.copy()
df_fx.index = pd.to_datetime(df_fx.index)
df_fx["Year"] = df_fx.index.year

# ─────────────────────────────────────────
# WORLD BANK DATA
# ─────────────────────────────────────────
def world_bank(country, indicator, col_name):
    print(f"Fetching World Bank: {col_name}...")

    url = (
        f"http://api.worldbank.org/v2/country/{country}"
        f"/indicator/{indicator}?format=json&per_page=20000"
    )

    try:
        data = requests.get(url).json()[1]

        return pd.DataFrame([
            {"Year": int(d["date"]), col_name: d["value"]}
            for d in data if d["value"] is not None
        ]).set_index("Year")

    except Exception as e:
        print(f"Error fetching {col_name}: {e}")
        return pd.DataFrame()

GDP_IND = "NY.GDP.MKTP.KD.ZG"
FDI_IND = "BX.KLT.DINV.CD.WD"
CPI_IND = "FP.CPI.TOTL.ZG"

wb_data = [
    world_bank("US", GDP_IND, "US_GDP"),
    world_bank("PH", GDP_IND, "PH_GDP"),
    world_bank("US", FDI_IND, "US_FDI"),
    world_bank("PH", FDI_IND, "PH_FDI"),
    world_bank("US", CPI_IND, "US_Inflation"),
    world_bank("PH", CPI_IND, "PH_Inflation"),
]

wb_final = wb_data[0].join(wb_data[1:])

# ─────────────────────────────────────────
# EIA OIL PRICES
# ─────────────────────────────────────────
def get_oil_prices():
    print("Fetching EIA Oil Prices...")

    url = (
        f"https://api.eia.gov/v2/petroleum/pri/spt/data/"
        f"?api_key={EIA_KEY}"
        f"&frequency=monthly"
        f"&data[0]=value"
        f"&facets[series][]=RBRTE"
        f"&start=2000-01"
        f"&sort[0][column]=period"
        f"&sort[0][direction]=asc"
        f"&offset=0&length=5000"
    )

    try:
        response = requests.get(url).json()
        records = response["response"]["data"]

        df = pd.DataFrame([
            {"Date": r["period"], "Brent_Crude_Oil_Price": r["value"]}
            for r in records if r["value"] is not None
        ])

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

        return df

    except Exception as e:
        print(f"Error fetching EIA oil prices: {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────
# FRED US POLICY RATE
# ─────────────────────────────────────────
def get_fred(series_id, col_name):
    print(f"Fetching FRED: {col_name}...")

    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}"
        f"&api_key={FRED_KEY}"
        f"&file_type=json"
        f"&observation_start=2000-01-01"
    )

    try:
        response = requests.get(url).json()

        if "observations" not in response:
            print(f"No observations for {col_name}: {response.get('error_message', 'unknown error')}")
            return pd.DataFrame()

        records = response["observations"]

        df = pd.DataFrame([
            {"Date": r["date"], col_name: float(r["value"])}
            for r in records if r["value"] != "."
        ])

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
        df = df.resample("ME").mean()

        return df

    except Exception as e:
        print(f"Error fetching {col_name}: {e}")
        return pd.DataFrame()

oil = get_oil_prices()
us_rate = get_fred("FEDFUNDS", "US_Policy_Rate")

# ─────────────────────────────────────────
# BSP POLICY RATE
# ─────────────────────────────────────────
def get_bsp_policy_rate():
    print("Fetching BSP Policy Rate from Excel...")

    try:
        df = pd.read_excel(
            "MonetaryPolicyDecisions.xlsx",
            sheet_name="Sheet1",
            header=1
        )

        df.columns = ["Date", "Description"]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])

        df["PH_Policy_Rate"] = (
            df["Description"]
            .str.extract(r'(?:to|at)\s+([\d.]+)\s+percent', expand=False)
            .astype(float)
        )

        df = df.dropna(subset=["PH_Policy_Rate"])
        df = df[["Date", "PH_Policy_Rate"]].set_index("Date").sort_index()
        df = df.resample("D").ffill()

        return df

    except Exception as e:
        print(f"Error loading BSP policy rate: {e}")
        return pd.DataFrame()

ph_rate = get_bsp_policy_rate()

# ─────────────────────────────────────────
# BSP GIR
# ─────────────────────────────────────────
def get_bsp_monthly_gir():
    print("Fetching BSP Monthly GIR data...")

    url = "https://www.bsp.gov.ph/Statistics/sdds/table12_data.aspx"

    try:
        try:
            tables = pd.read_html(url, flavor="lxml")
        except Exception:
            tables = pd.read_html(url)

        gir_df = None

        for table in tables:
            if table.shape[1] >= 2:
                gir_df = table
                break

        if gir_df is None:
            print("GIR table not found.")
            return pd.DataFrame()

        gir_df = gir_df.dropna(subset=[gir_df.columns[0]])

        cols = list(gir_df.columns)
        cols[0] = "Date"
        cols[1] = "GIR_Million_USD"
        gir_df.columns = cols

        gir_df = gir_df[["Date", "GIR_Million_USD"]].copy()

        gir_df["GIR_Million_USD"] = pd.to_numeric(
            gir_df["GIR_Million_USD"], errors="coerce"
        )

        gir_df = gir_df.dropna(subset=["GIR_Million_USD"])

        gir_df["BSP_Gross_International_Reserves"] = (
            gir_df["GIR_Million_USD"] / 1000
        ).round(2)

        gir_df["Date"] = pd.to_datetime(gir_df["Date"], errors="coerce")
        gir_df = gir_df.dropna(subset=["Date"])

        gir_df = gir_df[["Date", "BSP_Gross_International_Reserves"]]
        gir_df = gir_df.set_index("Date").sort_index()

        return gir_df

    except Exception as e:
        print(f"Error fetching BSP GIR: {e}")
        return pd.DataFrame()

gir_monthly = get_bsp_monthly_gir()

# ─────────────────────────────────────────
# MERGE ALL DATA
# ─────────────────────────────────────────
df = df_fx.join(wb_final, on="Year")
df = df.drop(columns=["Year"])

df = df.reset_index().rename(columns={"index": "Date"})
df["Date"] = pd.to_datetime(df["Date"])
df = df.set_index("Date")

for monthly_df in [oil, us_rate, ph_rate, gir_monthly]:
    if not monthly_df.empty:
        monthly_daily = monthly_df.resample("D").ffill()
        df = df.join(monthly_daily, how="left")

df = df.reset_index().rename(columns={"index": "Date"})
df["Date"] = df["Date"].astype(str)

df = df.ffill().bfill()

df_wide = df.sort_values("Date", ascending=True)

# ─────────────────────────────────────────
# EXPORT CSV
# ─────────────────────────────────────────
df_wide.to_csv("FX_WIDE.csv", index=False)
print("CSV saved: FX_WIDE.csv")

# ─────────────────────────────────────────
# GOOGLE SHEETS UPLOAD
# ─────────────────────────────────────────
print("Uploading to Google Sheets...")

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_env = os.environ.get("GOOGLE_CREDENTIALS")

if creds_env:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(creds_env), scope
    )
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )

client = gspread.authorize(creds)
spreadsheet = client.open("PH Forex Dashboard")

def update_sheet(title, dataframe):
    try:
        sheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title=title, rows="100000", cols="30"
        )

    existing_data = sheet.get_all_values()

    if len(existing_data) <= 1:
        sheet.clear()
        sheet.append_row(dataframe.columns.tolist())
        sheet.append_rows(dataframe.values.tolist())
        print(f"Initial load complete for {title}.")

    else:
        existing_dates = [row[0] for row in existing_data[1:] if row]

        if latest not in existing_dates:
            new_rows = dataframe[dataframe["Date"] == latest]

            if not new_rows.empty:
                sheet.append_rows(new_rows.values.tolist())
                print(f"Appended {latest} to {title}.")
            else:
                print(f"No row found for latest date: {latest}")
        else:
            print(f"{latest} already exists in {title}. Skipping.")

update_sheet("FX_WIDE", df_wide)

# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
print(f"\nTask completed in {time.perf_counter() - start_time:.2f} seconds")
print(df_wide.tail(5).to_string())
