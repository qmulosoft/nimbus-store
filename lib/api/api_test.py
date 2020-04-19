import pytest
from falcon import testing
import json
from os.path import join, dirname
from . import API
from sqlite3 import connect
from tempfile import mkdtemp
from migrate import Migration


db = connect(":memory:")
tempd = mkdtemp()
app = API(db, tempd)
migration_dir = join(dirname(__file__), "../../db/sqlite/migrations")
Migration(migration_dir, db)()

headers_json = {"content-type": "application/json"}


@pytest.fixture()
def client():
    return testing.TestClient(app)


def test_get_bucket_missing(client):
    result = client.simulate_get("/buckets/0")
    assert result.status_code == 404


def test_create_bucket(client):
    bucket = {
        "name": "default",
        "desc": "A test bucket"
    }
    result = client.simulate_post("/buckets", body=json.dumps(bucket), headers=headers_json)
    assert result.status_code == 201
    assert result.json["name"] == bucket["name"]
    assert result.json["desc"] == bucket["desc"]


def test_create_duplicate_bucket(client):
    bucket = {
        "name": "default",
        "desc": "A test duplicate bucket"
    }
    result = client.simulate_post("/buckets", body=json.dumps(bucket), headers=headers_json)
    assert result.status_code == 409


def test_create_file(client):
    file = {
        "name": "test.txt",
        "mime": "text/plaintext",
        "path": "test/path"
    }
    result = client.simulate_post("/buckets/default/files", body=json.dumps(file), headers=headers_json)
    assert result.status_code == 201
    assert result.json["name"] == file["name"]
    assert result.json['mime'] == file["mime"]
