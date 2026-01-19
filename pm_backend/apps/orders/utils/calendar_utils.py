"""
カレンダー営業日計算ユーティリティ

得意先のカレンダーに基づいて営業日を計算する共通関数を提供します。
"""
from datetime import date, datetime, timedelta
from typing import Optional
from django.db.models import Q
from masters.models import Calendar, CalendarDay


# 日替わり時刻（8時）
DAY_BOUNDARY_HOUR = 8


def get_business_today() -> date:
    """日替わり時刻（8時）を考慮した「今日」を取得

    弊社では日替わり時刻を8:00としています。
    - 1月19日 7:59 → 1月18日として扱う
    - 1月19日 8:00 → 1月19日として扱う

    Returns:
        業務上の「今日」の日付
    """
    now = datetime.now()
    if now.hour < DAY_BOUNDARY_HOUR:
        # 8時より前なら前日扱い
        return (now - timedelta(days=1)).date()
    return now.date()


def get_business_yesterday() -> date:
    """8時区切りの「昨日」を取得

    Returns:
        業務上の「昨日」の日付
    """
    return get_business_today() - timedelta(days=1)


class WorkingDayCalculator:
    """営業日計算クラス

    カレンダーに基づいて営業日を計算します。
    カレンダーが未設定の場合は週末判定（月～金を営業日）で代替します。
    """

    def __init__(self, calendar: Optional[Calendar] = None):
        """
        Args:
            calendar: カレンダマスタ。Noneの場合は週末判定を使用。
        """
        self.calendar = calendar
        self._cache = {}  # 営業日判定のキャッシュ

    def is_working_day(self, target_date: date) -> bool:
        """指定日が営業日かどうかを判定

        Args:
            target_date: 判定する日付

        Returns:
            営業日の場合True、休日の場合False
        """
        if not self.calendar:
            # カレンダー未設定の場合、週末判定（月～金を営業日とする）
            return target_date.weekday() < 5

        # キャッシュをチェック
        if target_date in self._cache:
            return self._cache[target_date]

        # カレンダから営業日を取得
        cal_day = CalendarDay.objects.filter(
            calendar=self.calendar,
            target_date=target_date
        ).first()

        is_working = cal_day.is_working_day if cal_day else (target_date.weekday() < 5)

        # キャッシュに保存
        self._cache[target_date] = is_working

        return is_working

    def subtract_working_days(self, base_date: date, days: int) -> date:
        """営業日を逆算

        指定した日付から指定営業日数を遡った日付を返します。

        Args:
            base_date: 基準日（納期など）
            days: 逆算する営業日数（正の整数）

        Returns:
            逆算した日付（出荷日など）

        Examples:
            >>> calc = WorkingDayCalculator(calendar)
            >>> # 2026-01-15（水）から2営業日前
            >>> calc.subtract_working_days(date(2026, 1, 15), 2)
            date(2026, 1, 13)  # 月曜日（土日をスキップ）
        """
        if days <= 0:
            return base_date

        remaining = days
        current = base_date

        while remaining > 0:
            current = current - timedelta(days=1)

            if self.is_working_day(current):
                remaining -= 1

        return current

    def add_working_days(self, base_date: date, days: int) -> date:
        """営業日を加算

        指定した日付から指定営業日数を進めた日付を返します。

        Args:
            base_date: 基準日
            days: 加算する営業日数（正の整数）

        Returns:
            加算した日付

        Examples:
            >>> calc = WorkingDayCalculator(calendar)
            >>> # 2026-01-13（月）から2営業日後
            >>> calc.add_working_days(date(2026, 1, 13), 2)
            date(2026, 1, 15)  # 水曜日（土日をスキップ）
        """
        if days <= 0:
            return base_date

        remaining = days
        current = base_date

        while remaining > 0:
            current = current + timedelta(days=1)

            if self.is_working_day(current):
                remaining -= 1

        return current

    def get_prev_working_day(self, target_date: date) -> date:
        """直前の営業日を取得

        Args:
            target_date: 基準日

        Returns:
            直前の営業日
        """
        prev_date = target_date - timedelta(days=1)

        if not self.calendar:
            # カレンダー未設定の場合、週末をスキップ
            while prev_date.weekday() >= 5:
                prev_date = prev_date - timedelta(days=1)
            return prev_date

        while not self.is_working_day(prev_date):
            prev_date = prev_date - timedelta(days=1)

        return prev_date

    def get_next_working_day(self, target_date: date) -> date:
        """直後の営業日を取得

        Args:
            target_date: 基準日

        Returns:
            直後の営業日
        """
        next_date = target_date + timedelta(days=1)

        if not self.calendar:
            # カレンダー未設定の場合、週末をスキップ
            while next_date.weekday() >= 5:
                next_date = next_date + timedelta(days=1)
            return next_date

        while not self.is_working_day(next_date):
            next_date = next_date + timedelta(days=1)

        return next_date


def subtract_working_days(base_date: date, days: int, calendar: Optional[Calendar] = None) -> date:
    """営業日を逆算（関数版）

    Args:
        base_date: 基準日（納期など）
        days: 逆算する営業日数（正の整数）
        calendar: カレンダマスタ。Noneの場合は週末判定を使用。

    Returns:
        逆算した日付（出荷日など）
    """
    calculator = WorkingDayCalculator(calendar)
    return calculator.subtract_working_days(base_date, days)


def add_working_days(base_date: date, days: int, calendar: Optional[Calendar] = None) -> date:
    """営業日を加算（関数版）

    Args:
        base_date: 基準日
        days: 加算する営業日数（正の整数）
        calendar: カレンダマスタ。Noneの場合は週末判定を使用。

    Returns:
        加算した日付
    """
    calculator = WorkingDayCalculator(calendar)
    return calculator.add_working_days(base_date, days)
