from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
import io
import json
import unittest
from unittest.mock import Mock, patch

import gspread
import numpy as np
import pandas as pd
import requests

from sheets_upload import dataframe_to_rows, to_sheet_cell, update_sheet
from forex_dates import get_latest_date


HEADERS = [
    "Date", "USD_to_PHP", "US_GDP", "PH_GDP", "US_FDI", "PH_FDI",
    "US_Inflation", "PH_Inflation", "Brent_Crude_Oil_Price", "US_Policy_Rate",
    "PH_Policy_Rate", "BSP_Gross_International_Reserves",
]
LATEST = "2026-11-06"


def assert_request_safe(values):
    """Exercise the same Requests encoder as gspread without sending a request."""
    body = {"values": values}
    encoded = json.dumps(body, allow_nan=False)
    request = requests.Request("POST", "https://example.invalid", json=body).prepare()
    assert json.loads(request.body) == json.loads(encoded)
    assert all(type(cell) in (str, bool, int, float) for row in values for cell in row)


class RecordingWorksheet:
    def __init__(self, existing):
        self.values = [list(row) for row in existing]
        self.calls = []

    def get_all_values(self):
        return self.values

    def clear(self):
        self.calls.append(("clear",))
        self.values = []

    def append_row(self, row):
        assert_request_safe([row])
        self.calls.append(("append_row", row))
        self.values.append([str(cell) for cell in row])

    def append_rows(self, rows):
        assert_request_safe(rows)
        self.calls.append(("append_rows", rows))
        self.values.extend([[str(cell) for cell in row] for row in rows])


