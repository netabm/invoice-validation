"""
Comprehensive test suite for process_records().

Organized into isolated groups (one concern each, fresh state per group)
plus one big combined "stress test" list at the end that mixes everything
together the way real OCR output would.

Run: python3 test_cases.py
"""

from solution import process_records


def run_group(title, records):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    cleaned, flagged = process_records(records)
    print(f"-> {len(cleaned)} cleaned, {len(flagged)} flagged\n")
    for r in cleaned:
        print(f"  CLEAN   {r}")
    for r in flagged:
        print(f"  FLAGGED {r}")


# ---------------------------------------------------------------------------
# 1. INVOICE ID FORMAT
# ---------------------------------------------------------------------------
GROUP_ID_FORMAT = [
    {"invoice_id": "INV-1001", "amount": "100", "date": "2024-01-01", "vendor": "Acme"},   # baseline valid
    {"invoice_id": "inv-1002", "amount": "100", "date": "2024-01-02", "vendor": "Acme"},   # lowercase prefix
    {"invoice_id": "INV1003", "amount": "100", "date": "2024-01-03", "vendor": "Acme"},    # missing dash
    {"invoice_id": "INV-100A", "amount": "100", "date": "2024-01-04", "vendor": "Acme"},   # letter in number
    {"invoice_id": "INVOICE-1005", "amount": "100", "date": "2024-01-05", "vendor": "Acme"},  # wrong prefix
    {"invoice_id": "", "amount": "100", "date": "2024-01-06", "vendor": "Acme"},           # empty
    {"invoice_id": None, "amount": "100", "date": "2024-01-07", "vendor": "Acme"},         # None
    {"invoice_id": 1008, "amount": "100", "date": "2024-01-08", "vendor": "Acme"},         # int, not string
    {"invoice_id": "INV--1009", "amount": "100", "date": "2024-01-09", "vendor": "Acme"},  # double dash
    {"invoice_id": "INV-01010", "amount": "100", "date": "2024-01-10", "vendor": "Acme"},  # leading zero (valid, tests int parsing)
    {"invoice_id": "INV-1011 ", "amount": "100", "date": "2024-01-11", "vendor": "Acme"},  # trailing space
]

# ---------------------------------------------------------------------------
# 2. DUPLICATES, COLLISIONS, ASCENDING ORDER
# ---------------------------------------------------------------------------
GROUP_ID_ORDERING = [
    {"invoice_id": "INV-2000", "amount": "100", "date": "2024-01-01", "vendor": "Acme"},
    {"invoice_id": "INV-2000", "amount": "100", "date": "2024-01-01", "vendor": "Acme"},   # exact duplicate
    {"invoice_id": "INV-2005", "amount": "200", "date": "2024-01-02", "vendor": "Beta"},
    {"invoice_id": "INV-2005", "amount": "999", "date": "2024-01-02", "vendor": "Beta"},   # same id, different amount -> collision
    {"invoice_id": "INV-2003", "amount": "300", "date": "2024-01-03", "vendor": "Gamma"},  # lower number than last seen (2005) -> out of order
    {"invoice_id": "INV-2010", "amount": "400", "date": "2024-01-04", "vendor": "Delta"},  # back in order, should be fine
    {"invoice_id": "INV-2010", "amount": "400", "date": "2024-01-04", "vendor": "Delta"},  # duplicate of the one right above
]

