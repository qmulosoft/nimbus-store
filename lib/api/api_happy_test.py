import pytest
import json
from .test import headers_json, client, headers_binary, db
from hashlib import md5
from .models.local_file import LocalFile


created_file_id = ""
created_file_data_id = ""


@pytest.fixture()
def file_id():
    return created_file_id


@pytest.fixture()
def local_file_id():
    return created_file_data_id


def test_create_bucket(client):
    bucket = {
        "name": "default",
        "desc": "A test bucket"
    }
    result = client.simulate_post("/buckets", body=json.dumps(bucket), headers=headers_json)
    assert result.status_code == 201
    assert result.json["name"] == bucket["name"]
    assert result.json["desc"] == bucket["desc"]


def test_get_bucket(client):
    result = client.simulate_get("/buckets/default", headers=headers_json)
    assert result.status_code == 200
    assert result.json["name"] == "default"
    assert result.json["desc"] == "A test bucket"


def test_list_buckets(client):
    result = client.simulate_get("/buckets", headers=headers_json)
    assert result.status_code == 200
    assert len(result.json) == 1
    assert result.json[0]['name'] == "default"


def test_create_duplicate_bucket(client):
    bucket = {
        "name": "default",
        "desc": "A test duplicate bucket"
    }
    result = client.simulate_post("/buckets", body=json.dumps(bucket), headers=headers_json)
    assert result.status_code == 409


def test_create_file(client):
    global created_file_id
    file = {
        "name": "test.txt",
        "mime": "text/plaintext",
        "path": "test/path"
    }
    result = client.simulate_post("/buckets/default/files", body=json.dumps(file), headers=headers_json)
    assert result.status_code == 201
    assert result.json["name"] == file["name"]
    assert result.json['mime'] == file["mime"]
    created_file_id = result.json['id']


def test_get_file(client, file_id):
    result = client.simulate_get(f"/buckets/default/files/{file_id}", headers=headers_json)
    assert result.status_code == 200
    assert result.json['id'] == file_id


def test_list_files(client, file_id):
    result = client.simulate_get("/buckets/default/files", headers=headers_json)
    assert result.status_code == 200
    assert len(result.json) == 1
    assert result.json[0]['id'] == file_id


def test_get_bucket_missing(client):
    result = client.simulate_get("/buckets/0", headers=headers_json)
    assert result.status_code == 404


def test_get_file_missing(client):
    result = client.simulate_get("/buckets/default/files/abc123noexist", headers=headers_json)
    assert result.status_code == 404


def test_get_local_file_missing(client, file_id):
    result = client.simulate_get(f"/buckets/default/files/{file_id}/data/dne", headers=headers_json)
    assert result.status_code == 404


def test_create_local_file(client, file_id):
    global created_file_data_id
    data = b"test bytes"
    hash = md5()
    hash.update(data)
    digest = hash.hexdigest()
    result = client.simulate_post(f"/buckets/default/files/{file_id}/data/{digest}", body=data, headers=headers_binary)
    assert result.status_code == 204
    # assure that the file object was updated with local_file id
    result = client.simulate_get(f"/buckets/default/files/{file_id}", headers=headers_json)
    assert result.status_code == 200
    assert result.json['local_file_id'] == digest
    created_file_data_id = digest


def test_get_local_file(client, file_id, local_file_id):
    result = client.simulate_get(f"/buckets/default/files/{file_id}/data/{local_file_id}", headers=headers_binary)
    assert result.status_code == 200
    hash = md5()
    hash.update(result.content)
    assert hash.hexdigest() == local_file_id


def test_delete_file(client, file_id, local_file_id):
    result = client.simulate_delete(f"/buckets/default/files/{file_id}", headers=headers_json)
    assert result.status_code == 204
    # Make sure file data was also deleted. This isn't exposed in the API (trying to access data without a File)
    cursor = db.cursor()
    stmt = LocalFile.find_by_id_statement()
    rows = cursor.execute(stmt, [local_file_id])
    assert rows.fetchone() is None
