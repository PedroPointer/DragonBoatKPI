"""Test web app directly."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dragonboat.database import init_db
init_db()

from dragonboat.web.app import app

# Use TestClient
from starlette.testclient import TestClient

client = TestClient(app)
try:
    response = client.get("/")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Body: {response.text[:1000]}")
except Exception as e:
    import traceback
    traceback.print_exc()
