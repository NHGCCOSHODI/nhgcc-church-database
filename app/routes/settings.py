import os
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from app.database import db
from app.models import SystemSetting, Member, Attendance
from app.services.email_service import send_raw_email, get_smtp_config
from app.services.pdf_importer import import_pdf_to_database

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/', methods=['GET', 'POST'])
def index():
    cfg = current_app.config

    if request.method == 'POST':
        SystemSetting.set_value('church_name', request.form.get('church_name', '').strip())
        SystemSetting.set_value('church_branch', request.form.get('church_branch', '').strip())
        SystemSetting.set_value('church_email', request.form.get('church_email', '').strip())
        SystemSetting.set_value('church_phone', request.form.get('church_phone', '').strip())
        SystemSetting.set_value('church_facebook', request.form.get('church_facebook', '').strip())

        SystemSetting.set_value('smtp_server', request.form.get('smtp_server', 'smtp.gmail.com').strip())
        SystemSetting.set_value('smtp_port', request.form.get('smtp_port', '587').strip())
        SystemSetting.set_value('smtp_use_tls', request.form.get('smtp_use_tls', 'True'))
        SystemSetting.set_value('smtp_username', request.form.get('smtp_username', '').strip())

        pwd = request.form.get('smtp_password', '').strip()
        if pwd:
            SystemSetting.set_value('smtp_password', pwd)

        SystemSetting.set_value('mail_sender', request.form.get('mail_sender', '').strip())

        flash('Settings have been successfully updated!', 'success')
        return redirect(url_for('settings.index'))

    smtp_cfg = get_smtp_config()
    db_type = 'SQLite (Local File)' if 'sqlite' in cfg['SQLALCHEMY_DATABASE_URI'] else 'Cloud Database (PostgreSQL)'

    return render_template('settings/index.html', smtp_cfg=smtp_cfg, db_type=db_type)


@settings_bp.route('/test-email', methods=['POST'])
def test_email():
    """Dispatches a quick test email to verify SMTP configuration."""
    recipient = request.form.get('test_email', '').strip()
    if not recipient:
        flash('Please specify a recipient email address.', 'danger')
        return redirect(url_for('settings.index'))

    subject = '🕊️ NHGCC Oshodi: Test Notification from Church Database'
    html = '''
    <div style="font-family: sans-serif; padding: 20px; background-color: #f8fafc; border-radius: 8px;">
        <h2 style="color: #0b192c;">NHGCC Oshodi Notification Test</h2>
        <p>This is a test notification confirming that email alerts from your NHGCC Church Management System are configured properly.</p>
        <p style="color: #10b981; font-weight: bold;">System status: Operational & Ready.</p>
    </div>
    '''

    success, msg = send_raw_email(
        subject=subject,
        html_content=html,
        recipient_email=recipient,
        notification_type='MANUAL_TEST'
    )

    if success:
        flash(f'Test email successfully dispatched: {msg}', 'success')
    else:
        flash(f'Test email notice: {msg}', 'warning')

    return redirect(url_for('settings.index'))


@settings_bp.route('/backup-db')
def backup_db():
    """Allows downloading a local backup copy of the SQLite database."""
    cfg = current_app.config
    db_uri = cfg['SQLALCHEMY_DATABASE_URI']

    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        if Path(db_path).exists():
            return send_file(
                db_path,
                as_attachment=True,
                download_name=f'nhgcc_church_backup_{Path(db_path).name}'
            )

    flash('Database backup is only supported for local SQLite storage.', 'warning')
    return redirect(url_for('settings.index'))


@settings_bp.route('/reimport-pdf', methods=['POST'])
def reimport_pdf():
    """Re-runs PDF ingestion to import or sync all 203 members."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    pdf_path = base_dir / 'NHGCC database .pdf'

    if not pdf_path.exists():
        flash('NHGCC database .pdf was not found in the project root.', 'danger')
        return redirect(url_for('settings.index'))

    res = import_pdf_to_database(str(pdf_path), force=True)
    flash(f"PDF sync completed: {res['total']} records processed ({res['added']} added, {res['updated']} updated).", 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/sync-cloud', methods=['GET', 'POST'])
def sync_cloud():
    """Manually triggers bidirectional sync between local SQLite and cloud Supabase."""
    from app.services.sync_service import sync_offline_sqlite_to_cloud
    ok, msg = sync_offline_sqlite_to_cloud(current_app)
    if ok:
        flash(f'Cloud Synchronization Complete: {msg}', 'success')
    else:
        flash(f'Sync Warning: {msg}', 'warning')
    return redirect(url_for('settings.index'))
