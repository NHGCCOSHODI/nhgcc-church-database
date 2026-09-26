import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    DATA_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR

load_dotenv(DATA_DIR / '.env')
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nhgcc-oshodi-secure-key-2026-prod-desktop')

    # Central Supabase PostgreSQL cloud database URL (Transaction Mode on port 6543 for multi-client concurrency)
    DEFAULT_CLOUD_DB = 'postgresql+psycopg://postgres.xjvftjeaovleukhuhkpa:NHGCC_Church_Db_2026%21@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require'

    raw_db_url = os.environ.get('DATABASE_URL', DEFAULT_CLOUD_DB)
    if raw_db_url:
        if raw_db_url.startswith('postgres://'):
            raw_db_url = raw_db_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif raw_db_url.startswith('postgresql://') and not raw_db_url.startswith('postgresql+'):
            raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        # Ensure Transaction Mode port 6543 is used if connecting to Supabase pooler
        if 'pooler.supabase.com:5432' in raw_db_url:
            raw_db_url = raw_db_url.replace(':5432', ':6543')
        SQLALCHEMY_DATABASE_URI = raw_db_url
    elif os.environ.get('VERCEL') and sys.platform != 'win32':
        tmp_db = Path('/tmp/nhgcc_church.db')
        seed_db = BASE_DIR / 'nhgcc_church.db'
        if not tmp_db.exists() and seed_db.exists():
            try:
                import shutil
                shutil.copy2(seed_db, tmp_db)
            except Exception:
                pass
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{tmp_db.as_posix()}'
    else:
        local_db = BASE_DIR / 'nhgcc_church.db'
        if local_db.exists():
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{local_db.as_posix()}'
        else:
            db_path = DATA_DIR / 'nhgcc_church.db'
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path.as_posix()}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Supabase cloud PostgreSQL connection resilience options:
    # NullPool ensures connections are immediately returned to Supabase's transaction pooler,
    # preventing idle connection accumulation and EMAXCONNSESSION errors across multiple church PCs.
    from sqlalchemy.pool import NullPool
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': NullPool,
        'connect_args': {
            'connect_timeout': 10,
        }
    }

    CHURCH_NAME = os.environ.get('CHURCH_NAME', 'National Holy Ghost Church of Christ')
    CHURCH_BRANCH = os.environ.get('CHURCH_BRANCH', 'Oshodi Parish, Lagos')
    CHURCH_EMAIL = os.environ.get('CHURCH_EMAIL', 'nhgccoshodi@gmail.com')
    CHURCH_PHONE = os.environ.get('CHURCH_PHONE', '+2348034540716')
    CHURCH_FACEBOOK = os.environ.get('CHURCH_FACEBOOK', 'https://www.facebook.com/nhgccoshodii/')

    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'NHGCC Oshodi Secretariat <nhgccoshodi@gmail.com>')
    ALERT_RECIPIENT_EMAILS = os.environ.get('ALERT_RECIPIENT_EMAILS', 'nhgccoshodi@gmail.com')
