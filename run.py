"""
NHGCC Church Database - Local Development Server
Run with: python run.py
"""
import os
import sys
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

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "=" * 60)
    print("  NHGCC Oshodi Church Database Management System")
    print(f"  Live local server: http://127.0.0.1:{port}")
    print("=" * 60 + "\n")
    app.run(host='127.0.0.1', port=port, debug=True)
