import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, datetime
from flask import current_app
from app.database import db
from app.models import SystemSetting, NotificationLog

def get_smtp_config():
    """Retrieves SMTP configuration from SystemSettings or environment/config."""
    cfg = {}
    cfg['server'] = SystemSetting.get_value('smtp_server') or current_app.config.get('SMTP_SERVER', 'smtp.gmail.com')
    port_val = SystemSetting.get_value('smtp_port') or current_app.config.get('SMTP_PORT', 587)
    cfg['port'] = int(port_val)
    use_tls_val = SystemSetting.get_value('smtp_use_tls') or str(current_app.config.get('SMTP_USE_TLS', True))
    cfg['use_tls'] = str(use_tls_val).lower() in ('true', '1', 'yes')
    cfg['username'] = SystemSetting.get_value('smtp_username') or current_app.config.get('SMTP_USERNAME', '')
    cfg['password'] = SystemSetting.get_value('smtp_password') or current_app.config.get('SMTP_PASSWORD', '')
    cfg['sender'] = SystemSetting.get_value('mail_sender') or current_app.config.get('MAIL_DEFAULT_SENDER', 'NHGCC Oshodi Secretariat <nhgccoshodi@gmail.com>')
    cfg['recipient'] = SystemSetting.get_value('church_email') or current_app.config.get('CHURCH_EMAIL', 'nhgccoshodi@gmail.com')
    cfg['church_name'] = SystemSetting.get_value('church_name') or current_app.config.get('CHURCH_NAME', 'National Holy Ghost Church of Christ')
    cfg['church_branch'] = SystemSetting.get_value('church_branch') or current_app.config.get('CHURCH_BRANCH', 'Oshodi Parish, Lagos')
    cfg['church_facebook'] = SystemSetting.get_value('church_facebook') or current_app.config.get('CHURCH_FACEBOOK', 'https://www.facebook.com/nhgccoshodii/')
    return cfg

def send_raw_email(subject, html_content, recipient_email=None, notification_type='GENERAL', record_count=0):
    """
    Sends an HTML email via SMTP, or logs as SIMULATED if SMTP credentials are not yet supplied.
    Returns: (success: bool, status_message: str)
    """
    config = get_smtp_config()
    recipient = recipient_email or config['recipient']
    is_live = bool(config['username'] and config['password'])

    if not is_live:
        log_entry = NotificationLog(
            notification_type=notification_type,
            recipient_email=recipient,
            subject=subject,
            content_html=html_content,
            status='SIMULATED',
            error_message='',
            record_count=record_count
        )
        db.session.add(log_entry)
        db.session.commit()
        return True, 'Simulation mode: Set SMTP credentials in Settings to dispatch live emails.'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = config['sender']
    msg['To'] = recipient

    part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part)

    try:
        if config['port'] == 465:
            server = smtplib.SMTP_SSL(config['server'], config['port'], timeout=20)
        else:
            server = smtplib.SMTP(config['server'], config['port'], timeout=20)
            if config['use_tls']:
                server.starttls()

        server.login(config['username'], config['password'])
        server.sendmail(config['sender'], [recipient], msg.as_string())
        server.quit()

        log_entry = NotificationLog(
            notification_type=notification_type,
            recipient_email=recipient,
            subject=subject,
            content_html=html_content,
            status='SENT',
            error_message='',
            record_count=record_count
        )
        db.session.add(log_entry)
        db.session.commit()
        return True, f'Email delivered to {recipient} successfully.'

    except Exception as e:
        error_str = str(e)
        log_entry = NotificationLog(
            notification_type=notification_type,
            recipient_email=recipient,
            subject=subject,
            content_html=html_content,
            status='FAILED',
            error_message=error_str,
            record_count=record_count
        )
        db.session.add(log_entry)
        db.session.commit()
        return False, f'Email dispatch failed: {error_str}'

