from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


MONEY_PLACES = Decimal("0.01")


def quantize_money(value):
    return Decimal(value).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def clamp_day(year, month, day):
    return min(day, monthrange(year, month)[1])


def add_months(source_date, months, day=None):
    month_index = (source_date.month - 1) + months
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    target_day = clamp_day(year, month, day or source_date.day)
    return date(year, month, target_day)


def month_bounds(year, month):
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def next_due_date(start_date, due_day):
    current_month_day = clamp_day(start_date.year, start_date.month, due_day)
    if start_date.day <= current_month_day:
        return date(start_date.year, start_date.month, current_month_day)
    return add_months(start_date.replace(day=1), 1, due_day)
