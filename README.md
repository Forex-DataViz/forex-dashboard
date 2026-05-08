## Requirements

* **Python Script:** `Forex_API_V4.py`
* **Authentication:** A valid `credentials.json` file for Google Sheets API access.
* **Target Destination:** Editor access to the "PH Forex Dashboard" Google Sheet.
* **Additional Dependencies:** `yfinance` (for commodity data via Yahoo Finance)

---

## Installation

Follow these steps to deploy the automated pipeline using GitHub Actions.

### 1. Prepare the Repository
1. Log into GitHub and create a new **Public** repository named `forex-dashboard`. Do not initialize it with a README.
2. In your new repository, click **Add file** > **Upload files**.
3. Upload `Forex_API_V4.py` to the root directory and commit the changes.

### 2. Configure Google Credentials
1. Navigate to the **Settings** tab of your repository.
2. On the left sidebar, select **Secrets and variables** > **Actions**.
3. Click the green **New repository secret** button.
4. Set the Name to exactly `GOOGLE_CREDENTIALS`.
5. Paste the entire contents of your `credentials.json` file into the Secret field and click **Add Secret**.

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
        run: pip install requests pandas gspread oauth2client yfinance

      - name: Run script
        env:
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
        run: python Forex_API_V4.py
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
   - `"Initial load complete for FX_WIDE."` / `"Initial load complete for FX_LONG."` (first-ever run)
   - `"Appended YYYY-MM-DD to FX_WIDE."` and `"Appended YYYY-MM-DD to FX_LONG."` (subsequent runs)
   - Or `"YYYY-MM-DD already exists in FX_WIDE/FX_LONG. Skipping."` (if run more than once on the same day)
   - Note: If the run indicator is red, open the job logs to review the error.

**2. Check Google Sheets:** Open the **PH Forex Dashboard**.
   - In the **FX_WIDE** sheet, confirm one new row is added for the latest date, containing daily forex rates (USD→PHP, JPY→PHP), World Bank annual metrics (GDP growth, FDI for US/JP/PH), and commodity prices (Crude Oil, Natural Gas, Gold, Silver).
   - In the **FX_LONG** sheet, confirm multiple rows are added for the same date (one row per variable/metric).

---

## Data Sources

The pipeline aggregates data from three sources:

| Source | Data | Granularity |
|---|---|---|
| [Frankfurter API](https://www.frankfurter.app/) | USD→PHP and JPY→PHP exchange rates | Daily (from 2000-01-01) |
| [World Bank API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) | GDP growth & FDI inflows for US, Japan, Philippines | Annual |
| [Yahoo Finance (yfinance)](https://pypi.org/project/yfinance/) | Crude Oil (BZ=F), Natural Gas (NG=F), Gold (GC=F), Silver (SI=F) | Annual average |

Annual metrics (World Bank + commodities) are forward-filled onto daily forex rows by year. Forward-fill and back-fill are applied to handle weekends and data lags.
