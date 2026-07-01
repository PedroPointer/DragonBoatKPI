"""Test script to check for import/route errors."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dragonboat.database import init_db
init_db()

from dragonboat.web.app import app
from dragonboat.repo import get_sesiones

# Try to reproduce what the index route does
try:
    sesiones = get_sesiones(50)
    print(f"Sesiones loaded: {len(sesiones)}")
    for s in sesiones:
        csv_name = s.csv_upload.filename if s.csv_upload else "—"
        print(f"  Sesion #{s.id}: {s.custom_name or 'Prueba ' + str(s.test_number)} ({csv_name}), metric={s.metric is not None}, boat={s.boat}")
    print("OK - no errors")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
