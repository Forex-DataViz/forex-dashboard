import os
import json
import time
import requests
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

start_time = time.perf_counter()

# GET LATEST FOREX DATE 
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
# FOREX - Daily (Frankfurter API)
# ─────────────────────────────────────────
print("Fetching Daily Forex...")
url_usd = f"https://api.frankfurter.app/2000-01-01..{latest}?from=USD&to=PHP"
url_jpy = f"https://api.frankfurter.app/2000-01-01..{latest}?from=JPY&to=PHP"

df_usd = pd.DataFrame.from_dict(requests.get(url_usd).json()["rates"], orient="index").rename(columns={"PHP": "USD_to_PHP"})
df_jpy = pd.DataFrame.from_dict(requests.get(url_jpy).json()["rates"], orient="index").rename(columns={"PHP": "JPY_to_PHP"})

df_fx = pd.concat([df_usd, df_jpy], axis=1)
df_fx.index = pd.to_datetime(df_fx.index)
df_fx["Year"] = df_fx.index.year

# ─────────────────────────────────────────
# WORLD BANK DATA (GDP & FDI)
# ─────────────────────────────────────────
def world_bank(country, indicator, col_name):
    print(f"Fetching World Bank: {col_name}...")
    url = f"http://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=20000"
    try:
        data = requests.get(url).json()[1]
        return pd.DataFrame([{"Year": int(d["date"]), col_name: d["value"]} for d in data if d["value"] is not None]).set_index("Year")
    except: return pd.DataFrame()

GDP_IND = "NY.GDP.MKTP.KD.ZG"
FDI_IND = "BX.KLT.DINV.CD.WD"

wb_data = [
    world_bank("US", GDP_IND, "US_GDP"),
    world_bank("JP", GDP_IND, "JP_GDP"),
    world_bank("PH", GDP_IND, "PH_GDP"),
    world_bank("US", FDI_IND, "US_FDI"),
    world_bank("JP", FDI_IND, "JP_FDI"),
    world_bank("PH", FDI_IND, "PH_FDI")
]
wb_final = wb_data[0].join(wb_data[1:])

# YAHOO FINANCE DATA (Global Market Commodities) 
def get_commodity_annual(ticker, col_name):
    print(f"Fetching Commodity: {col_name}...")
    data = yf.download(ticker, start="2000-01-01", progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        series = data['Close'][ticker]
    else:
        series = data['Close']
    # Average by year to match World Bank structure
    df_y = series.resample('YE').mean().to_frame()
    df_y.index = df_y.index.year
    return df_y.rename(columns={df_y.columns[0]: col_name})

comm_final = get_commodity_annual("BZ=F", "Crude_Oil_Price").join([
    get_commodity_annual("NG=F", "Natural_Gas_Price"),
    get_commodity_annual("GC=F", "Gold_Price"),
    get_commodity_annual("SI=F", "Silver_Price")
])

# ─────────────────────────────────────────
#  MERGE ALL DATA 
# ─────────────────────────────────────────

# Join Annual WB and Annual Commodities first
annual_metrics = wb_final.join(comm_final, how="outer")

# Map the annual metrics onto the Daily Forex rows using the 'Year' column
df = df_fx.join(annual_metrics, on="Year")
df = df.drop(columns=["Year"]).reset_index().rename(columns={"index": "Date"})
df["Date"] = df["Date"].astype(str)

# Fill gaps (Forex doesn't run on weekends, and WB data lags)
df = df.ffill().bfill()

# Prepare Long Format for Tableau
df_wide = df.sort_values("Date", ascending=True)
df_long = df_wide.melt(id_vars=["Date"], var_name="Variable", value_name="Value")

# ─────────────────────────────────────────
# GOOGLE SHEETS UPLOAD
# ─────────────────────────────────────────
print("Uploading to Google Sheets...")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_env = os.environ.get("GOOGLE_CREDENTIALS")
if creds_env:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_env), scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

client = gspread.authorize(creds)
spreadsheet = client.open("PH Forex Dashboard")

def update_sheet(title, dataframe, is_long=False):
    try:
        sheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=title, rows="100000", cols="20")
    
    existing_data = sheet.get_all_values()
    if len(existing_data) <= 1:
        sheet.clear()
        sheet.append_row(dataframe.columns.tolist())
        sheet.append_rows(dataframe.values.tolist())
        print(f"Initial load complete for {title}.")
    else:
        # Check if the latest date is already there
        existing_dates = [row[0] for row in existing_data[1:] if row]
        if latest not in existing_dates:
            new_rows = dataframe[dataframe["Date"] == latest]
            if not new_rows.empty:
                sheet.append_rows(new_rows.values.tolist())
                print(f"Appended {latest} to {title}.")
        else:
            print(f"{latest} already exists in {title}. Skipping.")

update_sheet("FX_WIDE", df_wide)
update_sheet("FX_LONG", df_long, is_long=True)

# ─────────────────────────────────────────
#  LOGGING 
# ─────────────────────────────────────────
print(f"\nTask completed in {time.perf_counter() - start_time:.2f} seconds")
print(df_wide.tail(5))