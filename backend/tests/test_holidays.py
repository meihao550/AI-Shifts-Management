from datetime import date

from app.services.holidays import category_for, is_busy_day, is_weekend_or_holiday


def test_saturday_is_weekend():
    assert is_weekend_or_holiday(date(2025, 6, 7))  # Saturday
    assert category_for(date(2025, 6, 7)) == "weekend_or_holiday"


def test_weekday_is_weekday():
    assert not is_weekend_or_holiday(date(2025, 6, 4))  # Wednesday
    assert category_for(date(2025, 6, 4)) == "weekday"


def test_friday_is_busy_category():
    # 要件6.3: 金曜は繁忙区分（必要人数が多い）
    friday = date(2025, 6, 6)  # Friday
    assert is_busy_day(friday)
    assert category_for(friday) == "weekend_or_holiday"
    # 金曜は「週末」ではないが繁忙区分に含める
    assert not is_weekend_or_holiday(friday)
