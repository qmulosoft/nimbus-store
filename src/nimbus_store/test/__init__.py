import pytest
from falcon import testing
from os.path import join, dirname
from .. import API
from sqlite3 import connect
from tempfile import mkdtemp
from migrate import Migration


db = connect(":memory:")
tempd = mkdtemp()
app = API(db, tempd)
migration_dir = join(dirname(__file__), "../../../db/sqlite/migrations")
Migration(migration_dir, db)()

headers_json = {"content-type": "application/json"}
headers_binary = {"content-type": "application/octet-stream"}


@pytest.fixture()
def client():
    return testing.TestClient(app)
