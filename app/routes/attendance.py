import io
from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from sqlalchemy import or_, func
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from app.database import db
from app.models import Member, Attendance
from app.services.notification_logic import get_latest_sunday, get_upcoming_sunday

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance_bp.route('/checkin')
def checkin():
    today = date.today()
    if today.weekday() == 6:
        default_sunday = get_latest_sunday(today)
    else:
        default_sunday = get_upcoming_sunday(today)

    date_str = request.args.get('date', default_sunday.strftime('%Y-%m-%d'))
    service_type = request.args.get('service_type', 'Sunday Service')

    try:
        service_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        service_date = default_sunday

    members = Member.query.filter_by(is_active=True).order_by(Member.full_name).all()
    attendances = Attendance.query.filter_by(service_date=service_date, service_type=service_type).all()

    attended_member_ids = {a.member_id: a for a in attendances if a.status == 'Present'}
    total_active = len(members)
    total_present = len(attended_member_ids)
    first_timers_present = sum(1 for a in attended_member_ids.values() if a.member and a.member.status == 'First-Timer')

    return render_template(
        'attendance/checkin.html',
        service_date=service_date,
        service_date_str=service_date.strftime('%Y-%m-%d'),
        service_type=service_type,
        members=members,
        attended_member_ids=attended_member_ids,
        total_active=total_active,
        total_present=total_present,
        first_timers_present=first_timers_present
    )


@attendance_bp.route('/api/search')
def api_search():
    """Live search API for entrance check-in desk."""
    query = request.args.get('q', '').strip()
    date_str = request.args.get('date')
    service_type = request.args.get('service_type', 'Sunday Service')

    try:
        service_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        service_date = get_latest_sunday()

    members_query = Member.query.filter(Member.is_active == True)
    if query:
        pattern = f"%{query}%"
        members_query = members_query.filter(
            or_(
                Member.full_name.ilike(pattern),
                Member.phone.ilike(pattern),
                Member.member_code.ilike(pattern),
                Member.department.ilike(pattern)
            )
        )

    members = members_query.order_by(Member.full_name).limit(50).all()
    member_ids = [m.id for m in members]

    attendances = Attendance.query.filter(
        Attendance.member_id.in_(member_ids),
        Attendance.service_date == service_date,
        Attendance.service_type == service_type
    ).all()

    present_dict = {
        a.member_id: a.check_in_time.strftime('%I:%M %p')
        for a in attendances if a.status == 'Present' and a.check_in_time
    }

    results = []
    for m in members:
        is_present = m.id in present_dict
        results.append({
            'id': m.id,
            'member_code': m.member_code or '',
            'full_name': m.display_title_name,
            'phone': m.phone or '',
            'email': m.email or '',
            'department': m.department or 'Congregation',
            'status': m.status or 'Active',
            'is_present': is_present,
            'check_in_time': present_dict.get(m.id, '')
        })

    return jsonify({
        'success': True,
        'count': len(results),
        'members': results
    })


@attendance_bp.route('/api/toggle', methods=['POST'])
def api_toggle():
    """Toggles a member's check-in status for a given service date."""
    data = request.get_json() or {}
    member_id = data.get('member_id')
    date_str = data.get('service_date')
    service_type = data.get('service_type', 'Sunday Service')

    if not member_id or not date_str:
        return jsonify({'success': False, 'message': 'Missing member ID or date'}), 400

    try:
        service_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400

    member = Member.query.get(member_id)
    if not member:
        return jsonify({'success': False, 'message': 'Member not found'}), 404

    record = Attendance.query.filter_by(
        member_id=member.id,
        service_date=service_date,
        service_type=service_type
    ).first()

    if record:
        db.session.delete(record)
        db.session.commit()
        is_present = False
        check_time = ''
        action_msg = f"Marked {member.full_name} as ABSENT"
    else:
        record = Attendance(
            member_id=member.id,
            service_date=service_date,
            service_type=service_type,
            status='Present',
            check_in_time=datetime.now(),
            marked_by='Entrance Desk'
        )
        db.session.add(record)
        db.session.commit()
        is_present = True
        check_time = record.check_in_time.strftime('%I:%M %p')
        action_msg = f"Checked in {member.full_name} successfully!"

    total_present = Attendance.query.filter_by(
        service_date=service_date,
        service_type=service_type,
        status='Present'
    ).count()

    return jsonify({
        'success': True,
        'is_present': is_present,
        'check_in_time': check_time,
        'message': action_msg,
        'total_present': total_present
    })


