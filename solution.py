from datetime import datetime, date
import re
from dataclasses import dataclass, field
from typing import Any


# --- Constants ---
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d"]
PLACEHOLDER_VENDORS = {"N/A", "UNKNOWN", "NULL", "UNSPECIFIED"}


@dataclass
class ValidationResult:
    value: object
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_invoice_id(record: dict, seen_records: dict, last_id_num: int) -> ValidationResult:
    """
    Validates invoice_id and checks for ascending order / duplicates.
    value = the parsed numeric id (int) if valid, else the raw invoice_id string.
    """
    errors = []
    invoice_id = record.get("invoice_id", "")

    # Check for missing or empty invoice_id
    if not invoice_id or not str(invoice_id).strip():
        errors.append("Invoice ID is missing or empty")
        return ValidationResult(invoice_id, errors)

    # Check format, must be "INV-" followed by digits
    if not isinstance(invoice_id, str) or not re.match(r"^INV-\d+$", invoice_id):
        errors.append("Invalid invoice_id format")
        return ValidationResult(invoice_id, errors)

    # Extract the numeric part for order checking
    current_id_num = int(invoice_id.split("-")[1])

    # Check for duplication
    if invoice_id in seen_records:
        # Check if it's an exact duplicate of the previously seen record
        if record == seen_records[invoice_id]:
            errors.append("Record duplication")
        else:
            errors.append("ID collision (wrong ID or conflicting data)")
        return ValidationResult(current_id_num, errors)
        
    seen_records[invoice_id] = record.copy() # Store a copy of the record to avoid mutation issues

    if current_id_num <= last_id_num:
        errors.append("Invoice ID is out of ascending order")

    return ValidationResult(current_id_num, errors)


def validate_normalize_amount(amount_raw: Any) -> ValidationResult:
    """
    Cleans up, formats, and validates the amount.
    value = formatted (or original) string.
    """
    errors = []

    # Check for empty or N/A
    is_missing = amount_raw is None or (
        isinstance(amount_raw, str) and (not amount_raw.strip() or amount_raw.strip().upper() == "N/A")
    )

    if is_missing:
        errors.append("Amount is missing or N/A")
        return ValidationResult(str(amount_raw), errors)

    amount_str = str(amount_raw).strip()
    amount_str = amount_str.replace("$", "").replace(" ", "")
    # Fix common OCR typos
    amount_str = amount_str.replace("O", "0").replace("o", "0")
    amount_str = amount_str.replace("I", "1").replace("i", "1").replace("l", "1")

    # Check for random/unresolvable letters remaining
    if re.search(r"[a-zA-Z]", amount_str):
        errors.append("Amount contains unresolvable letters")
        return ValidationResult(amount_str, errors)

    # Try to parse to float (strip commas first)
    clean_num_str = amount_str.replace(",", "")
    try:
        val = float(clean_num_str)
    except ValueError:
        errors.append("Amount is not a valid number")
        return ValidationResult(amount_str, errors)

    if val <= 0:
        errors.append("Amount is zero or negative")

    # Normalize formatting to exactly 2 decimal places with commas
    formatted_amount = f"-${val:,.2f}" if val < 0 else f"${val:,.2f}"
    return ValidationResult(formatted_amount, errors)


