from datetime import date, datetime, timedelta
from sqlalchemy import func
from app.database import db
from app.models import Member, Attendance

def get_latest_sunday(reference_date=None):
    """Returns the most recent Sunday on or before reference_date."""
    if reference_date is None:
        reference_date = date.today()
    offset = (reference_date.weekday() + 1) % 7
    return reference_date - timedelta(days=offset)

def get_upcoming_sunday(reference_date=None):
    """Returns the next upcoming Sunday (or today if today is Sunday)."""
    if reference_date is None:
        reference_date = date.today()
    days_ahead = 6 - reference_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return reference_date + timedelta(days=days_ahead)

def get_recent_sundays(count=4, reference_date=None):
    """Returns a list of the last `count` Sundays descending from most recent."""
    latest = get_latest_sunday(reference_date)
    return [latest - timedelta(weeks=i) for i in range(count)]

def get_birthdays_in_range(days_ahead=7, reference_date=None):
    """
    Returns list of members with birthdays in the next `days_ahead` days.
    Also tags members whose birthday is EXACTLY `days_ahead` days away.
    """
    if reference_date is None:
        reference_date = date.today()

    all_members = Member.query.filter(
        Member.is_active == True,
        Member.birth_month.isnot(None),
        Member.birth_day.isnot(None)
    ).all()

    results = []
    target_exact_date = reference_date + timedelta(days=days_ahead)

    for m in all_members:
        try:
            bday_this_year = date(reference_date.year, m.birth_month, m.birth_day)
        except ValueError:
            # Leap year handling for Feb 29
            bday_this_year = date(reference_date.year, m.birth_month, 28)

        if bday_this_year < reference_date:
            try:
                bday_next = date(reference_date.year + 1, m.birth_month, m.birth_day)
            except ValueError:
                bday_next = date(reference_date.year + 1, m.birth_month, 28)
            diff = (bday_next - reference_date).days
            target_date = bday_next
        else:
            diff = (bday_this_year - reference_date).days
            target_date = bday_this_year

        if 0 <= diff <= days_ahead:
            is_exactly_7_days = (diff == days_ahead)
            results.append({
                'member': m,
                'days_until': diff,
                'target_date': target_date,
                'formatted_date': target_date.strftime('%A, %B %d'),
                'is_exactly_7_days': is_exactly_7_days
            })

    results.sort(key=lambda x: x['days_until'])
    return results

def get_birthdays_exactly_7_days(reference_date=None):
    """Returns members whose birthday is exactly 7 days from reference_date."""
    all_upcoming = get_birthdays_in_range(days_ahead=7, reference_date=reference_date)
    return [item for item in all_upcoming if item['is_exactly_7_days']]

def get_consecutive_absentees(min_weeks=2, max_weeks=6, reference_date=None):
    """
    Identifies active church members who have missed church for 2 or 3+ consecutive Sundays.
    Returns:
    {
        'summary': {'total_absentees': int, 'streak_2': int, 'streak_3_plus': int},
        'absentees': [
            {
                'member': Member,
                'streak': int, # consecutive missed Sundays
                'last_attended_date': date or None,
                'missed_sundays': [date, ...],
                'status_level': 'warning' (2 weeks) or 'danger' (3+ weeks)
            }
        ]
    }
    """
    sundays = get_recent_sundays(count=max_weeks, reference_date=reference_date)
    if not sundays:
        return {
            'summary': {'total_absentees': 0, 'streak_2': 0, 'streak_3_plus': 0},
            'absentees': []
        }

    active_members = Member.query.filter_by(is_active=True).all()
    if not active_members:
        return {
            'summary': {'total_absentees': 0, 'streak_2': 0, 'streak_3_plus': 0},
            'absentees': []
        }

    # Fetch all attendances for these sundays in ONE single bulk query
    recent_attendances = Attendance.query.filter(
        Attendance.service_date.in_(sundays),
        Attendance.status == 'Present'
    ).all()

    attended_dates_by_member = {}
    for a in recent_attendances:
        attended_dates_by_member.setdefault(a.member_id, set()).add(a.service_date)

    # Fetch max attended date for each member in ONE single aggregated query
    last_dates = dict(
        db.session.query(
            Attendance.member_id,
            func.max(Attendance.service_date)
        ).filter(
            Attendance.status == 'Present'
        ).group_by(Attendance.member_id).all()
    )

    absentees = []
    for member in active_members:
        attended_dates = attended_dates_by_member.get(member.id, set())

        streak = 0
        missed_dates = []
        for s in sundays:
            if s not in attended_dates:
                streak += 1
                missed_dates.append(s)
            else:
                break

        if streak >= min_weeks:
            last_attended = last_dates.get(member.id)
            absentees.append({
                'member': member,
                'streak': streak,
                'last_attended_date': last_attended,
                'missed_sundays': missed_dates,
                'status_level': 'danger' if streak >= 3 else 'warning'
            })

    absentees.sort(key=lambda x: x['streak'], reverse=True)

    streak_2 = sum(1 for a in absentees if a['streak'] == 2)
    streak_3_plus = sum(1 for a in absentees if a['streak'] >= 3)

    return {
        'summary': {
            'total_absentees': len(absentees),
            'streak_2': streak_2,
            'streak_3_plus': streak_3_plus
        },
        'absentees': absentees
    }
