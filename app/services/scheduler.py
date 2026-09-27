import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from app.database import db
from app.services.notification_logic import get_birthdays_in_range, get_consecutive_absentees
from app.services.email_service import send_raw_email, generate_birthday_email_html, generate_absentee_email_html

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(daemon=True)

def trigger_birthday_check(app):
    """Checks for members whose birthday is within 7 days and dispatches email alert."""
    with app.app_context():
        try:
            celebrants = get_birthdays_in_range(days_ahead=7)
            if celebrants:
                subject = f"🎂 NHGCC Birthday Alert: {len(celebrants)} Celebrant(s) Coming Up Within 7 Days"
                html_body = generate_birthday_email_html(celebrants, days_ahead=7)
                success, msg = send_raw_email(
                    subject=subject,
                    html_content=html_body,
                    notification_type='BIRTHDAY_7_DAYS',
                    record_count=len(celebrants)
                )
                logger.info(f"Birthday notification processed: {msg}")
            else:
                logger.info("Birthday check ran: No celebrants in the next 7 days.")
        except Exception as e:
            logger.error(f"Error in automated birthday check: {e}")

def trigger_absentee_check(app):
    """Checks for members who missed 2-3 consecutive Sundays and dispatches alert."""
    with app.app_context():
        try:
            absentees_data = get_consecutive_absentees(min_weeks=2, max_weeks=6)
            absentees = absentees_data.get('absentees', [])
            if absentees:
                subject = f"🕊️ NHGCC Retention Alert: {len(absentees)} Member(s) Missed 2-3+ Sundays"
                html_body = generate_absentee_email_html(absentees_data)
                success, msg = send_raw_email(
                    subject=subject,
                    html_content=html_body,
                    notification_type='ABSENTEE_2_3_WEEKS',
                    record_count=len(absentees)
                )
                logger.info(f"Absentee notification processed: {msg}")
            else:
                logger.info("Absentee check ran: No consecutive absentees found.")
        except Exception as e:
            logger.error(f"Error in automated absentee check: {e}")

def trigger_cloud_sync(app):
    """Periodically syncs local offline database with cloud database."""
    try:
        from app.services.sync_service import sync_offline_sqlite_to_cloud
        sync_offline_sqlite_to_cloud(app)
    except Exception as e:
        logger.warning(f"Error in automated cloud sync job: {e}")

def init_scheduler(app):
    """Initializes APScheduler background jobs if not running in a serverless environment."""
    if os.environ.get('VERCEL') or app.config.get('FLASK_ENV') == 'testing':
        return

    try:
        if not scheduler.running:
            # Daily birthday check at 07:00 AM
            scheduler.add_job(
                func=trigger_birthday_check,
                args=[app],
                trigger='cron',
                hour=7,
                minute=0,
                id='daily_birthday_check',
                replace_existing=True
            )
            # Weekly absentee retention check on Tuesday morning at 08:00 AM
            scheduler.add_job(
                func=trigger_absentee_check,
                args=[app],
                trigger='cron',
                day_of_week='tue',
                hour=8,
                minute=0,
                id='weekly_absentee_check',
                replace_existing=True
            )
            # Periodic cloud sync every 5 minutes
            scheduler.add_job(
                func=trigger_cloud_sync,
                args=[app],
                trigger='interval',
                minutes=5,
                id='periodic_cloud_sync',
                replace_existing=True
            )
            scheduler.start()
            logger.info("NHGCC Background scheduler started successfully.")
    except Exception as e:
        logger.warning(f"Could not start scheduler: {e}")