# ---------------------------------------------------------------------------
# 3. AMOUNT: FORMATS, OCR TYPOS, MISSING, ZERO/NEGATIVE, GARBAGE
# ---------------------------------------------------------------------------
GROUP_AMOUNT = [
    {"invoice_id": "INV-3001", "amount": "$1,200.00", "date": "2024-01-01", "vendor": "Acme"},  # clean formatted
    {"invoice_id": "INV-3002", "amount": "1200", "date": "2024-01-02", "vendor": "Acme"},        # plain int-like string
    {"invoice_id": "INV-3003", "amount": "1,200", "date": "2024-01-03", "vendor": "Acme"},       # comma no decimals
    {"invoice_id": "INV-3004", "amount": "95O.5", "date": "2024-01-04", "vendor": "Acme"},       # capital O typo
    {"invoice_id": "INV-3005", "amount": "l200.00", "date": "2024-01-05", "vendor": "Acme"},     # lowercase l typo
    {"invoice_id": "INV-3006", "amount": "I200.00", "date": "2024-01-06", "vendor": "Acme"},     # capital I typo
    {"invoice_id": "INV-3007", "amount": "9S0.00", "date": "2024-01-07", "vendor": "Acme"},      # unresolvable letter (S)
    {"invoice_id": "INV-3008", "amount": "", "date": "2024-01-08", "vendor": "Acme"},            # empty string
    {"invoice_id": "INV-3009", "amount": " ", "date": "2024-01-09", "vendor": "Acme"},           # whitespace only
    {"invoice_id": "INV-3010", "amount": None, "date": "2024-01-10", "vendor": "Acme"},          # None
    {"invoice_id": "INV-3011", "amount": "N/A", "date": "2024-01-11", "vendor": "Acme"},         # explicit N/A
    {"invoice_id": "INV-3012", "amount": "NA", "date": "2024-01-12", "vendor": "Acme"},          # "NA" - doesn't match "N/A" exactly, hits number parsing instead
    {"invoice_id": "INV-3013", "amount": "0", "date": "2024-01-13", "vendor": "Acme"},           # zero as string
    {"invoice_id": "INV-3014", "amount": 0, "date": "2024-01-14", "vendor": "Acme"},             # zero as int (falsy!)
    {"invoice_id": "INV-3015", "amount": 0.0, "date": "2024-01-15", "vendor": "Acme"},           # zero as float (falsy!)
    {"invoice_id": "INV-3016", "amount": "-450.00", "date": "2024-01-16", "vendor": "Acme"},     # negative string
    {"invoice_id": "INV-3017", "amount": -75.5, "date": "2024-01-17", "vendor": "Acme"},         # negative float
    {"invoice_id": "INV-3018", "amount": 1200, "date": "2024-01-18", "vendor": "Acme"},          # already an int
    {"invoice_id": "INV-3019", "amount": 1200.5, "date": "2024-01-19", "vendor": "Acme"},        # already a float
    {"invoice_id": "INV-3020", "amount": "$ 1200 ", "date": "2024-01-20", "vendor": "Acme"},     # dollar sign + spaces
    {"invoice_id": "INV-3021", "amount": "12.34.56", "date": "2024-01-21", "vendor": "Acme"},    # malformed number
    {"invoice_id": "INV-3022", "amount": "ABC", "date": "2024-01-22", "vendor": "Acme"},         # pure garbage
    {"invoice_id": "INV-3023", "amount": "1e10", "date": "2024-01-23", "vendor": "Acme"},        # scientific notation (valid float!)
    {"invoice_id": "INV-3024", "amount": [1, 2], "date": "2024-01-24", "vendor": "Acme"},        # wrong type entirely (list)
]

# ---------------------------------------------------------------------------
# 4. DATE: FORMATS, MISSING, INVALID, FUTURE, ORDER, GAPS
# ---------------------------------------------------------------------------
GROUP_DATE = [
    {"invoice_id": "INV-4001", "amount": "100", "date": "2024-01-05", "vendor": "Acme"},   # ISO format
    {"invoice_id": "INV-4002", "amount": "100", "date": "01/06/2024", "vendor": "Acme"},   # MM/DD/YYYY
    {"invoice_id": "INV-4003", "amount": "100", "date": "Jan 7, 2024", "vendor": "Acme"},  # abbreviated month
    {"invoice_id": "INV-4004", "amount": "100", "date": "January 8, 2024", "vendor": "Acme"},  # full month name
    {"invoice_id": "INV-4005", "amount": "100", "date": "2024/01/09", "vendor": "Acme"},   # slash ISO-like
    {"invoice_id": "INV-4006", "amount": "100", "date": "", "vendor": "Acme"},             # empty
    {"invoice_id": "INV-4007", "amount": "100", "date": None, "vendor": "Acme"},           # None
    {"invoice_id": "INV-4008", "amount": "100", "date": "2024-13-40", "vendor": "Acme"},   # invalid month/day
    {"invoice_id": "INV-4009", "amount": "100", "date": "not a date", "vendor": "Acme"},   # garbage text
    {"invoice_id": "INV-4010", "amount": "100", "date": "05-01-2024", "vendor": "Acme"},   # unsupported format (DD-MM-YYYY)
    {"invoice_id": "INV-4011", "amount": "100", "date": "2099-01-01", "vendor": "Acme"},   # future date
    {"invoice_id": "INV-4012", "amount": "100", "date": "2024-01-24", "vendor": "Acme"},   # goes BACKWARD vs 4011's baseline -> out of order (note: 4011 was future so didn't update last_valid_date... verify below)
    {"invoice_id": "INV-4013", "amount": "100", "date": "2024-06-01", "vendor": "Acme"},   # gap > 90 days from 4009's context
    {"invoice_id": "INV-4014", "amount": "100", "date": 20240105, "vendor": "Acme"},       # date as int, not string
]