def validate_normalize_date(date_raw: str, last_valid_date: date | None) -> ValidationResult:
    """
    Validates date existence, order, gaps, and formats.
    value = normalized_date_str (or original raw string if invalid).
    """
    errors = []
    parsed_date = None

    # Check for missing date
    if not date_raw or not str(date_raw).strip():
        errors.append("Date is missing")
        return ValidationResult(date_raw, errors)

    date_str = str(date_raw).strip()

    # Parse the date
    for fmt in DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(date_str, fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        errors.append("Invalid date format or non-existent date")
        return ValidationResult(date_str, errors)

    # Future date check
    if parsed_date > datetime.today().date():
        errors.append("Date is in the future")

    # Chronological order and gap checks
    if last_valid_date:
        if parsed_date < last_valid_date:
            errors.append("Date is out of chronological order")
        elif (parsed_date - last_valid_date).days > 90:
            errors.append("Gap between invoices exceeds 90 days")

    return ValidationResult(parsed_date, errors)


def validate_vendor(vendor_raw: str) -> ValidationResult:
    """
    Validates the vendor name for garbage OCR reads and placeholders.
    value = normalized_vendor_str (str).
    """
    errors = []

    # Check for missing vendor
    if not vendor_raw or not str(vendor_raw).strip():
        errors.append("Vendor is missing or empty")
        return ValidationResult(vendor_raw, errors)

    vendor_str = str(vendor_raw).strip()

    # Check for placeholders
    if vendor_str.upper() in PLACEHOLDER_VENDORS:
        errors.append("Vendor is a placeholder")

    # Garbage check, must contain at least one valid letter or number
    if not re.search(r"[a-zA-Z0-9]", vendor_str):
        errors.append("Vendor name does not contain valid letters or numbers (likely OCR garbage)")

    # Length check
    if len(vendor_str) < 2:
        errors.append("Vendor name is unusually short")

    # Normalization: Replace multiple spaces with a single space
    normalized_vendor = re.sub(r"\s+", " ", vendor_str)

    return ValidationResult(normalized_vendor, errors)


def process_records(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Takes the raw records and returns (clean_records, flagged_records).
    Flagged records should also include a 'reason' field explaining why
    they were flagged.
    """

    cleaned_records = []
    flagged_records = []

    seen_records = {}  # To track unique invoice_ids
    last_id_num = -1 # To track the last invoice_id number for ascending order
    last_valid_date = None # To track the last valid date for chronological order

    expected_keys = {"invoice_id", "amount", "date", "vendor"}

    for record in raw_records:
        # Work with a copy to avoid mutating the original
        current_record = record.copy()

        # --- Check for extra keys ---
        actual_keys = set(current_record.keys())
        extra_keys = actual_keys - expected_keys

        if extra_keys:
            # We can flag it and immediately skip
            current_record["reason"] = f"Extra keys found: {'; '.join(extra_keys)}"
            flagged_records.append(current_record)
            continue  # Skip further processing for this record

        # --- Invoice ID validation ---
        id_result = validate_invoice_id(current_record, seen_records, last_id_num)
        if not id_result.errors:
            last_id_num = id_result.value

        if "Record duplication" in id_result.errors:
            current_record["reason"] = "Record duplication"
            flagged_records.append(current_record)
            continue  # Skip further processing for this record

        reasons = list(id_result.errors)  # picks up or format errors, not duplication

        # --- Amount validation ---
        amount_result = validate_normalize_amount(current_record.get("amount", ""))
        current_record["amount"] = amount_result.value
        reasons.extend(amount_result.errors)

        # --- Date validation ---
        date_result = validate_normalize_date(current_record.get("date", ""), last_valid_date)
        reasons.extend(date_result.errors)

        if date_result.errors and not isinstance(date_result.value, date):
            current_record["date"] = date_result.value  # raw string, parsing failed
        else:
            # Normalize date to YYYY-MM-DD format
            current_record["date"] = date_result.value.strftime("%Y-%m-%d")
            if not date_result.errors:
                last_valid_date = date_result.value  # Update last_valid_date only if the date is valid

        # --- Vendor validation ---
        vendor_result = validate_vendor(current_record.get("vendor", ""))
        current_record["vendor"] = vendor_result.value
        reasons.extend(vendor_result.errors)

        if reasons:
            current_record["reason"] = "; ".join(reasons)
            flagged_records.append(current_record)
        else:
            cleaned_records.append(current_record)

    return cleaned_records, flagged_records


if __name__ == "__main__":
    raw_records = [
        {"invoice_id": "INV-1001", "amount": "$1,200.00", "date": "2024-01-05", "vendor": "Acme Corp"},
        {"invoice_id": "INV-1002", "amount": "95O.5", "date": "01/06/2024", "vendor": "Beta LLC"},
        {"invoice_id": "INV-1003", "amount": "N/A", "date": "2024-01-07", "vendor": "Acme Corp"},
        {"invoice_id": "INV-1004", "amount": "2,340", "date": "Jan 8, 2024", "vendor": ""},
        {"invoice_id": "INV-1001", "amount": "$1,200.00", "date": "2024-01-05", "vendor": "Acme Corp"},
        {"invoice_id": "INV-1005", "amount": "-450.00", "date": "2024-13-40", "vendor": "Gamma Inc"},
        {"invoice_id": "INV-1006", "amount": " ", "date": "2024/01/09", "vendor": "Delta Co"},
        {"invoice_id": "INV-1007", "amount": "3200.00", "date": "2019-01-10", "vendor": "Acme Corp"},
        ]

    cleaned, flagged = process_records(raw_records)
    print(f"CLEANED RECORDS:")
    for rec in cleaned:
        print(rec)
    print()

    print(f"FLAGGED RECORDS:")
    for rec in flagged:
        print(rec)
