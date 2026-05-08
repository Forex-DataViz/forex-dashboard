# PHP/USD & PHP/JPY Analysis (Forex_API_V2)

This project aims to analyze the Philippine Peso (PHP) against two major currencies, USD and JPY, throughout 
the year 2000 up to present day to identify economic events that drove the depreciation of the PHP.

---

## Prerequisites

Before you begin, ensure you have met the following requirements:
* **Python Script:** `Forex_API_V2.py`
* **Authentication:** A valid `credentials.json` file for Google Sheets API access.
* **Target Destination:** Editor access to the "PH Forex Dashboard" Google Sheet.

---

## Installation

Follow these steps to deploy the automated pipeline using GitHub Actions.

### 1. Prepare the Repository
1. Log into GitHub and create a new **Public** repository named `forex-dashboard`.
2. In your new repository, click **Add file** > **Upload files**.
3. Upload `Forex_API_V2.py` to the root directory and commit the changes.

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
    - cron: '0 1 * * 1-5'
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
        run: pip install requests pandas gspread oauth2client

      - name: Run script
        env:
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
        run: python Forex_API_V2.py
```

4. Click Commit changes and save with a message like "Add GitHub Actions workflow".

---

## Usage

Once set up, the pipeline is designed to run automatically but can be manually triggered and monitored.

### Automated Schedule

The workflow automatically runs every weekday (Monday to Friday) at 9:00 AM Manila time (1:00 AM UTC).

### Manual Execution

To force the script to run immediately:
1. Go to the Actions tab in your repository.
2. Select Daily Forex Pipeline from the left sidebar.
3. Click the Run workflow dropdown on the right side and execute it.

### Verifying the Output
1. Check GitHub Logs: Click into the most recent workflow run in the Actions tab. Open the logs and confirm
success by looking for:
* "Appended WIDE row for YYYY-MM-DD" and "Appended X LONG rows for YYYY-MM-DD"
* Or, "YYYY-MM-DD already exists... Skipping append"
* Note: If the run indicator is red, open the job logs to review the error.

2. Check Google Sheets: Open the PH Forex Dashboard.
* In the FX_WIDE sheet, confirm one new row is added for the latest date.
* In the FX_LONG sheet, confirm multiple rows are added for the same date.
