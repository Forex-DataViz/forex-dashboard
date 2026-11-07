"""JSON-safe Google Sheets uploads, independently testable without credentials."""

from collections import Counter
from datetime import date, datetime, timedelta
import json
import logging
import math

import gspread
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


def to_sheet_cell(value):
    """Return a native Sheets scalar; missing/nonfinite values become blank cells.

    Empty strings explicitly write blanks. None would be skipped by Sheets.
    Do not stringify numbers or change the source DataFrame's dtypes.
    """
    if not pd.api.types.is_scalar(value):
        raise TypeError(f"Unsupported Sheets cell type: {type(value).__name__}")
    if pd.isna(value):
        return ""
    if isinstance(value, (str, np.str_)):
        return str(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    # Handle temporal scalars before numeric ones (np.timedelta64 is an integer).
    if isinstance(value, np.datetime64):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (timedelta, np.timedelta64)):
        return pd.Timedelta(value).isoformat()
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            return ""
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Finite number exceeds the Sheets double range")
        return result
    raise TypeError(f"Unsupported Sheets cell type: {type(value).__name__}")


def dataframe_to_rows(dataframe):
    """Serialize in existing row/column order and report replaced cells by column."""
    rows = []
    replacements = Counter()
    examples = {}
    for row_number, values in enumerate(dataframe.itertuples(index=False, name=None), 1):
        row = []
        for column_number, value in enumerate(values):
            column = dataframe.columns[column_number]
            try:
                cell = to_sheet_cell(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(
                    f"Invalid Sheets cell at payload row {row_number}, "
                    f"column {column!r}: {exc}"
                ) from exc
            if cell == "" and not isinstance(value, (str, np.str_)):
                # Only missing/nonfinite scalars reach this branch; no data dumps.
                key = (column_number, repr(value))
                replacements[key] += 1
                examples.setdefault(key, row_number)
            row.append(cell)
        rows.append(row)

    # Match Requests' strict encoding before any worksheet is cleared or written.
    json.dumps({"values": rows}, allow_nan=False)
    for (column_number, value), count in replacements.items():
        logger.warning(
            "Sheets payload: replaced %s cell(s) in column %r (%s) with blanks; "
            "first payload row=%s",
            count, dataframe.columns[column_number], value,
            examples[(column_number, value)],
        )
    return rows


def update_sheet(title, dataframe, *, spreadsheet, latest):
    """Keep full-load/schema and latest-date selection rules at the upload boundary."""
    try:
        sheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title=title, rows="100000", cols="30"
        )

    existing_data = sheet.get_all_values()
    existing_headers = existing_data[0] if existing_data else []
    existing_dates = [row[0] for row in existing_data[1:] if row and row[0]]

    current_headers = dataframe.columns.tolist()
    schema_changed = existing_headers != current_headers

    print(f"[DEBUG] Sheet: {title}")
    print(f"[DEBUG] Schema changed: {schema_changed}")
    print(f"[DEBUG] Existing headers: {existing_headers}")
    print(f"[DEBUG] Current headers: {current_headers}")

    if not existing_dates or schema_changed:
        rows = dataframe_to_rows(dataframe)
        headers = [to_sheet_cell(value) for value in current_headers]
        json.dumps({"values": [headers]}, allow_nan=False)
        sheet.clear()
        sheet.append_row(headers)
        if rows:
            sheet.append_rows(rows)
        print(f"[DEBUG] Full load done for {title}.")

    elif latest not in existing_dates:
        new_rows = dataframe[dataframe["Date"] == latest]
        print(f"[DEBUG] Rows matched for latest date: {len(new_rows)}")
        if not new_rows.empty:
            sheet.append_rows(dataframe_to_rows(new_rows))
            print(f"Appended {latest} to {title}.")
        else:
            print(f"[DEBUG] No row found for latest date: {latest}")
    else:
        print(f"[DEBUG] {latest} already exists in {title}. Skipping.")
