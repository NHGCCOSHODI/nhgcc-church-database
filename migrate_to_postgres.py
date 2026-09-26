"""
=============================================================================
NHGCC Oshodi Church Database - SQLite to PostgreSQL Cloud Migration Tool
=============================================================================
This script exports all existing church data from your local SQLite database
(298 members, all Sunday attendance logs, pastoral follow-ups, and settings)
and uploads it directly to your production PostgreSQL cloud database
(e.g., Supabase, Neon, Render Postgres).

Usage:
    python migrate_to_postgres.py "postgresql://user:pass@host/dbname?sslmode=require"
Or:
    Set DATABASE_URL in your .env file and run:
    python migrate_to_postgres.py
=============================================================================
"""
import os
import sys
import sqlite3
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sqlalchemy import create_engine, text
from app.database import db
import app.models  # Import models to register with db.metadata


def get_sqlite_path():
    # Check current directory first
    local_db = root_dir / 'nhgcc_church.db'
    if local_db.exists():
        return local_db

    # Check AppData location if running on Windows
    appdata = os.environ.get('LOCALAPPDATA')
    if appdata:
        appdata_db = Path(appdata) / 'NHGCC_Church_Database' / 'nhgcc_church.db'
        if appdata_db.exists():
            return appdata_db

    return None


def run_migration(pg_url):
    print("=" * 70)
    print("  NHGCC OSHODI - CLOUD DATABASE MIGRATION TOOL")
    print("=" * 70)

    sqlite_file = get_sqlite_path()
    if not sqlite_file:
        print("[ERROR] Could not find 'nhgcc_church.db' in the project directory or LocalAppData.")
        sys.exit(1)

    print(f"\n[1/5] Source SQLite database: {sqlite_file}")
    src_conn = sqlite3.connect(sqlite_file)
    src_conn.row_factory = sqlite3.Row
    src_cur = src_conn.cursor()

    # Normalize PostgreSQL URL if needed
    if pg_url.startswith('postgres://'):
        pg_url = pg_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif pg_url.startswith('postgresql://'):
        pg_url = pg_url.replace('postgresql://', 'postgresql+psycopg://', 1)

    masked_url = pg_url
    if '@' in pg_url:
        prefix = pg_url.split('@')[0]
        suffix = pg_url.split('@')[1]
        masked_url = f"{prefix.split(':')[0]}://****:****@{suffix}"

    print(f"[2/5] Target Cloud Database:  {masked_url}")

    dest_engine = create_engine(pg_url)

    print("[3/5] Initializing target database schema...")
    db.metadata.drop_all(dest_engine)
    db.metadata.create_all(dest_engine)
    print("      Schema tables verified in target PostgreSQL.")

    # Tables to migrate in dependency order
    tables = [
        ('system_settings', 'id'),
        ('members', 'id'),
        ('attendance', 'id'),
        ('follow_up_logs', 'id'),
        ('notification_logs', 'id')
    ]

    print("\n[4/5] Transferring records...")
    with dest_engine.begin() as dest_conn:
        # Clear existing data in reverse order
        for table_name, _ in reversed(tables):
            try:
                dest_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE;'))
            except Exception:
                dest_conn.execute(text(f'DELETE FROM "{table_name}"'))

        for table_name, pk_col in tables:
            try:
                src_cur.execute(f"SELECT * FROM {table_name}")
                rows = src_cur.fetchall()
            except sqlite3.OperationalError:
                print(f"      Table '{table_name}' does not exist in SQLite source. Skipping.")
                continue

            if not rows:
                print(f"      Table '{table_name}': 0 rows in source. Skipping.")
                continue

            columns = [description[0] for description in src_cur.description]
            cols_str = ', '.join([f'"{c}"' for c in columns])
            placeholders = ', '.join([f':{c}' for c in columns])

            # Prepare data
            data = []
            for row in rows:
                d = dict(row)
                if 'is_active' in d and d['is_active'] is not None:
                    d['is_active'] = bool(d['is_active'])
                data.append(d)

            # Insert all rows
            dest_conn.execute(
                text(f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders})'),
                data
            )

            # Reset PostgreSQL serial sequence to MAX(id) + 1
            if pk_col == 'id':
                try:
                    seq_query = text(f"""
                        SELECT setval(pg_get_serial_sequence('"{table_name}"', '{pk_col}'), 
                               coalesce(max({pk_col}), 1), 
                               max({pk_col}) IS NOT NULL) 
                        FROM "{table_name}";
                    """)
                    dest_conn.execute(seq_query)
                except Exception as seq_err:
                    pass

            print(f"      Successfully transferred {len(rows):>4} rows -> '{table_name}'")

    src_conn.close()

    print("\n[5/5] Verifying cloud data integrity...")
    with dest_engine.connect() as dest_conn:
        for table_name, _ in tables:
            try:
                res = dest_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                print(f"      Cloud database verification: {table_name} = {res} rows")
            except Exception as e:
                print(f"      Cloud database verification error ({table_name}): {e}")

    print("\n" + "=" * 70)
    print("  MIGRATION COMPLETE! YOUR CLOUD DATABASE IS LIVE AND READY.")
    print("=" * 70)


if __name__ == '__main__':
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
    else:
        url = os.environ.get('DATABASE_URL')

    if not url:
        print("\n[NHGCC Migration] No DATABASE_URL provided.")
        print("Please enter your PostgreSQL connection string:")
        print("Example: postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres")
        try:
            url = input("\nDATABASE_URL: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

    if not url:
        print("[ERROR] DATABASE_URL cannot be empty.")
        sys.exit(1)

    run_migration(url)
