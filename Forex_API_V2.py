import os
import json
import time
import requests
import pandas as pd
from datetime import date, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

start_time = time.perf_counter()


def get_latest_date():
    # Tries today, falls back to previous days until data is found
    for i in range(5):
        check_date = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        url = f"https://api.frankfurter.dev/v2/rates?date={check_date}&quotes=PHP"
        response = requests.get(url).json()
        if isinstance(response, list) and len(response) > 0:
            return response[0]["date"]
    return None

# ─────────────────────────────────────────
# FOREX - Daily (Frankfurter API)
# ─────────────────────────────────────────
latest = get_latest_date()

if latest is None:
    raise Exception("No latest forex data available from Frankfurter API.")

url_usd = f"https://api.frankfurter.dev/v2/rates?from=2000-01-01&to={latest}&quotes=PHP&base=USD"
url_jpy = f"https://api.frankfurter.dev/v2/rates?from=2000-01-01&to={latest}&quotes=PHP&base=JPY"

data_usd = requests.get(url_usd).json()
data_jpy = requests.get(url_jpy).json()

df_usd = pd.DataFrame([{"Date": r["date"], "USD_to_PHP": r["rate"]} for r in data_usd])
df_usd = df_usd.set_index("Date")
df_usd.index = pd.to_datetime(df_usd.index)

df_jpy = pd.DataFrame([{"Date": r["date"], "JPY_to_PHP": r["rate"]} for r in data_jpy])
df_jpy = df_jpy.set_index("Date")
df_jpy.index = pd.to_datetime(df_jpy.index)

df_fx = pd.concat([df_usd, df_jpy], axis=1)
df_fx.index = pd.to_datetime(df_fx.index)

# Add Year column for joining World Bank annual data
df_fx["Year"] = df_fx.index.year


# ─────────────────────────────────────────
# INFLATION + GDP (World Bank API)
# ─────────────────────────────────────────
def world_bank(country, indicator, col_name):
    url = f"http://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=20000"
    response = requests.get(url).json()

    if len(response) < 2 or response[1] is None:
        raise Exception(f"No World Bank data found for {country} - {indicator}")

    data = response[1]

    df = pd.DataFrame([
        {"Year": int(d["date"]), col_name: d["value"]}
        for d in data if d["value"] is not None
    ])

    return df.set_index("Year").sort_index()


CPI = "FP.CPI.TOTL.ZG"
GDP = "NY.GDP.MKTP.KD.ZG"

infl_us = world_bank("US", CPI, "US_Inflation")
infl_jp = world_bank("JP", CPI, "JP_Inflation")
infl_ph = world_bank("PH", CPI, "PH_Inflation")

gdp_us = world_bank("US", GDP, "US_GDP")
gdp_jp = world_bank("JP", GDP, "JP_GDP")
gdp_ph = world_bank("PH", GDP, "PH_GDP")

wb = infl_us.join([infl_jp, infl_ph, gdp_us, gdp_jp, gdp_ph])


# ─────────────────────────────────────────
# MERGE - Daily Forex + Annual World Bank
# ─────────────────────────────────────────
df = df_fx.join(wb, on="Year")
df = df.drop(columns=["Year"])
df = df.reset_index().rename(columns={"index": "Date"})
df["Date"] = df["Date"].astype(str)

# Fill NA values
df = df.ffill()
df = df.bfill()

# Sort in chronological order: oldest to newest
df_wide = df.sort_values("Date", ascending=True)

# Create long format version for Tableau
df_long = df_wide.melt(
    id_vars=["Date"],
    var_name="Variable",
    value_name="Value"
)


# ─────────────────────────────────────────
# GOOGLE SHEETS - Wide + Long
# ─────────────────────────────────────────
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Supports both local credentials.json and GitHub Actions env secret
creds_env = os.environ.get("GOOGLE_CREDENTIALS")

if creds_env:
    creds_dict = json.loads(creds_env)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

client = gspread.authorize(creds)
spreadsheet = client.open("PH Forex Dashboard")


def get_or_create_worksheet(spreadsheet, title, rows, cols):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


sheet_wide = get_or_create_worksheet(
    spreadsheet,
    title="FX_WIDE",
    rows="10000",
    cols="20"
)

sheet_long = get_or_create_worksheet(
    spreadsheet,
    title="FX_LONG",
    rows="100000",
    cols="5"
)


def load_or_append_wide(sheet, df_wide, latest):
    existing = sheet.get_all_values()

    if len(existing) <= 1:
        sheet.clear()
        sheet.append_row(df_wide.columns.tolist())
        sheet.append_rows(df_wide.values.tolist())
        print("Initial load complete for FX_WIDE.")
    else:
        existing_dates = [row[0] for row in existing[1:] if len(row) > 0]

        latest_row = df_wide[df_wide["Date"] == latest]

        if latest_row.empty:
            print(f"No WIDE data available for {latest}.")
        elif latest in existing_dates:
            print(f"{latest} already exists in FX_WIDE. Skipping append.")
        else:
            sheet.append_row(latest_row.values.tolist()[0])
            print(f"Appended WIDE row for {latest}.")


def load_or_append_long(sheet, df_long, latest):
    existing = sheet.get_all_values()

    if len(existing) <= 1:
        sheet.clear()
        sheet.append_row(df_long.columns.tolist())
        sheet.append_rows(df_long.values.tolist())
        print("Initial load complete for FX_LONG.")
    else:
        existing_dates = [row[0] for row in existing[1:] if len(row) > 0]

        latest_rows = df_long[df_long["Date"] == latest]

        if latest_rows.empty:
            print(f"No LONG data available for {latest}.")
        elif latest in existing_dates:
            print(f"{latest} already exists in FX_LONG. Skipping append.")
        else:
            sheet.append_rows(latest_rows.values.tolist())
            print(f"Appended {len(latest_rows)} LONG rows for {latest}.")


load_or_append_wide(sheet_wide, df_wide, latest)
load_or_append_long(sheet_long, df_long, latest)


# ─────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────
end_time = time.perf_counter()

print("\nLatest WIDE rows:")
print(df_wide.tail().to_string(index=False))

print("\nLatest LONG rows:")
print(df_long.tail(20).to_string(index=False))

print(f"\nLatest available data date: {latest}")
print(f"Runtime: {end_time - start_time:.2f} seconds")
