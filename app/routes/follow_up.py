from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.database import db
from app.models import Member, FollowUpLog
from app.services.notification_logic import get_consecutive_absentees
from app.services.email_service import generate_absentee_email_html, send_raw_email

follow_up_bp = Blueprint('follow_up', __name__, url_prefix='/follow-up')


@follow_up_bp.route('/')
def index():
    streak_filter = request.args.get('streak', 'all')
    absentees_data = get_consecutive_absentees(min_weeks=2, max_weeks=6)
    all_absentees = absentees_data.get('absentees', [])

    if streak_filter == '2':
        filtered = [a for a in all_absentees if a['streak'] == 2]
    elif streak_filter == '3':
        filtered = [a for a in all_absentees if a['streak'] >= 3]
    else:
        filtered = all_absentees

    recent_logs = (
        FollowUpLog.query.order_by(FollowUpLog.contact_date.desc())
        .limit(15)
        .all()
    )

    return render_template(
        'follow_up/index.html',
        absentees=filtered,
        summary=absentees_data.get('summary', {}),
        streak_filter=streak_filter,
        recent_logs=recent_logs
    )


@follow_up_bp.route('/log', methods=['POST'])
def log_follow_up():
    """Records a pastoral contact attempt for an absent member."""
    member_id = request.form.get('member_id', type=int)
    absence_streak = request.form.get('absence_streak', 2, type=int)
    contact_type = request.form.get('contact_type', 'Phone Call')
    outcome = request.form.get('outcome', 'Reached - Returning')
    notes = request.form.get('notes', '').strip()
    contacted_by = request.form.get('contacted_by', 'Pastoral Care Team').strip()

    member = Member.query.get_or_404(member_id)

    log = FollowUpLog(
        member_id=member.id,
        absence_streak=absence_streak,
        contact_type=contact_type,
        outcome=outcome,
        notes=notes,
        contacted_by=contacted_by,
        contact_date=datetime.now()
    )
    db.session.add(log)
    db.session.commit()

    flash(f"Follow-up note successfully recorded for {member.full_name}!", 'success')
    return redirect(url_for('follow_up.index'))


@follow_up_bp.route('/send-report', methods=['POST'])
def send_email_report():
    """Manually triggers the Absentee Retention email report to church email."""
    absentees_data = get_consecutive_absentees(min_weeks=2, max_weeks=6)
    absentees = absentees_data.get('absentees', [])

    if not absentees:
        flash('No members currently match the 2-3 consecutive weeks absence criteria.', 'info')
        return redirect(url_for('follow_up.index'))

    subject = f"🕊️ NHGCC Retention Alert: {len(absentees)} Member(s) Missed 2-3+ Sundays"
    html_body = generate_absentee_email_html(absentees_data)

    success, msg = send_raw_email(
        subject=subject,
        html_content=html_body,
        notification_type='ABSENTEE_2_3_WEEKS',
        record_count=len(absentees)
    )

    if success:
        flash(f"Absentee alert email processed! {msg}", 'success')
    else:
        flash(f"Notice: {msg}", 'warning')

    return redirect(url_for('follow_up.index'))
