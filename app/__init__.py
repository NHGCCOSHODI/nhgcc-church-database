import os
import sys
import shutil
from pathlib import Path
from flask import Flask, render_template
from app.config import Config, BASE_DIR, DATA_DIR
from app.database import db
from app.models import Member, SystemSetting
from app.services.scheduler import init_scheduler
from app.services.pdf_importer import import_pdf_to_database


def create_app(config_class=Config):
    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(sys._MEIPASS, 'app', 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'app', 'static')
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)

    try:
        db_target = DATA_DIR / 'nhgcc_church.db'
        if not db_target.exists():
            seed_db = BASE_DIR / 'nhgcc_church.db'
            if seed_db.exists() and seed_db.resolve() != db_target.resolve():
                shutil.copy2(seed_db, db_target)
                print('[NHGCC Startup] Initialized local church database from seed.')
    except Exception as e:
        print(f'[NHGCC Startup] Notice on seed db copy: {e}')

    app.config.from_object(config_class)

    # Cloud connectivity probe: if cloud DB is specified but machine is offline, fall back gracefully to local SQLite
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'supabase.com' in db_uri or 'postgres' in db_uri:
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.pool import NullPool
            test_engine = create_engine(db_uri, poolclass=NullPool, connect_args={'connect_timeout': 5, 'prepare_threshold': None})
            with test_engine.connect() as probe_conn:
                probe_conn.execute(text('SELECT 1'))
            print('[NHGCC Startup] Connected successfully to Supabase Cloud Database (Live Sync Active).')
        except Exception as conn_err:
            local_db_path = DATA_DIR / 'nhgcc_church.db'
            if not local_db_path.exists():
                local_db_path = BASE_DIR / 'nhgcc_church.db'
            print(f'[NHGCC Startup] Cloud database unreachable ({conn_err}). Falling back to local offline database: {local_db_path}')
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{local_db_path.as_posix()}'
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

    db.init_app(app)

    from app.routes.dashboard import dashboard_bp
    from app.routes.attendance import attendance_bp
    from app.routes.members import members_bp
    from app.routes.follow_up import follow_up_bp
    from app.routes.notifications import notifications_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(follow_up_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(settings_bp)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f'[NHGCC Startup] Notice on db.create_all: {e}')

        try:
            if not SystemSetting.query.filter_by(setting_key='church_name').first():
                SystemSetting.set_value('church_name', app.config.get('CHURCH_NAME', 'National Holy Ghost Church of Christ'))
                SystemSetting.set_value('church_branch', app.config.get('CHURCH_BRANCH', 'Oshodi Parish, Lagos'))
                SystemSetting.set_value('church_email', app.config.get('CHURCH_EMAIL', 'nhgccoshodi@gmail.com'))
                SystemSetting.set_value('church_phone', app.config.get('CHURCH_PHONE', '+2348034540716'))
                SystemSetting.set_value('church_facebook', app.config.get('CHURCH_FACEBOOK', 'https://www.facebook.com/nhgccoshodii/'))
                SystemSetting.set_value('smtp_server', app.config.get('SMTP_SERVER', 'smtp.gmail.com'))
                SystemSetting.set_value('smtp_port', str(app.config.get('SMTP_PORT', 587)))
                SystemSetting.set_value('smtp_use_tls', 'True')
                SystemSetting.set_value('mail_sender', app.config.get('MAIL_DEFAULT_SENDER', 'NHGCC Oshodi Secretariat <nhgccoshodi@gmail.com>'))
        except Exception as e:
            print(f'[NHGCC Startup] Notice on settings initialization: {e}')

        try:
            if Member.query.count() == 0:
                pdf_path = DATA_DIR / 'NHGCC database .pdf'
                if not pdf_path.exists():
                    pdf_path = BASE_DIR / 'NHGCC database .pdf'
                if pdf_path.exists():
                    import_pdf_to_database(str(pdf_path))
                    print(f'[NHGCC Startup] Successfully ingested initial members from {pdf_path.name}')
        except Exception as e:
            print(f'[NHGCC Startup] Notice on PDF import: {e}')

        try:
            init_scheduler(app)
        except Exception as e:
            print(f'[NHGCC Scheduler] Warning: {e}')

        try:
            from app.services.sync_service import sync_offline_sqlite_to_cloud
            sync_ok, sync_msg = sync_offline_sqlite_to_cloud(app)
            print(f'[NHGCC Startup] Offline-Cloud Sync Status: {sync_msg}')
        except Exception as e:
            print(f'[NHGCC Startup] Sync notice: {e}')

    @app.errorhandler(500)
    def internal_server_error(e):
        import traceback
        from datetime import datetime
        err_msg = traceback.format_exc()
        print(f'[NHGCC 500 Server Error] {err_msg}')
        try:
            log_file = DATA_DIR / 'server_error.log'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ---\n{err_msg}\n")
        except Exception:
            pass

        template_path = os.path.join(app.template_folder or 'templates', '500.html')
        if os.path.exists(template_path):
            return render_template('500.html'), 500
        return "<h3>An unexpected error occurred.</h3><p>The error has been logged. <a href='/'>Return to Dashboard</a></p>", 500

    return app
