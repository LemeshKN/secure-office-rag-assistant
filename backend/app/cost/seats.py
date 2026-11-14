import io
from datetime import date, datetime, timedelta

import pandas as pd

from app.cost.budget_period import KOLKATA

REQUIRED_COLUMNS = [
    "user_name", "department", "seat_type",
    "assigned_date", "last_active_date", "messages_last_30_days",
]
SEAT_TYPES = ("standard", "premium")
ACTIVE_DAYS = 30
DOWNGRADE_BELOW = 20  # active premium seats under this many messages are downgrade candidates


class SeatDataError(ValueError):
    """A problem with the uploaded CSV or the prices. The message is safe to show."""


def today_kolkata() -> date:
    return datetime.now(KOLKATA).date()


def parse_seats(content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        raise SeatDataError("The file is empty.")
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise SeatDataError(f"Could not read the file as CSV: {exc.__class__.__name__}.")

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SeatDataError(
            f"Missing columns: {', '.join(missing)}. Expected: {', '.join(REQUIRED_COLUMNS)}."
        )
    if df.empty:
        raise SeatDataError("The CSV has no rows.")
    return df[REQUIRED_COLUMNS]


def _date(value: str, column: str, line: int, errors: list[str]) -> date | None:
    value = value.strip()
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        errors.append(f"Row {line}: {column} '{value}' is not a valid date. Use YYYY-MM-DD.")
        return None
    return parsed.date()


def _clean_rows(df: pd.DataFrame) -> list[dict]:
    rows, errors = [], []
    for index, raw in df.iterrows():
        line = index + 2  # line 1 is the header
        seat_type = raw["seat_type"].strip().lower()
        if seat_type not in SEAT_TYPES:
            errors.append(f"Row {line}: seat_type must be standard or premium (found '{raw['seat_type']}').")
            continue

        text = raw["messages_last_30_days"].strip()
        try:
            messages = int(float(text)) if text else 0
            if messages < 0:
                raise ValueError
        except ValueError:
            errors.append(f"Row {line}: messages_last_30_days must be a whole number of 0 or more (found '{text}').")
            continue

        name = raw["user_name"].strip()
        last_active = None
        if name:  # dates only matter for assigned seats
            _date(raw["assigned_date"], "assigned_date", line, errors)
            last_active = _date(raw["last_active_date"], "last_active_date", line, errors)
        rows.append({
            "user_name": name,
            "department": raw["department"].strip(),
            "seat_type": seat_type,
            "last_active": last_active,
            "messages": messages,
        })
    if errors:
        shown = errors[:5]
        extra = f" (and {len(errors) - 5} more)" if len(errors) > 5 else ""
        raise SeatDataError(" ".join(shown) + extra)
    return rows


def analyze_seats(df: pd.DataFrame, standard_price: float, premium_price: float, today: date) -> dict:
    if standard_price < 0 or premium_price < 0:
        raise SeatDataError("Seat prices cannot be negative.")
    if premium_price < standard_price:
        raise SeatDataError("The premium price must be at least the standard price.")
    price = {"standard": standard_price, "premium": premium_price}

    unused = inactive = downgrade = active = assigned = 0
    unused_saving = inactive_saving = downgrade_saving = 0.0
    seats = []

    for row in _clean_rows(df):
        if not row["user_name"]:
            status = "unused"
            unused += 1
            unused_saving += price[row["seat_type"]]
        else:
            assigned += 1
            last = row["last_active"]
            is_active = last is not None and (today - last).days <= ACTIVE_DAYS and row["messages"] >= 1
            if not is_active:
                status = "inactive"
                inactive += 1
                inactive_saving += price[row["seat_type"]]
            else:
                active += 1
                if row["seat_type"] == "premium" and row["messages"] < DOWNGRADE_BELOW:
                    status = "downgrade"
                    downgrade += 1
                    downgrade_saving += premium_price - standard_price
                else:
                    status = "active"
        seats.append({
            "user_name": row["user_name"] or "(unassigned)",
            "department": row["department"],
            "seat_type": row["seat_type"],
            "messages_last_30_days": row["messages"],
            "status": status,
        })

    total = unused_saving + inactive_saving + downgrade_saving
    return {
        "metrics": {
            "seats_purchased": len(seats),
            "seats_assigned": assigned,
            "active_users": active,
            "inactive_assigned": inactive,
            "unused_seats": unused,
            "downgrade_candidates": downgrade,
            "potential_monthly_saving": round(total, 2),
        },
        "saving_breakdown": [
            {"reason": "Unused paid seats", "seats": unused, "saving": round(unused_saving, 2)},
            {"reason": "Inactive assigned seats", "seats": inactive, "saving": round(inactive_saving, 2)},
            {"reason": "Premium seats to downgrade", "seats": downgrade, "saving": round(downgrade_saving, 2)},
        ],
        "prices": price,
        "as_of": today.isoformat(),
        "seats": seats,
    }


def sample_csv(today: date) -> str:
    """20 demo seats with dates relative to today: 11 active, 5 inactive, 4 unused."""

    def d(days_ago: int | None) -> str:
        return "" if days_ago is None else (today - timedelta(days=days_ago)).isoformat()

    # name, department, seat type, assigned days ago, last active days ago, messages
    rows = [
        ("Aarav", "Engineering", "standard", 200, 1, 60),
        ("Diya", "Engineering", "standard", 200, 2, 45),
        ("Kabir", "HR", "standard", 180, 3, 30),
        ("Meera", "HR", "standard", 150, 5, 22),
        ("Rohan", "Platform", "standard", 150, 7, 18),
        ("Sana", "Platform", "standard", 120, 10, 15),
        ("Ishaan", "Engineering", "premium", 200, 1, 80),
        ("Tara", "Engineering", "premium", 200, 2, 45),
        ("Vikram", "Engineering", "premium", 190, 2, 4),
        ("Neha", "HR", "premium", 190, 4, 9),
        ("Arjun", "Platform", "premium", 160, 6, 12),
        ("Pooja", "HR", "standard", 170, 5, 0),
        ("Rahul", "Engineering", "standard", 170, 45, 0),
        ("Anjali", "Platform", "standard", 160, 90, 0),
        ("Dev", "Engineering", "premium", 220, 75, 0),
        ("Zoya", "HR", "premium", 220, 120, 0),
        ("", "", "standard", None, None, 0),
        ("", "", "standard", None, None, 0),
        ("", "", "standard", None, None, 0),
        ("", "", "standard", None, None, 0),
    ]
    frame = pd.DataFrame(
        [(n, dept, t, d(a), d(last), m) for n, dept, t, a, last, m in rows],
        columns=REQUIRED_COLUMNS,
    )
    return frame.to_csv(index=False)