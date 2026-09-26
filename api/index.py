import os
import sys
from pathlib import Path

# Set VERCEL environment flag to ensure background schedulers are avoided
os.environ['VERCEL'] = '1'

# Add parent directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import create_app

# Vercel serverless WSGI expects 'app'
app = create_app()