class CellConversionTests(unittest.TestCase):
    def test_missing_and_nonfinite_cells_become_empty_strings(self):
        values = [
            None, pd.NA, pd.NaT, float("nan"), float("inf"), -float("inf"),
            np.float16("nan"), np.float32("inf"), np.float64("-inf"),
            np.longdouble("nan"), np.datetime64("NaT", "ns"), np.timedelta64("NaT", "ns"),
        ]
        for value in values:
            with self.subTest(value=repr(value)):
                self.assertEqual(to_sheet_cell(value), "")

    def test_finite_values_keep_native_types_and_values(self):
        cases = [
            (np.int64(307018000000), 307018000000, int),
            (np.uint64(2**63), 2**63, int),
            (np.int32(-12), -12, int), (0, 0, int),
            (np.float32(4.5), 4.5, float), (np.float64(-2.75), -2.75, float),
            (np.longdouble(1.25), 1.25, float), (0.0, 0.0, float),
            (np.bool_(False), False, bool), (np.bool_(True), True, bool),
            (False, False, bool), (np.str_("PHP"), "PHP", str),
            ("", "", str), ("NaN", "NaN", str), ("inf", "inf", str),
            (LATEST, LATEST, str),
        ]
        for value, expected, native_type in cases:
            with self.subTest(value=repr(value)):
                result = to_sheet_cell(value)
                self.assertIs(type(result), native_type)
                self.assertEqual(result, expected)
                assert_request_safe([[result]])

    def test_dates_and_durations_become_iso_strings(self):
        cases = [
            (date(2026, 11, 6), LATEST),
            (datetime(2026, 11, 6, 12, tzinfo=timezone.utc), "2026-11-06T12:00:00+00:00"),
            (pd.Timestamp("2026-11-06T12:34:56.123456789"), "2026-11-06T12:34:56.123456789"),
            (np.datetime64("2026-11-06T12:34:56", "ns"), "2026-11-06T12:34:56"),
            (pd.Timedelta(hours=2), "P0DT2H0M0S"),
            (np.timedelta64(2, "h"), "P0DT2H0M0S"),
            (timedelta(hours=2), "P0DT2H0M0S"),
        ]
        for value, expected in cases:
            with self.subTest(value=repr(value)):
                self.assertEqual(to_sheet_cell(value), expected)

    def test_containers_and_unsupported_scalars_are_rejected(self):
        for value in ([1, 2], {"x": 1}, np.array([1]), 1 + 2j, b"bytes"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(TypeError):
                    to_sheet_cell(value)

    def test_float_conversion_cannot_introduce_infinity(self):
        if np.finfo(np.longdouble).max <= np.finfo(float).max:
            self.skipTest("longdouble has no wider range on this platform")
        with self.assertRaisesRegex(ValueError, "double range"):
            to_sheet_cell(np.finfo(np.longdouble).max)


class DataframeConversionTests(unittest.TestCase):
    def test_reproduces_requests_error_then_converts_all_three_nonfinite_values(self):
        frame = pd.DataFrame({"Date": [LATEST], "NaN": [np.nan], "Pos": [np.inf], "Neg": [-np.inf]})
        with self.assertRaises(requests.exceptions.InvalidJSONError):
            requests.Request("POST", "https://example.invalid", json={"values": frame.values.tolist()}).prepare()
        # CSV output succeeds with the same values that break the JSON upload.
        self.assertIn(LATEST, frame.to_csv(index=False))
        with self.assertLogs("sheets_upload", level="WARNING") as logs:
            rows = dataframe_to_rows(frame)
        self.assertEqual(rows, [[LATEST, "", "", ""]])
        assert_request_safe(rows)
        self.assertIn("column 'NaN' (nan)", " ".join(logs.output))
        self.assertIn("column 'Pos' (inf)", " ".join(logs.output))
        self.assertIn("column 'Neg' (-inf)", " ".join(logs.output))
        self.assertIn("first payload row=1", " ".join(logs.output))

    def test_nullable_columns_preserve_order_shape_and_source_dtypes(self):
        frame = pd.DataFrame({
            "Date": pd.Series([LATEST, pd.NA], dtype="string"),
            "Count": pd.Series([np.int64(7), pd.NA], dtype="Int64"),
            "Rate": pd.Series([4.5, pd.NA], dtype="Float64"),
            "Flag": pd.Series([False, pd.NA], dtype="boolean"),
            "When": pd.to_datetime([LATEST, None]),
            "AllMissing": [np.nan, np.nan],
        })
        frame.index = [17, 3]
        original = frame.copy(deep=True)
        with self.assertLogs("sheets_upload", level="WARNING"):
            rows = dataframe_to_rows(frame)
        self.assertEqual(rows, [
            [LATEST, 7, 4.5, False, "2026-11-06T00:00:00", ""],
            ["", "", "", "", "", ""],
        ])
        assert_request_safe(rows)
        pd.testing.assert_frame_equal(frame, original)

    def test_diagnostics_aggregate_counts_and_do_not_warn_for_literal_blanks(self):
        frame = pd.DataFrame({"Date": [LATEST] * 3, "Rate": [np.inf, np.inf, np.inf], "Text": [""] * 3})
        with self.assertLogs("sheets_upload", level="WARNING") as logs:
            dataframe_to_rows(frame)
        self.assertEqual(len(logs.output), 1)
        self.assertIn("replaced 3 cell(s) in column 'Rate'", logs.output[0])

    def test_invalid_cell_error_identifies_column_and_row(self):
        with self.assertRaisesRegex(ValueError, "payload row 2, column 'Rate'"):
            dataframe_to_rows(pd.DataFrame({"Rate": [4.5, {"unexpected": 1}]}))

    def test_empty_dataframe_has_no_payload_rows(self):
        self.assertEqual(dataframe_to_rows(pd.DataFrame(columns=HEADERS)), [])

    def test_itertuples_preserves_integers_in_mixed_numeric_frames(self):
        value = 2**53 + 1
        frame = pd.DataFrame({"Integer": [value], "Float": [1.25]})
        self.assertEqual(dataframe_to_rows(frame), [[value, 1.25]])


class UpdateSheetTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            ["2026-11-04", 63.5, 2.1, 4.4, 307018000000, 8122212784, 2.9, 1.6, 114.16, 3.75, 4.5, 104.8],
            ["2026-11-05", 63.6, 2.1, 4.4, 307018000000, 8122212784, 2.9, 1.6, 114.16, 3.75, 4.5, 104.8],
            [LATEST, 63.7, np.nan, 4.4, 307018000000, 8122212784, 2.9, 1.6, np.inf, 3.75, 4.5, -np.inf],
        ], columns=HEADERS)
        self.original = self.frame.copy(deep=True)
        self.book = Mock()
        self.output = io.StringIO()

    def run_update(self, existing, frame=None, missing_sheet=False):
        sheet = RecordingWorksheet(existing)
        if missing_sheet:
            self.book.worksheet.side_effect = gspread.WorksheetNotFound("FX_WIDE")
            self.book.add_worksheet.return_value = sheet
        else:
            self.book.worksheet.return_value = sheet
        with redirect_stdout(self.output), self.assertLogs("sheets_upload", level="WARNING"):
            update_sheet("FX_WIDE", self.frame if frame is None else frame, spreadsheet=self.book, latest=LATEST)
        pd.testing.assert_frame_equal(self.frame, self.original)
        return sheet

    def test_full_load_preserves_all_twelve_columns_and_row_order(self):
        sheet = self.run_update([])
        self.assertEqual([call[0] for call in sheet.calls], ["clear", "append_row", "append_rows"])
        self.assertEqual(sheet.calls[1][1], HEADERS)
        rows = sheet.calls[2][1]
        self.assertEqual([row[0] for row in rows], ["2026-11-04", "2026-11-05", LATEST])
        self.assertTrue(all(len(row) == 12 for row in rows))
        self.assertEqual(rows[-1], [LATEST, 63.7, "", 4.4, 307018000000, 8122212784, 2.9, 1.6, "", 3.75, 4.5, ""])

    def test_incremental_load_selects_only_latest_not_all_unseen_dates(self):
        sheet = self.run_update([HEADERS, ["2026-11-04"]])
        self.assertEqual([call[0] for call in sheet.calls], ["append_rows"])
        self.assertEqual(len(sheet.calls[0][1]), 1)
        self.assertEqual(sheet.calls[0][1][0][0], LATEST)
        self.assertEqual(sheet.calls[0][1][0][2], "")
        self.assertEqual(sheet.calls[0][1][0][8], "")
        self.assertEqual(sheet.calls[0][1][0][11], "")
        # A repeat run sees the appended date and performs no further writes.
        with redirect_stdout(self.output):
            update_sheet("FX_WIDE", self.frame, spreadsheet=self.book, latest=LATEST)
        self.assertEqual(len(sheet.calls), 1)

    def test_existing_latest_date_skips_without_normalizing_unused_rows(self):
        sheet = RecordingWorksheet([HEADERS, [LATEST]])
        self.book.worksheet.return_value = sheet
        self.frame["US_GDP"] = self.frame["US_GDP"].astype(object)
        self.frame.at[0, "US_GDP"] = {"unused": "invalid"}
        with redirect_stdout(self.output):
            update_sheet("FX_WIDE", self.frame, spreadsheet=self.book, latest=LATEST)
        self.assertEqual(sheet.calls, [])

    @patch("forex_dates.requests.get")
    def test_saturday_published_date_appends_friday_once(self, get):
        get.return_value.json.return_value = {
            "date": LATEST, "rates": {"PHP": 63.017},
        }
        latest = get_latest_date(date(2026, 11, 7))
        sheet = RecordingWorksheet([HEADERS, ["2026-11-05"]])
        self.book.worksheet.return_value = sheet
        with redirect_stdout(self.output), self.assertLogs("sheets_upload", level="WARNING"):
            update_sheet("FX_WIDE", self.frame, spreadsheet=self.book, latest=latest)
        self.assertEqual(len(sheet.calls), 1)
        self.assertEqual(sheet.calls[0][0], "append_rows")
        self.assertEqual(len(sheet.calls[0][1]), 1)
        self.assertEqual(sheet.calls[0][1][0][0], "2026-11-06")
        self.assertEqual(sheet.calls[0][1][0][-1], "")
        with redirect_stdout(self.output):
            update_sheet("FX_WIDE", self.frame, spreadsheet=self.book, latest=latest)
        self.assertEqual(len(sheet.calls), 1)
        pd.testing.assert_frame_equal(self.frame, self.original)

    def test_no_matching_latest_row_does_not_write(self):
        sheet = RecordingWorksheet([HEADERS, ["2026-11-04"], [], [""]])
        self.book.worksheet.return_value = sheet
        with redirect_stdout(self.output):
            update_sheet("FX_WIDE", self.frame.iloc[:2], spreadsheet=self.book, latest=LATEST)
        self.assertEqual(sheet.calls, [])
        self.assertIn("No row found for latest date", self.output.getvalue())

    def test_schema_change_reloads_even_if_latest_already_exists(self):
        for headers in (HEADERS[:-1], [HEADERS[0]] + list(reversed(HEADERS[1:]))):
            with self.subTest(headers=headers):
                sheet = self.run_update([headers, [LATEST]])
                self.assertEqual(sheet.calls[0], ("clear",))
                self.assertEqual(sheet.calls[1], ("append_row", HEADERS))
                self.assertEqual(len(sheet.calls[2][1]), 3)

    def test_header_only_sheet_gets_full_load(self):
        sheet = self.run_update([HEADERS])
        self.assertEqual(len(sheet.calls[2][1]), 3)

    def test_missing_worksheet_is_created_and_fully_loaded(self):
        sheet = self.run_update([], missing_sheet=True)
        self.book.add_worksheet.assert_called_once_with(title="FX_WIDE", rows="100000", cols="30")
        self.assertEqual(len(sheet.calls[2][1]), 3)

    def test_invalid_payload_is_rejected_before_clear_or_header_write(self):
        sheet = RecordingWorksheet([["Old schema"], [LATEST]])
        self.book.worksheet.return_value = sheet
        frame = pd.DataFrame({"Date": [LATEST], "Bad": [{"nested": "object"}]})
        with redirect_stdout(self.output), self.assertRaisesRegex(ValueError, "column 'Bad'"):
            update_sheet("FX_WIDE", frame, spreadsheet=self.book, latest=LATEST)
        self.assertEqual(sheet.calls, [])

    def test_empty_full_load_writes_only_headers(self):
        sheet = RecordingWorksheet([])
        self.book.worksheet.return_value = sheet
        with redirect_stdout(self.output):
            update_sheet("FX_WIDE", self.frame.iloc[:0], spreadsheet=self.book, latest=LATEST)
        self.assertEqual(sheet.calls, [("clear",), ("append_row", HEADERS)])


if __name__ == "__main__":
    unittest.main()