@attendance_bp.route('/quick-add', methods=['POST'])
def quick_add():
    """
    Instantly registers a newcomer/unregistered attendee from the check-in modal
    and automatically marks them present for today's service!
    """
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    gender = request.form.get('gender', 'Not Specified')
    address = request.form.get('address', '').strip()
    status = request.form.get('status', 'First-Timer')
    department = request.form.get('department', 'Congregation')
    email = request.form.get('email', '').strip()
    service_date_str = request.form.get('service_date', date.today().strftime('%Y-%m-%d'))
    service_type = request.form.get('service_type', 'Sunday Service')

    if not full_name:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Full name is required'}), 400
        flash('Full name is required to register attendee.', 'danger')
        return redirect(url_for('attendance.checkin', date=service_date_str, service_type=service_type))

    last_member = Member.query.order_by(Member.id.desc()).first()
    next_num = (last_member.id + 1) if last_member else 1
    member_code = f"NHGCC-{next_num:04d}"

    parts = full_name.split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    new_member = Member(
        member_code=member_code,
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        gender=gender,
        address=address,
        status=status,
        department=department,
        date_joined=date.today(),
        is_active=True
    )
    db.session.add(new_member)
    db.session.flush()

    try:
        service_date = datetime.strptime(service_date_str, '%Y-%m-%d').date()
    except ValueError:
        service_date = date.today()

    att = Attendance(
        member_id=new_member.id,
        service_date=service_date,
        service_type=service_type,
        status='Present',
        check_in_time=datetime.now(),
        marked_by='Quick Entrance Registration'
    )
    db.session.add(att)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f"Successfully registered and checked in {new_member.full_name}!",
            'member': new_member.to_dict()
        })

    flash(f"New member '{new_member.full_name}' successfully added and marked present for today's service!", 'success')
    return redirect(url_for('attendance.checkin', date=service_date_str, service_type=service_type))


@attendance_bp.route('/history')
def history():
    """Displays chronological history of past Sunday attendances."""
    import traceback
    try:
        records = (
            db.session.query(
                Attendance.service_date,
                Attendance.service_type,
                func.count(Attendance.id).label('total_present')
            )
            .filter(Attendance.status == 'Present')
            .group_by(Attendance.service_date, Attendance.service_type)
            .order_by(Attendance.service_date.desc())
            .all()
        )
    except Exception as e:
        print(f"[NHGCC Error] Attendance history query error: {e}\n{traceback.format_exc()}")
        records = []

    formatted_records = []
    for rec in records:
        try:
            s_date = rec[0] if isinstance(rec, (tuple, list)) else getattr(rec, 'service_date', None)
            s_type = rec[1] if isinstance(rec, (tuple, list)) else getattr(rec, 'service_type', 'Sunday Service')
            count = rec[2] if isinstance(rec, (tuple, list)) else getattr(rec, 'total_present', 0)

            if isinstance(s_date, str):
                try:
                    s_date = datetime.strptime(s_date, '%Y-%m-%d').date()
                except Exception:
                    pass

            date_formatted = s_date.strftime('%d %B %Y') if hasattr(s_date, 'strftime') else str(s_date)
            date_iso = s_date.strftime('%Y-%m-%d') if hasattr(s_date, 'strftime') else str(s_date)
            day_name = s_date.strftime('%A') if hasattr(s_date, 'strftime') else 'Sunday'

            formatted_records.append({
                'service_date': s_date,
                'service_date_formatted': date_formatted,
                'service_date_iso': date_iso,
                'day_name': day_name,
                'service_type': s_type or 'Sunday Service',
                'total_present': int(count) if count else 0
            })
        except Exception as row_err:
            print(f"[NHGCC Warning] Error formatting row: {row_err}")

    return render_template('attendance/history.html', history_records=formatted_records)


@attendance_bp.route('/export')
def export_excel():
    """Exports a clean Excel sheet of attendance for a given Sunday."""
    date_str = request.args.get('date')
    service_type = request.args.get('service_type', 'Sunday Service')

    try:
        service_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        service_date = get_latest_sunday()

    attendances = (
        Attendance.query.filter_by(
            service_date=service_date,
            service_type=service_type,
            status='Present'
        )
        .join(Member)
        .order_by(Member.full_name)
        .all()
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Attendance {service_date.strftime('%d-%b-%Y')}"

    title_font = Font(name='Segoe UI', size=15, bold=True, color='1E3E62')
    ws.append(['NHGCC OSHODI - ATTENDANCE REGISTER'])
    ws.append([f"Service: {service_type} | Date: {service_date.strftime('%A, %d %B %Y')} | Total Present: {len(attendances)}"])
    ws.append([])

    ws['A1'].font = title_font
    ws['A2'].font = Font(name='Segoe UI', size=11, italic=True)

    headers = ['S/N', 'Member Code', 'Full Name', 'Gender', 'Phone Number', 'Email', 'Department', 'Status', 'Check-in Time']
    ws.append(headers)

    header_fill = PatternFill(start_color='0B192C', end_color='0B192C', fill_type='solid')
    header_font = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=4, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center' if col_idx in (1, 2, 4, 8, 9) else 'left')

    for idx, a in enumerate(attendances, 1):
        m = a.member
        ws.append([
            idx,
            m.member_code or '',
            m.display_title_name,
            m.gender,
            m.phone,
            m.email,
            m.department,
            m.status,
            a.check_in_time.strftime('%I:%M %p') if a.check_in_time else 'Present'
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"NHGCC_Attendance_{service_date.strftime('%Y%m%d')}_{service_type.replace(' ', '_')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
