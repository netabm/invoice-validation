### Invoice Validation - Design Notes

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

* **Zero amounts:** Python treats 0 as falsy, so I made sure a submitted 0 is treated as an actual amount and flagged as invalid, rather than as a missing value.
* **Future dates:** A future-dated invoice must not update the chronological baseline, otherwise it could cause subsequent valid dates to be incorrectly flagged.
* **Multiple validation errors:** I report all applicable errors for a record instead of stopping at the first one. Exact duplicates are the exception and are skipped to avoid redundant processing.
* **Input integrity:** I don't modify the original input records; each record is copied before processing.
* **Order-dependent validation:** Checks such as ID and date ordering depend on previous valid records, so the same invoice can produce a different result depending on where it appears in the input sequence.

**4. How I Used AI Tools**

I used Gemini and Claude as pair-programming and review tools, mainly for brainstorming, code review, and identifying edge cases. I did not treat the generated code as final, I tested the suggestions against the sample data and made changes when the behavior didn't match what I expected.

* **Initial implementation (Gemini):** Used Gemini to help build the initial validation logic for invoice IDs, amounts, vendors, and dates, as well as the ValidationResult structure and schema validation.
* **Code review (Claude):** Claude helped identify inconsistencies in the validators' return values. I refactored them so all validators return the same ValidationResult(value, errors) structure.
* **State management (Claude):** We also reviewed how chronological and ID-order state should be handled. I kept this state in the main processing loop rather than mixing it into the individual validators, keeping the validators focused on validating individual fields.
* **Testing and edge cases (Gemini & Claude):** I used both tools to question and test edge cases such as zero amounts, duplicate records, and future dates. I verified the behavior against the sample data and adjusted the implementation where needed.

https://share.gemini.google/vHF7PvDVPY2C
https://claude.ai/share/14588398-d775-4cd1-b967-eef2ca2e9bf3