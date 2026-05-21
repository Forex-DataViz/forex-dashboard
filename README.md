## Dashboard Link
Working web dashboard [Click Here](https://forex-dashboard-carolino-favorada-lavado-punzalan-yutuc.streamlit.app)

---

## Requirements

* **Python Script:** `Forex_API_V5.py`
* **Authentication:** A valid `credentials.json` file for Google Sheets API access.
* **Target Destination:** Editor access to the "PH Forex Dashboard" Google Sheet.
* **API Keys:** `EIA_API_KEY` (EIA oil prices) and `FRED_API_KEY` (US Federal Funds Rate)
* **Additional File:** `MonetaryPolicyDecisions.xlsx` (BSP policy rate decisions, uploaded to repo root)

---

## Installation

Follow these steps to deploy the automated pipeline using GitHub Actions.

### 1. Prepare the Repository
1. Log into GitHub and create a new **Public** repository named `forex-dashboard`. Do not initialize it with a README.
2. In your new repository, click **Add file** > **Upload files**.
3. Upload `Forex_API_V5.py` and `MonetaryPolicyDecisions.xlsx` to the root directory and commit the changes.

### 2. Configure Secrets
1. Navigate to the **Settings** tab of your repository.
2. On the left sidebar, select **Secrets and variables** > **Actions**.
3. Click the green **New repository secret** button and add the following three secrets:

| Name | Value |
|---|---|
| `GOOGLE_CREDENTIALS` | Entire contents of your `credentials.json` file |
| `EIA_API_KEY` | Your EIA API key |
| `FRED_API_KEY` | Your FRED API key |

### 3. Set Up the Automation Pipeline
1. Go back to the main page of your repository and click **Add file** > **Create new file**.
2. Name the file path exactly: `.github/workflows/forex_pipeline.yml`
3. Paste the following GitHub Actions configuration into the editor:

```yaml
name: Daily Forex Pipeline

on:
  schedule:
    - cron: '0 10 * * 1-5'  # 6:00 PM Manila time (UTC+8)
  workflow_dispatch:

permissions:
  contents: write

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests pandas gspread oauth2client lxml openpyxl

      - name: Run script
        env:
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
        run: python Forex_API_V5.py

      - name: Commit CSV
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add FX_WIDE.csv
          git commit -m "Update FX_WIDE.csv [$(date +%Y-%m-%d)]" || echo "No changes"
          git push
```

4. Click **Commit changes** and save with a message like `"Add GitHub Actions workflow"`.

---

## Usage

Once set up, the pipeline is designed to run automatically but can be manually triggered and monitored.

### Automated Schedule

The workflow automatically runs every weekday (Monday to Friday) at **6:00 PM Manila time** (10:00 AM UTC).

### Manual Execution

To force the script to run immediately:

1. Go to the **Actions** tab in your repository.
2. Select **Daily Forex Pipeline** from the left sidebar.
3. Click the **Run workflow** dropdown on the right side and execute it.

### Verifying the Output

**1. Check GitHub Logs:** Click into the most recent workflow run in the Actions tab. Open the logs and confirm success by looking for:
   - `"[DEBUG] Full load done for FX_WIDE."` (first-ever run, or after a schema change)
   - `"Appended YYYY-MM-DD to FX_WIDE."` (subsequent runs)
   - Or `"[DEBUG] YYYY-MM-DD already exists in FX_WIDE. Skipping."` (if run more than once on the same day)
   - Note: If the run indicator is red, open the job logs to review the error. Debug lines prefixed with `[DEBUG]` are printed on every run and are normal.

**2. Check Google Sheets:** Open the **PH Forex Dashboard**.
   - In the **FX_WIDE** sheet, confirm one new row is added for the latest date, containing: daily USD→PHP forex rate, World Bank annual metrics (GDP growth & inflation for US/PH, FDI for US/PH), monthly EIA Brent crude oil price, monthly US Federal Funds Rate, daily BSP policy rate, and monthly BSP Gross International Reserves.

**3. Check the Repository:** After a successful run, a file named `FX_WIDE.csv` will be automatically committed to the root of your repository, providing a flat-file backup of the full dataset.

---

## Data Sources

The pipeline aggregates data from five sources:

| Source | Data | Granularity |
|---|---|---|
| [Frankfurter API](https://www.frankfurter.app/) | USD→PHP exchange rate | Daily (from 2000-01-01) |
| [World Bank API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) | GDP growth, FDI inflows, and CPI inflation for US & Philippines | Annual |
| [EIA API](https://www.eia.gov/opendata/) | Brent Crude Oil spot price (RBRTE) | Monthly |
| [FRED API](https://fred.stlouisfed.org/) | US Federal Funds Rate (FEDFUNDS) | Monthly |
| BSP (`MonetaryPolicyDecisions.xlsx`) | Philippines BSP overnight policy rate | Per decision (forward-filled daily) |
| [BSP Website](https://www.bsp.gov.ph/Statistics/sdds/table12_data.aspx) | Philippines Gross International Reserves (in million USD) | Monthly |

All monthly and annual series are forward-filled onto the daily forex spine. An additional forward-fill and back-fill pass is applied at the end to handle weekends and data publication lags.
