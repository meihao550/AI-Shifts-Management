from datetime import date

from app.services.holidays import category_for, is_weekend_or_holiday


def test_saturday_is_weekend():
    assert is_weekend_or_holiday(date(2025, 6, 7))  # Saturday
    assert category_for(date(2025, 6, 7)) == "weekend_or_holiday"


def test_weekday_is_weekday():
    assert not is_weekend_or_holiday(date(2025, 6, 4))  # Wednesday
    assert category_for(date(2025, 6, 4)) == "weekday"
