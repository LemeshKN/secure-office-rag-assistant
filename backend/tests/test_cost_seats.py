from datetime import date, timedelta

import pytest

from app.cost.seats import SeatDataError, analyze_seats, parse_seats, sample_csv

TODAY = date(2026, 11, 14)
HEADER = "user_name,department,seat_type,assigned_date,last_active_date,messages_last_30_days\n"


def run(*rows, std=20.0, prem=30.0):
    text = HEADER + "\n".join(rows) + "\n"
    return analyze_seats(parse_seats(text.encode()), std, prem, TODAY)


SMALL = (
    "Asha,Eng,standard,2026-01-01,2026-11-10,30",   # active
    "Ben,Eng,premium,2026-01-01,2026-11-12,5",      # active premium, under 20 messages: downgrade
    "Cara,HR,premium,2026-01-01,2026-11-13,25",     # active premium, busy
    "Dev,HR,standard,2026-01-01,2026-08-01,0",      # inactive
    ",,premium,,,",                                 # unused premium seat
)


def test_sample_matches_the_plan_numbers():
    result = analyze_seats(parse_seats(sample_csv(TODAY).encode()), 20.0, 30.0, TODAY)
    assert result["metrics"] == {
        "seats_purchased": 20, "seats_assigned": 16, "active_users": 11,
        "inactive_assigned": 5, "unused_seats": 4, "downgrade_candidates": 3,
        "potential_monthly_saving": 230.0,
    }


def test_small_known_csv():
    m = run(*SMALL)["metrics"]
    assert m["seats_purchased"] == 5
    assert m["seats_assigned"] == 4
    assert m["active_users"] == 3
    assert m["inactive_assigned"] == 1
    assert m["unused_seats"] == 1
    assert m["downgrade_candidates"] == 1
    assert m["potential_monthly_saving"] == 60.0  # 30 unused premium + 20 inactive + 10 downgrade


def test_custom_prices():
    assert run(*SMALL, std=10.0, prem=25.0)["metrics"]["potential_monthly_saving"] == 50.0


def test_thirty_days_is_active_and_thirty_one_is_not():
    last30 = (TODAY - timedelta(days=30)).isoformat()
    last31 = (TODAY - timedelta(days=31)).isoformat()
    m = run(f"A,Eng,standard,2026-01-01,{last30},3", f"B,Eng,standard,2026-01-01,{last31},3")["metrics"]
    assert m["active_users"] == 1
    assert m["inactive_assigned"] == 1


def test_recent_date_with_zero_messages_is_inactive():
    m = run("A,Eng,standard,2026-01-01,2026-11-13,0")["metrics"]
    assert m["inactive_assigned"] == 1
    assert m["active_users"] == 0


def test_downgrade_boundary_is_twenty_messages():
    m = run("A,Eng,premium,2026-01-01,2026-11-13,19", "B,Eng,premium,2026-01-01,2026-11-13,20")["metrics"]
    assert m["downgrade_candidates"] == 1


@pytest.mark.parametrize("content, message", [
    (b"", "empty"),
    (HEADER.encode(), "no rows"),
    (b"user_name,department,seat_type\nA,B,standard\n", "Missing columns"),
    ((HEADER + "A,Eng,gold,2026-01-01,2026-11-10,5\n").encode(), "seat_type"),
    ((HEADER + "A,Eng,standard,2026-01-01,2026-11-10,abc\n").encode(), "messages_last_30_days"),
    ((HEADER + "A,Eng,standard,2026-01-01,not-a-date,5\n").encode(), "last_active_date"),
])
def test_bad_csv_gives_clear_error(content, message):
    with pytest.raises(SeatDataError, match=message):
        analyze_seats(parse_seats(content), 20.0, 30.0, TODAY)


@pytest.mark.parametrize("std, prem", [(-1.0, 30.0), (30.0, 20.0)])
def test_bad_prices_are_rejected(std, prem):
    with pytest.raises(SeatDataError):
        run(*SMALL, std=std, prem=prem)