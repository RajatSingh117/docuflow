import re
from datetime import datetime
from typing import Optional
import dateutil.parser


def normalize_date(val: Optional[str]) -> Optional[str]:
    """Parse various date formats into standard ISO 8601 (YYYY-MM-DD)."""
    if not val:
        return None
    val_clean = str(val).strip()
    try:
        # Use dateutil parser to handle diverse date formats
        dt = dateutil.parser.parse(val_clean, fuzzy=True, dayfirst=False)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # Fallback regex checks
        match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', val_clean)
        if match:
            y, m, d = match.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        return val_clean


def normalize_amount(val: Optional[str]) -> Optional[float]:
    """Clean monetary values into a standard float number."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    # Remove currency symbols and non-numeric except . and ,
    s = re.sub(r'[^\d.,-]', '', s)
    if not s:
        return None

    # Handle European decimal formatting (e.g., 1.250,50 -> 1250.50)
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        # Check if comma represents decimal or thousands
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')

    try:
        return float(s)
    except ValueError:
        return None


def normalize_currency(val: Optional[str]) -> str:
    """Normalize currency symbols to ISO 4217 standard codes."""
    if not val:
        return "USD"
    s = str(val).strip().upper()
    if "$" in s or "USD" in s:
        return "USD"
    elif "€" in s or "EUR" in s:
        return "EUR"
    elif "£" in s or "GBP" in s:
        return "GBP"
    elif "₹" in s or "INR" in s:
        return "INR"
    elif "CAD" in s:
        return "CAD"
    elif "AUD" in s:
        return "AUD"
    return "USD"


def normalize_phone(val: Optional[str]) -> Optional[str]:
    """Format phone numbers to clean digits and standard separators."""
    if not val:
        return None
    digits = re.sub(r'\D', '', str(val))
    if len(digits) == 10:
        return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return str(val).strip()


def normalize_text(val: Optional[str]) -> Optional[str]:
    """Normalize whitespace and strip extra formatting characters."""
    if not val:
        return None
    return re.sub(r'\s+', ' ', str(val)).strip()
