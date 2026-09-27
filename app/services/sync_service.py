import os
import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from flask import current_app
from sqlalchemy import text
from app.database import db
from app.config import DATA_DIR, BASE_DIR

logger = logging.getLogger(__name__)

def get_local_sqlite_path():
    """Finds the local SQLite database file used for offline storage."""
    candidates = [
        DATA_DIR / 'nhgcc_church.db',
        BASE_DIR / 'nhgcc_church.db',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'NHGCC_Church_Database' / 'nhgcc_church.db'
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return DATA_DIR / 'nhgcc_church.db'

def sync_offline_sqlite_to_cloud(app=None):
    """
    Scans the local offline SQLite database and synchronizes any offline-recorded
    members or attendances into the Supabase cloud database.
    Also updates the local SQLite database to mirror the cloud database.
    """
    ctx = app.app_context() if app else current_app.app_context()
    with ctx:
        db_uri = str(db.engine.url)
        # Only run cloud sync if currently connected to a PostgreSQL cloud database
        if 'sqlite' in db_uri:
            logger.info("[NHGCC Sync] App is running in offline SQLite mode; skipping cloud push.")
            return False, "Running offline"

        sqlite_path = get_local_sqlite_path()
        if not sqlite_path.exists():
            logger.info("[NHGCC Sync] No local SQLite database found to sync.")
            return True, "No local database found"

        logger.info(f"[NHGCC Sync] Checking offline SQLite database at {sqlite_path}...")
        try:
            conn_sq = sqlite3.connect(sqlite_path)
            conn_sq.row_factory = sqlite3.Row
            cur_sq = conn_sq.cursor()

            # 1. Sync Members from SQLite to Cloud
            cur_sq.execute("SELECT * FROM members ORDER BY id;")
            local_members = cur_sq.fetchall()

            from app.models import Member, Attendance

            cloud_members = {m.id: m for m in Member.query.all()}
            new_members_count = 0

            for m in local_members:
                m_id = m['id']
                if m_id not in cloud_members:
                    new_m = Member(
                        id=m_id,
                        member_code=m['member_code'],
                        full_name=m['full_name'],
                        first_name=m['first_name'],
                        last_name=m['last_name'],
                        title=m['title'],
                        phone=m['phone'],
                        email=m['email'],
                        address=m['address'],
                        gender=m['gender'],
                        date_of_birth=m['date_of_birth'],
                        birth_day=m['birth_day'],
                        birth_month=m['birth_month'],
                        department=m['department'],
                        status=m['status'],
                        notes=m['notes'],
                        is_active=bool(m['is_active'])
                    )
                    db.session.add(new_m)
                    new_members_count += 1

            if new_members_count > 0:
                db.session.commit()
                # Update PostgreSQL sequence
                try:
                    db.session.execute(text("SELECT setval('members_id_seq', (SELECT COALESCE(MAX(id), 1) FROM members));"))
                    db.session.commit()
                except Exception:
                    pass
                logger.info(f"[NHGCC Sync] Synced {new_members_count} new offline member(s) to cloud.")

            # 2. Sync Attendance from SQLite to Cloud
            cur_sq.execute("SELECT * FROM attendance ORDER BY service_date, id;")
            local_attendances = cur_sq.fetchall()

            existing_cloud_att = {
                (a.member_id, str(a.service_date), a.service_type): a 
                for a in Attendance.query.all()
            }
            new_att_count = 0

            for a in local_attendances:
                a_dict = dict(a)
                s_type = a_dict.get('service_type') or 'Sunday Service'
                key = (a_dict['member_id'], str(a_dict['service_date']), s_type)
                if key not in existing_cloud_att:
                    # Verify member exists in cloud
                    m_exists = Member.query.get(a_dict['member_id'])
                    if m_exists:
                        from datetime import datetime as dt
                        s_date = a_dict['service_date']
                        if isinstance(s_date, str):
                            s_date = dt.strptime(s_date, '%Y-%m-%d').date()

                        new_att = Attendance(
                            member_id=a_dict['member_id'],
                            service_date=s_date,
                            service_type=s_type,
                            status=a_dict.get('status') or 'Present',
                            marked_by=a_dict.get('marked_by') or 'Entrance Desk',
                            notes=a_dict.get('notes')
                        )
                        db.session.add(new_att)
                        new_att_count += 1
                        existing_cloud_att[key] = new_att

            if new_att_count > 0:
                db.session.commit()
                try:
                    db.session.execute(text("SELECT setval('attendance_id_seq', (SELECT COALESCE(MAX(id), 1) FROM attendance));"))
                    db.session.commit()
                except Exception:
                    pass
                logger.info(f"[NHGCC Sync] Synced {new_att_count} new offline attendance record(s) to cloud.")

            # 3. Two-way: Mirror cloud database back into local SQLite for offline resilience
            try:
                mirror_cloud_to_local_sqlite(conn_sq)
            except Exception as mirror_err:
                logger.warning(f"[NHGCC Sync] Local cache mirror notice: {mirror_err}")

            conn_sq.close()
            msg = f"Synced {new_members_count} members, {new_att_count} attendances."
            return True, msg

        except Exception as e:
            logger.error(f"[NHGCC Sync] Error during offline-to-cloud synchronization: {e}")
            db.session.rollback()
            return False, str(e)


def mirror_cloud_to_local_sqlite(conn_sq):
    """Refreshes the local SQLite database so offline computers always have a fresh backup of the cloud."""
    from app.models import Member, Attendance
    cur = conn_sq.cursor()
    
    # Mirror all members
    for m in Member.query.all():
        cur.execute("""
            INSERT INTO members (id, member_code, full_name, first_name, last_name, title, phone, email, address, gender, date_of_birth, birth_day, birth_month, department, status, date_joined, notes, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                member_code=excluded.member_code,
                full_name=excluded.full_name,
                phone=excluded.phone,
                email=excluded.email,
                department=excluded.department,
                status=excluded.status,
                is_active=excluded.is_active;
        """, (
            m.id, m.member_code, m.full_name, m.first_name, m.last_name, m.title,
            m.phone, m.email, m.address, m.gender,
            str(m.date_of_birth) if m.date_of_birth else None,
            m.birth_day, m.birth_month, m.department, m.status,
            str(m.date_joined) if m.date_joined else None,
            m.notes, 1 if m.is_active else 0,
            str(m.created_at) if m.created_at else None,
            str(m.updated_at) if m.updated_at else None
        ))
    
    # Mirror all attendances
    for a in Attendance.query.all():
        cur.execute("""
            INSERT INTO attendance (id, member_id, service_date, service_type, status, check_in_time, marked_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(member_id, service_date, service_type) DO UPDATE SET
                status=excluded.status,
                marked_by=excluded.marked_by;
        """, (
            a.id, a.member_id, str(a.service_date), a.service_type, a.status,
            str(a.check_in_time) if a.check_in_time else None,
            a.marked_by, a.notes
        ))
        
    conn_sq.commit()
