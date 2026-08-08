### Invoice Validation — Design Notes

**1. Assumptions Made**

* **Amounts:** I assumed invoice amounts must be greater than $0, and that amounts may include standard formatting such as `$` signs and commas. Since the input may come from OCR, I correct a few obvious numeric misreads (`O→0`, `I/l→1`) before parsing. If a value still can't be parsed confidently, I flag it rather than guessing.
* **Dates:** I support several common date formats, including ISO, US-style dates, and dates with month names. For ambiguous dates, I assume US formatting (`MM/DD/YYYY`). Future dates are considered invalid, and I flag invoices that are out of chronological order or have a gap of more than 90 days from the previous invoice.
* **Invoice IDs:** I assume valid IDs follow the `INV-\d+` format and should appear in ascending numerical order.
* **Vendors:** I treat common placeholders such as `N/A`, `UNKNOWN`, `NULL`, and `UNSPECIFIED`, as well as strings made only of special characters, as invalid. I require vendor names to contain at least 3 characters.

I kept the configurable values, such as supported date formats and placeholder vendor names, as constants rather than hardcoding them throughout the validation logic. This makes the rules easier to update if the input format changes.

**2. Judgment Calls / Limitations**

* I run all validations on a record instead of stopping at the first error, so a record can report multiple issues at once.
* If an invoice ID is out of order, I don't use it as the new baseline. This prevents one incorrect ID from affecting later comparisons.
* Numeric-only vendor names currently pass validation. I chose not to enforce stricter name validation because it could reject legitimate vendor names.
* OCR correction is intentionally limited to obvious numeric misreads. I prefer flagging an uncertain value rather than silently changing it.

**3. Edge Cases I Checked**

* A numeric `0` is falsy in Python, so I made sure it is treated as an actual amount and flagged as invalid rather than being reported as missing.
* A future date must not update the chronological baseline. Otherwise, one future-dated invoice could cause all following valid dates to be incorrectly flagged.
