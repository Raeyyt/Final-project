"""School calendar helpers (academic year label)."""
from datetime import date


def current_academic_year_label(today: date | None = None) -> str:
    """Label like '2025-2026'. Year starts in September (common school pattern)."""
    d = today or date.today()
    y = d.year
    if d.month >= 9:
        return f"{y}-{y + 1}"
    return f"{y - 1}-{y}"
