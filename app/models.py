from datetime import datetime, date
from app.database import db

class Member(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    member_code = db.Column(db.String(30), unique=True, index=True)
    full_name = db.Column(db.String(150), nullable=False, index=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    title = db.Column(db.String(30), default='Member')
    phone = db.Column(db.String(50), index=True)
    email = db.Column(db.String(120), index=True)
    address = db.Column(db.Text)
    gender = db.Column(db.String(50), default='Not Specified')

    date_of_birth = db.Column(db.Date, nullable=True)
    birth_day = db.Column(db.Integer, nullable=True, index=True)
    birth_month = db.Column(db.Integer, nullable=True, index=True)

    department = db.Column(db.String(80), default='Congregation')
    status = db.Column(db.String(30), default='Active')
    date_joined = db.Column(db.Date, default=date.today)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attendances = db.relationship('Attendance', backref='member', cascade='all, delete-orphan', lazy='dynamic')
    follow_up_logs = db.relationship('FollowUpLog', backref='member', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'member_code': self.member_code,
            'full_name': self.full_name,
            'title': self.title,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone or '',
            'email': self.email or '',
            'address': self.address or '',
            'gender': self.gender or 'Not Specified',
            'date_of_birth': self.date_of_birth.strftime('%Y-%m-%d') if self.date_of_birth else '',
            'birth_day': self.birth_day,
            'birth_month': self.birth_month,
            'department': self.department or 'Congregation',
            'status': self.status or 'Active',
            'date_joined': self.date_joined.strftime('%Y-%m-%d') if self.date_joined else '',
            'notes': self.notes or ''
        }

    @property
    def display_title_name(self):
        if self.title and self.title != 'Member':
            if not self.full_name.lower().startswith(self.title.lower()):
                return f"{self.title} {self.full_name}"
        return self.full_name

    @property
    def formatted_birthday(self):
        if self.birth_month and self.birth_day:
            from datetime import date
            try:
                fake_date = date(2000, self.birth_month, self.birth_day)
                return fake_date.strftime('%B %d')
            except Exception:
                return f"{self.birth_day}/{self.birth_month}"
        return 'Not Set'


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False, index=True)
    service_date = db.Column(db.Date, nullable=False, index=True)
    service_type = db.Column(db.String(60), default='Sunday Service')
    status = db.Column(db.String(20), default='Present')
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    marked_by = db.Column(db.String(80), default='Entrance Desk')
    notes = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('member_id', 'service_date', 'service_type', name='unique_member_service_checkin'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'member_name': self.member.full_name if self.member else 'Unknown',
            'service_date': self.service_date.strftime('%Y-%m-%d'),
            'service_type': self.service_type,
            'status': self.status,
            'check_in_time': self.check_in_time.strftime('%H:%M:%S') if self.check_in_time else '',
            'marked_by': self.marked_by
        }


class FollowUpLog(db.Model):
    __tablename__ = 'follow_up_logs'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False, index=True)
    absence_streak = db.Column(db.Integer, default=2)
    contact_date = db.Column(db.DateTime, default=datetime.utcnow)
    contact_type = db.Column(db.String(40), default='Phone Call')
    outcome = db.Column(db.String(60), default='Reached - Returning')
    notes = db.Column(db.Text, nullable=True)
    contacted_by = db.Column(db.String(100), default='Pastoral Care')

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'member_name': self.member.full_name if self.member else 'Unknown',
            'absence_streak': self.absence_streak,
            'contact_date': self.contact_date.strftime('%Y-%m-%d %H:%M'),
            'contact_type': self.contact_type,
            'outcome': self.outcome,
            'notes': self.notes or '',
            'contacted_by': self.contacted_by
        }


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.Text, default='')
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_value(cls, key, default=None):
        item = cls.query.filter_by(setting_key=key).first()
        if item and item.setting_value is not None:
            return item.setting_value
        return default

    @classmethod
    def set_value(cls, key, value, description=''):
        item = cls.query.filter_by(setting_key=key).first()
        if not item:
            item = cls(setting_key=key, setting_value=str(value), description=description)
            db.session.add(item)
        else:
            item.setting_value = str(value)
            if description:
                item.description = description
        db.session.commit()
        return item


class NotificationLog(db.Model):
    __tablename__ = 'notification_logs'

    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(50), nullable=False)
    recipient_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    content_html = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='SENT')
    error_message = db.Column(db.Text, nullable=True)
    record_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'status': self.status,
            'record_count': self.record_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'error_message': self.error_message or ''
        }
