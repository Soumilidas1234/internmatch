import os
import tempfile

os.environ["SECRET_KEY"] = "test-secret-key-internmatch"
os.environ["ADMIN_PASSWORD"] = "TestAdmin@123"
os.environ["DEMO_STUDENT_PASSWORD"] = "Demo@123"
os.environ["FLASK_DEBUG"] = "0"

_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db_file.close()
os.environ["DATABASE_URI"] = "sqlite:///" + _db_file.name.replace("\\", "/")

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