# ---------------------------------------------------------------------------
# 5. VENDOR: MISSING, PLACEHOLDER, GARBAGE, SHORT, WHITESPACE
# ---------------------------------------------------------------------------
GROUP_VENDOR = [
    {"invoice_id": "INV-5001", "amount": "100", "date": "2024-01-01", "vendor": "Acme Corp"},     # normal
    {"invoice_id": "INV-5002", "amount": "100", "date": "2024-01-02", "vendor": ""},               # empty
    {"invoice_id": "INV-5003", "amount": "100", "date": "2024-01-03", "vendor": "   "},            # whitespace only
    {"invoice_id": "INV-5004", "amount": "100", "date": "2024-01-04", "vendor": None},             # None
    {"invoice_id": "INV-5005", "amount": "100", "date": "2024-01-05", "vendor": "N/A"},            # placeholder
    {"invoice_id": "INV-5006", "amount": "100", "date": "2024-01-06", "vendor": "unknown"},        # placeholder, lowercase
    {"invoice_id": "INV-5007", "amount": "100", "date": "2024-01-07", "vendor": "NULL"},           # placeholder
    {"invoice_id": "INV-5008", "amount": "100", "date": "2024-01-08", "vendor": "Unspecified"},    # placeholder, mixed case
    {"invoice_id": "INV-5009", "amount": "100", "date": "2024-01-09", "vendor": "@@@###"},         # no alnum chars (OCR garbage)
    {"invoice_id": "INV-5010", "amount": "100", "date": "2024-01-10", "vendor": "-----"},          # no alnum chars
    {"invoice_id": "INV-5011", "amount": "100", "date": "2024-01-11", "vendor": "X"},              # too short
    {"invoice_id": "INV-5012", "amount": "100", "date": "2024-01-12", "vendor": "  Acme   Corp  "},# extra internal/outer spaces (should normalize, not flag)
    {"invoice_id": "INV-5013", "amount": "100", "date": "2024-01-13", "vendor": "12345"},          # numeric-only vendor (currently passes - worth checking if intended)
    {"invoice_id": "INV-5014", "amount": "100", "date": "2024-01-14", "vendor": 12345},            # vendor as int, not string
]

# ---------------------------------------------------------------------------
# 6. STRUCTURAL EDGE CASES: missing keys, empty dict, extra keys
# ---------------------------------------------------------------------------
GROUP_STRUCTURAL = [
    {},  # completely empty record
    {"invoice_id": "INV-6002"},  # only invoice_id, everything else missing
    {"invoice_id": "INV-6003", "amount": "100", "date": "2024-01-03", "vendor": "Acme",
     "extra_field": "should just pass through untouched"},  # unexpected extra key
]

# ---------------------------------------------------------------------------
# 7. COMBINED STRESS TEST — everything mixed together in one real-looking batch
# ---------------------------------------------------------------------------
GROUP_STRESS = [
    {"invoice_id": "INV-7001", "amount": "$500.00", "date": "2024-02-01", "vendor": "Acme Corp"},        # clean
    {"invoice_id": "INV-7002", "amount": "75O.25", "date": "02/02/2024", "vendor": "Beta LLC"},          # OCR typo, clean otherwise
    {"invoice_id": "INV-7003", "amount": "N/A", "date": "2024-02-03", "vendor": "Gamma Inc"},            # bad amount only
    {"invoice_id": "INV-7003", "amount": "N/A", "date": "2024-02-03", "vendor": "Gamma Inc"},            # exact duplicate of the flagged one above
    {"invoice_id": "INV-7004", "amount": "-100.00", "date": "2024-02-04", "vendor": ""},                 # two problems at once
    {"invoice_id": "INV-7000", "amount": "200.00", "date": "2024-02-05", "vendor": "Delta Co"},          # out-of-order id
    {"invoice_id": "INV-7005", "amount": "300.00", "date": "2024-01-01", "vendor": "Epsilon LLC"},       # date out of order
    {"invoice_id": "INV-7006", "amount": "400.00", "date": "2024-06-01", "vendor": "Zeta Corp"},         # big gap (>90 days)
    {"invoice_id": "INV-7007", "amount": "abc123xyz", "date": "2024-06-02", "vendor": "N/A"},            # bad amount + placeholder vendor
    {"invoice_id": "INV-7008", "amount": "150.00", "date": "3024-01-01", "vendor": "Eta Inc"},           # far future date
]


if __name__ == "__main__":
    run_group("1. INVOICE ID FORMAT", GROUP_ID_FORMAT)
    run_group("2. DUPLICATES / COLLISIONS / ASCENDING ORDER", GROUP_ID_ORDERING)
    run_group("3. AMOUNT: FORMATS, TYPOS, MISSING, ZERO/NEGATIVE, GARBAGE", GROUP_AMOUNT)
    run_group("4. DATE: FORMATS, MISSING, INVALID, FUTURE, ORDER, GAPS", GROUP_DATE)
    run_group("5. VENDOR: MISSING, PLACEHOLDER, GARBAGE, SHORT, WHITESPACE", GROUP_VENDOR)
    run_group("6. STRUCTURAL EDGE CASES", GROUP_STRUCTURAL)
    run_group("7. COMBINED STRESS TEST", GROUP_STRESS)