def generate_birthday_email_html(celebrants, days_ahead=7):
    """Generates a modern, responsive HTML email for upcoming birthdays."""
    cfg = get_smtp_config()
    today_str = date.today().strftime('%A, %d %B %Y')

    rows_html = ''
    for item in celebrants:
        m = item['member']
        target_date = item['target_date']
        days = item['days_until']

        if days == 7:
            days_badge = f'<span style="background-color: #dbeafe; color: #1d4ed8; padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 12px;">Exactly 7 Days ({item["formatted_date"]})</span>'
        else:
            days_badge = f'<span style="background-color: #fef3c7; color: #b45309; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 12px;">In {days} days ({item["formatted_date"]})</span>'

        phone_html = f'<a href="tel:{m.phone}" style="color: #2563eb; text-decoration: none; font-weight: 500;">{m.phone}</a>' if m.phone else '—'
        wa_link = ''
        if m.phone:
            raw_phone = m.phone.replace(' ', '').replace('-', '')
            if raw_phone.startswith('0'):
                wa_link = f'https://wa.me/234{raw_phone[1:]}'
            elif raw_phone.startswith('+'):
                wa_link = f'https://wa.me/{raw_phone.lstrip("+")}'
            else:
                wa_link = f'https://wa.me/{raw_phone}'
        wa_btn = f'&nbsp;<a href="{wa_link}" style="background-color: #25D366; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: bold;">WhatsApp</a>' if wa_link else ''

        rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 14px 16px; font-weight: 600; color: #1e293b;">
                {m.display_title_name}
                <div style="font-size: 12px; color: #64748b; font-weight: normal;">{m.department or 'Member'}</div>
            </td>
            <td style="padding: 14px 16px; color: #334155;">{phone_html}{wa_btn}</td>
            <td style="padding: 14px 16px; color: #475569;">{m.email or '—'}</td>
            <td style="padding: 14px 16px; text-align: right;">{days_badge}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .card {{ max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); overflow: hidden; border: 1px solid #e2e8f0; }}
            .header {{ background: linear-gradient(135deg, #0b192c 0%, #1e3e62 100%); color: #ffffff; padding: 28px 32px; text-align: center; }}
            .badge {{ display: inline-block; background: #f59e0b; color: #0b192c; font-size: 11px; font-weight: 800; text-transform: uppercase; padding: 4px 12px; border-radius: 9999px; letter-spacing: 0.5px; margin-bottom: 10px; }}
            .title {{ font-size: 24px; font-weight: 700; margin: 0 0 6px 0; }}
            .subtitle {{ font-size: 14px; opacity: 0.85; margin: 0; }}
            .body {{ padding: 28px 32px; }}
            .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
            .table th {{ background-color: #f1f5f9; color: #475569; font-weight: 600; text-align: left; padding: 12px 16px; border-bottom: 2px solid #cbd5e1; }}
            .footer {{ background-color: #f8fafc; padding: 20px 32px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <span class="badge">NHGCC Pastoral Care Alert</span>
                <h1 class="title">🎂 Upcoming Birthday Notifications</h1>
                <p class="subtitle">{cfg['church_name']} • {cfg['church_branch']}</p>
            </div>
            <div class="body">
                <p style="font-size: 15px; line-height: 1.6; color: #334155;">
                    Calvary greetings in Jesus' name. This is your automated notice of church members whose birthdays are coming up within the next <strong>7 days</strong>.
                </p>
                <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 6px; margin: 16px 0;">
                    <strong style="color: #1e40af;">Total Celebrants: {len(celebrants)} members</strong>
                    <div style="font-size: 13px; color: #3b82f6; margin-top: 4px;">Please plan church felicitations, prayers, and celebratory calls in advance.</div>
                </div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Member Name</th>
                            <th>Phone Contact</th>
                            <th>Email</th>
                            <th style="text-align: right;">Birthday Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
                    Report generated on <strong>{today_str}</strong> by the NHGCC Church Management System.
                </p>
            </div>
            <div class="footer">
                &copy; 2026 {cfg['church_name']} ({cfg['church_branch']}). All rights reserved.<br>
                For assistance, contact the church secretariat at {cfg['recipient']}.
            </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_absentee_email_html(absentees_data):
    """Generates a modern, responsive HTML email for members missing 2-3 Sundays consecutively."""
    cfg = get_smtp_config()
    today_str = date.today().strftime('%A, %d %B %Y')
    absentees = absentees_data.get('absentees', [])
    summary = absentees_data.get('summary', {})

    rows_html = ''
    for item in absentees:
        m = item['member']
        streak = item['streak']
        last_date = item['last_attended_date'].strftime('%d %b %Y') if item.get('last_attended_date') else 'No recent record'

        if streak >= 3:
            badge = f'<span style="background-color: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 9999px; font-weight: 700; font-size: 12px;">Missed {streak} Sundays (Urgent)</span>'
        else:
            badge = f'<span style="background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 9999px; font-weight: 600; font-size: 12px;">Missed {streak} Sundays</span>'

        phone_html = f'<a href="tel:{m.phone}" style="color: #2563eb; text-decoration: none; font-weight: 600;">{m.phone}</a>' if m.phone else '—'
        wa_link = ''
        if m.phone:
            raw_phone = m.phone.replace(' ', '').replace('-', '')
            if raw_phone.startswith('0'):
                wa_link = f'https://wa.me/234{raw_phone[1:]}'
            elif raw_phone.startswith('+'):
                wa_link = f'https://wa.me/{raw_phone.lstrip("+")}'
            else:
                wa_link = f'https://wa.me/{raw_phone}'
        wa_btn = f'&nbsp;<a href="{wa_link}" style="background-color: #25D366; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: bold;">WhatsApp</a>' if wa_link else ''

        address_html = m.address or 'Address not registered'

        rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 14px 16px; vertical-align: top;">
                <div style="font-weight: 700; color: #0f172a; font-size: 14px;">{m.display_title_name}</div>
                <div style="font-size: 12px; color: #64748b;">Dept: {m.department or 'Congregation'}</div>
            </td>
            <td style="padding: 14px 16px; vertical-align: top;">
                <div>{phone_html}{wa_btn}</div>
                <div style="font-size: 11px; color: #475569; margin-top: 4px;">{m.email or '—'}</div>
            </td>
            <td style="padding: 14px 16px; vertical-align: top; font-size: 13px; color: #475569;">
                {address_html}
            </td>
            <td style="padding: 14px 16px; vertical-align: top; font-size: 13px; color: #64748b;">
                {last_date}
            </td>
            <td style="padding: 14px 16px; vertical-align: top; text-align: right;">
                {badge}
            </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .card {{ max-width: 780px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); overflow: hidden; border: 1px solid #e2e8f0; }}
            .header {{ background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%); color: #ffffff; padding: 28px 32px; text-align: center; }}
            .badge {{ display: inline-block; background: #fef08a; color: #854d0e; font-size: 11px; font-weight: 800; text-transform: uppercase; padding: 4px 12px; border-radius: 9999px; letter-spacing: 0.5px; margin-bottom: 10px; }}
            .title {{ font-size: 24px; font-weight: 700; margin: 0 0 6px 0; }}
            .subtitle {{ font-size: 14px; opacity: 0.85; margin: 0; }}
            .body {{ padding: 28px 32px; }}
            .summary-box {{ display: flex; background-color: #fff1f2; border: 1px solid #fecdd3; border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
            .table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
            .table th {{ background-color: #f1f5f9; color: #334155; font-weight: 600; text-align: left; padding: 12px 16px; border-bottom: 2px solid #cbd5e1; }}
            .footer {{ background-color: #f8fafc; padding: 20px 32px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <span class="badge">NHGCC Retention & Care Alert</span>
                <h1 class="title">🕊️ Pastoral Care: Consecutive Absentees Report</h1>
                <p class="subtitle">{cfg['church_name']} • {cfg['church_branch']}</p>
            </div>
            <div class="body">
                <p style="font-size: 15px; line-height: 1.6; color: #334155;">
                    Calvary greetings. This automated retention report identifies church members who have missed church services for <strong>2 or 3+ consecutive Sundays</strong>.
                </p>
                <div style="background-color: #fff7ed; border-left: 4px solid #f97316; padding: 14px 18px; border-radius: 6px; margin: 16px 0;">
                    <div style="font-weight: 700; color: #9a3412; font-size: 15px;">Follow-up Summary:</div>
                    <div style="font-size: 13px; color: #7c2d12; margin-top: 4px;">
                        • Total Members Requiring Follow-Up: <strong>{summary.get('total_absentees', 0)}</strong><br>
                        • Missed 2 Consecutive Sundays: <strong>{summary.get('streak_2', 0)}</strong> (Call & WhatsApp check-in recommended)<br>
                        • Missed 3+ Consecutive Sundays: <strong>{summary.get('streak_3_plus', 0)}</strong> (High priority for Pastoral visitation)
                    </div>
                </div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Member</th>
                            <th>Contact Info</th>
                            <th>Residential Address</th>
                            <th>Last Attended</th>
                            <th style="text-align: right;">Absence Level</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
                    Generated on <strong>{today_str}</strong>. You can record follow-up call notes directly on the NHGCC Church Management Dashboard.
                </p>
            </div>
            <div class="footer">
                &copy; 2026 {cfg['church_name']} ({cfg['church_branch']}). All rights reserved.<br>
                For inquiries, contact the church secretariat at {cfg['recipient']}.
            </div>
        </div>
    </body>
    </html>
    """
    return html
