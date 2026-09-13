"""Working-time calendar that reproduces the date arithmetic of onlinegantt.com
(Syncfusion Gantt, taskType "fixedDuration").

All datetimes handled here are *naive local* datetimes in the plan's timezone.
Conversion to/from the UTC ISO strings stored in .gantt files lives in tz.py.

Verified against the live site (2026-09-13):
- durations are counted in working hours; "1 day" == the sum of the work-time
  ranges (8 h with the default 08-12 + 13-17);
- a task that would start outside working time snaps forward to the next
  working instant (weekends, holidays and the lunch gap are skipped);
- an end that lands exactly on the end of a work range stays there (12:00 or 17:00);
- dependency lags are counted in working time too ("+2 days" == 16 working hours).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, List, Sequence, Set, Tuple

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_EPS = 1e-9


def _to_datetime(d: date | datetime) -> datetime:
    if isinstance(d, datetime):
        return d
    return datetime(d.year, d.month, d.day)


class WorkCalendar:
    def __init__(self, work_week: Sequence[str], work_time: Sequence[dict], holidays: Iterable[Tuple[date, date]] = ()):
        bad = [d for d in work_week if d not in DAY_NAMES]
        if bad:
            raise ValueError(f"Unknown work-week day names: {bad} (use English names like 'Sunday')")
        self.work_week = list(work_week)
        self.work_days: Set[int] = {DAY_NAMES.index(d) for d in work_week}
        if not self.work_days:
            raise ValueError("workWeek must contain at least one day")
        ranges: List[Tuple[float, float]] = []
        for r in work_time:
            f, t = float(r["from"]), float(r["to"])
            if t == 24:
                t = 24.0
            if not (0 <= f < t <= 24):
                raise ValueError(f"Invalid work-time range {r}: 'from' must be before 'to' (hours 0-24)")
            ranges.append((f, t))
        ranges.sort()
        for a, b in zip(ranges, ranges[1:]):
            if b[0] < a[1]:
                raise ValueError(f"Work-time ranges overlap: {ranges}")
        if not ranges:
            raise ValueError("workTime must contain at least one range")
        self.ranges = ranges
        self.hours_per_day = sum(t - f for f, t in ranges)
        self.holiday_days: Set[date] = set()
        for frm, to in holidays:
            d = frm
            while d <= to:
                self.holiday_days.add(d)
                d += timedelta(days=1)

    # ------------------------------------------------------------------ days
    def is_work_day(self, d: date) -> bool:
        return d.weekday() in self.work_days and d not in self.holiday_days

    def day_ranges(self, d: date) -> List[Tuple[datetime, datetime]]:
        if not self.is_work_day(d):
            return []
        base = datetime(d.year, d.month, d.day)
        return [(base + timedelta(hours=f), base + timedelta(hours=t)) for f, t in self.ranges]

    def day_start(self, d: date) -> datetime:
        """First working instant of a calendar day (or the next working day)."""
        return self.next_working_time(datetime(d.year, d.month, d.day))

    def day_end(self, d: date) -> datetime:
        """Last working instant of a calendar day (or the previous working day)."""
        return self.prev_working_time(datetime(d.year, d.month, d.day) + timedelta(days=1))

    def next_work_day(self, d: date) -> date:
        d = d + timedelta(days=1)
        guard = 0
        while not self.is_work_day(d):
            d += timedelta(days=1)
            guard += 1
            if guard > 3660:
                raise ValueError("No working day found within 10 years - check workWeek/holidays")
        return d

    def prev_work_day(self, d: date) -> date:
        d = d - timedelta(days=1)
        guard = 0
        while not self.is_work_day(d):
            d -= timedelta(days=1)
            guard += 1
            if guard > 3660:
                raise ValueError("No working day found within 10 years - check workWeek/holidays")
        return d

    # --------------------------------------------------------------- instants
    def next_working_time(self, dt: datetime) -> datetime:
        """Smallest working instant >= dt (a range end such as 17:00 is NOT a working start)."""
        d = dt.date()
        guard = 0
        while True:
            for s, e in self.day_ranges(d):
                if s <= dt < e:
                    return dt
                if dt < s:
                    return s
            d = self.next_work_day(d)
            dt = datetime(d.year, d.month, d.day)
            guard += 1
            if guard > 3660:
                raise ValueError("No working time found")

    def prev_working_time(self, dt: datetime) -> datetime:
        """Largest working instant <= dt that can END work (a range start such as 08:00 is not)."""
        d = dt.date()
        guard = 0
        while True:
            for s, e in reversed(self.day_ranges(d)):
                if s < dt <= e:
                    return dt
                if dt > e:
                    return e
            d = self.prev_work_day(d)
            dt = datetime(d.year, d.month, d.day) + timedelta(days=1)
            guard += 1
            if guard > 3660:
                raise ValueError("No working time found")

    def add_hours(self, start: datetime, hours: float) -> datetime:
        """Advance `hours` of working time from `start` (negative hours go backwards)."""
        if hours < 0:
            return self.sub_hours(start, -hours)
        if hours <= _EPS:
            return start
        cur = self.next_working_time(start)
        remaining = hours
        guard = 0
        while True:
            for s, e in self.day_ranges(cur.date()):
                if cur >= e:
                    continue
                if cur < s:
                    cur = s
                avail = (e - cur).total_seconds() / 3600.0
                if remaining <= avail + _EPS:
                    return cur + timedelta(hours=remaining)
                remaining -= avail
                cur = e
            nd = self.next_work_day(cur.date())
            cur = datetime(nd.year, nd.month, nd.day)
            guard += 1
            if guard > 36600:
                raise ValueError("Duration too long")

    def sub_hours(self, end: datetime, hours: float) -> datetime:
        if hours < 0:
            return self.add_hours(end, -hours)
        if hours <= _EPS:
            return end
        cur = self.prev_working_time(end)
        d = cur.date()
        remaining = hours
        guard = 0
        while True:
            for s, e in reversed(self.day_ranges(d)):
                if cur <= s:
                    continue
                if cur > e:
                    cur = e
                avail = (cur - s).total_seconds() / 3600.0
                if remaining <= avail + _EPS:
                    return cur - timedelta(hours=remaining)
                remaining -= avail
                cur = s
            d = self.prev_work_day(d)
            cur = datetime(d.year, d.month, d.day) + timedelta(days=1)
            guard += 1
            if guard > 36600:
                raise ValueError("Duration too long")

    def hours_between(self, a: datetime, b: datetime) -> float:
        """Working hours in [a, b]."""
        if b <= a:
            return 0.0
        total = 0.0
        d = a.date()
        while d <= b.date():
            for s, e in self.day_ranges(d):
                lo, hi = max(s, a), min(e, b)
                if hi > lo:
                    total += (hi - lo).total_seconds() / 3600.0
            d += timedelta(days=1)
        return total

    def days_between(self, a: datetime, b: datetime) -> float:
        return round(self.hours_between(a, b) / self.hours_per_day, 4)

    def add_days(self, start: datetime, days: float) -> datetime:
        return self.add_hours(start, days * self.hours_per_day)

    def work_days_in(self, a: date, b: date) -> List[date]:
        out = []
        d = a
        while d <= b:
            if self.is_work_day(d):
                out.append(d)
            d += timedelta(days=1)
        return out
