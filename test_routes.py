import os
import sys
os.environ['FLASK_ENV'] = 'testing'
from app import create_app

app = create_app()
client = app.test_client()

routes = [
    ('/', 'Executive Dashboard'),
    ('/attendance/checkin', 'Sunday Entrance Check-In Desk'),
    ('/attendance/history', 'Sunday Service Records & History'),
    ('/members/', 'Church Members Directory'),
    ('/members/1', 'Member Profile'),
    ('/follow-up/', 'Retention & Absentee Follow-Up Desk'),
    ('/notifications/', 'Church Notification & Email Hub'),
    ('/settings/', 'Church System & Email Settings'),
    ('/static/css/style.css', '--primary'),
    ('/static/js/main.js', 'DOMContentLoaded'),
    ('/static/js/attendance.js', 'DOMContentLoaded'),
    ('/static/js/dashboard.js', 'initDashboardCharts'),
]

all_passed = True
print('=' * 70)
print('  COMPREHENSIVE HTTP & TEMPLATE RENDER VERIFICATION')
print('=' * 70)
for url, expected_text in routes:
    res = client.get(url)
    status_ok = res.status_code == 200
    has_text = expected_text in res.data.decode('utf-8', errors='ignore')
    status_sym = 'PASS' if (status_ok and has_text) else 'FAIL'
    print(f'[{status_sym}] {res.status_code} | {url:<30} | Match: \"{expected_text}\"')
    if not (status_ok and has_text):
        all_passed = False
        print(f"Error on {url}: status {res.status_code}")

if all_passed:
    print('=' * 70)
    print('ALL 12 ROUTES AND STATIC ASSETS PASSED WITH HTTP 200!')
    print('=' * 70)
