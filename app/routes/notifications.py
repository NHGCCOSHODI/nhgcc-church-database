from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import db
from app.models import NotificationLog, Member
from app.services.notification_logic import (
    get_birthdays_in_range,
    get_birthdays_exactly_7_days,
    get_consecutive_absentees
)
from app.services.email_service import (
    generate_birthday_email_html,
    generate_absentee_email_html,
    send_raw_email,
    get_smtp_config
)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/')
def index():
    today = date.today()
    upcoming_birthdays = get_birthdays_in_range(days_ahead=7, reference_date=today)
    absentees_data = get_consecutive_absentees(min_weeks=2, max_weeks=6)
    logs = (
        NotificationLog.query.order_by(NotificationLog.created_at.desc())
        .limit(20)
        .all()
    )
    smtp_cfg = get_smtp_config()

    return render_template(
        'notifications/index.html',
        upcoming_birthdays=upcoming_birthdays,
        absentees_summary=absentees_data['summary'],
        absentees=absentees_data['absentees'][:10],
        logs=logs,
        smtp_cfg=smtp_cfg
    )


@notifications_bp.route('/send-birthday-digest', methods=['POST'])
def send_birthday_digest():
    """Manually dispatches the 7-day birthday email notification to the church email."""
    days_ahead = request.form.get('days_ahead', 7, type=int)
    celebrants = get_birthdays_in_range(days_ahead=days_ahead)

    if not celebrants:
        flash(f"No members have birthdays coming up within {days_ahead} days.", 'info')
        return redirect(url_for('notifications.index'))

    subject = f"🎂 NHGCC Birthday Alert: {len(celebrants)} Celebrant(s) Coming Up Within {days_ahead} Days"
    html_body = generate_birthday_email_html(celebrants, days_ahead=days_ahead)

    success, msg = send_raw_email(
        subject=subject,
        html_content=html_body,
        notification_type='BIRTHDAY_7_DAYS',
        record_count=len(celebrants)
    )

    if success:
        flash(f"Birthday notification processed successfully! {msg}", 'success')
    else:
        flash(f"Notification status: {msg}", 'warning')

    return redirect(url_for('notifications.index'))


@notifications_bp.route('/preview/<int:log_id>')
def preview_email(log_id):
    """Renders the HTML body of a logged email for inspection."""
    log = NotificationLog.query.get_or_404(log_id)
    return log.content_html
