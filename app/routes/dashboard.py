from datetime import date, timedelta
from flask import Blueprint, render_template, jsonify
from sqlalchemy import func
from app.database import db
from app.models import Member, Attendance, FollowUpLog
from app.services.notification_logic import (
    get_latest_sunday, get_upcoming_sunday, get_recent_sundays,
    get_birthdays_in_range, get_consecutive_absentees
)

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    today = date.today()
    latest_sunday = get_latest_sunday(today)
    upcoming_sunday = get_upcoming_sunday(today)

    total_members = Member.query.filter_by(is_active=True).count()
    total_males = Member.query.filter_by(is_active=True, gender='Male').count()
    total_females = Member.query.filter_by(is_active=True, gender='Female').count()

    latest_att_count = Attendance.query.filter_by(service_date=latest_sunday, status='Present').count()

    upcoming_birthdays = get_birthdays_in_range(days_ahead=7, reference_date=today)

    absentees_data = get_consecutive_absentees(min_weeks=2, max_weeks=6, reference_date=today)
    urgent_absentees = absentees_data['absentees'][:8]

    recent_sundays = get_recent_sundays(count=6, reference_date=today)
    recent_sundays.reverse()
    chart_labels = [s.strftime('%b %d') for s in recent_sundays]
    
    # Efficient bulk aggregation for recent Sunday attendances (1 query instead of 6)
    att_counts_map = dict(
        db.session.query(Attendance.service_date, func.count(Attendance.id))
        .filter(Attendance.service_date.in_(recent_sundays), Attendance.status == 'Present')
        .group_by(Attendance.service_date)
        .all()
    )
    chart_data = [att_counts_map.get(s, 0) for s in recent_sundays]

    dept_query = db.session.query(Member.department, func.count(Member.id)).filter(Member.is_active == True).group_by(Member.department).all()
    dept_labels = [d[0] if d[0] else 'General' for d in dept_query]
    dept_counts = [d[1] for d in dept_query]

    recent_members = Member.query.order_by(Member.id.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total_members=total_members,
        total_males=total_males,
        total_females=total_females,
        latest_sunday=latest_sunday,
        upcoming_sunday=upcoming_sunday,
        latest_att_count=latest_att_count,
        upcoming_birthdays=upcoming_birthdays,
        absentees_summary=absentees_data['summary'],
        urgent_absentees=urgent_absentees,
        chart_labels=chart_labels,
        chart_data=chart_data,
        dept_labels=dept_labels,
        dept_counts=dept_counts,
        recent_members=recent_members
    )
