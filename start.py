#!/usr/bin/env python3

import argparse
import hashlib
import sqlite3
import falcon
from models.bucket import Bucket
from models.file import File
from models.local_file import LocalFile
from wsgiref import simple_server
from uuid import uuid4
from os.path import join, getsize

parser = argparse.ArgumentParser(
    description="Nimbus distributed data store service"
)

parser.add_argument(
    'volume',
    help="the local system path to use as a nimbus storage root"
)
parser.add_argument(
    'db',
    help="the path to the local instance of the database file"
)

args = parser.parse_args()

sql_conn = sqlite3.connect(args.db)


def require(content_type):
    def decorator(next):
        def f(self, req: falcon.Request, resp: falcon.Response, **kwargs):
            if req.method in ("POST", "PUT") and content_type not in req.get_header("Content-Type", required=True):
                raise falcon.HTTPUnsupportedMediaType(f"Only {content_type} supported")
            if not req.client_accepts(content_type):
                raise falcon.HTTPNotAcceptable(f"Must accept {content_type}")
            next(self, req, resp, **kwargs)
        return f
    return decorator


def validate_bucket(next):
    def f(self, req: falcon.Request, resp: falcon.Response, bucket: str, **kwargs):
        cursor = sql_conn.cursor()
        stmt = cursor.execute(Bucket.find_statement(Bucket.name), [bucket])
        row = stmt.fetchone()
        if row is None:
            raise falcon.HTTPNotFound(description=f"No bucket with name '{bucket}' found")
        bucket = Bucket.from_db_row(row)
        req.context.bucket = bucket
        next(self, req, resp, **kwargs)
    return f


def validate_file(next):
    def f(self, req: falcon.Request, resp: falcon.Response, file: str, **kwargs):
        cursor = sql_conn.cursor()
        stmt = cursor.execute(File.find_statement(File.id), [file])
        row = stmt.fetchone()
        if row is None:
            raise falcon.HTTPNotFound(description=f"No file with id '{id}' found")
        file = File.from_db_row(row)
        req.context.file = file
        next(self, req, resp, **kwargs)
    return f


class LocalFilesResource:
    """ Manages uploading and downloading of local files, which is actual, binary data """
    @require("application/octet-stream")
    @validate_bucket
    @validate_file
    def on_post(self, req: falcon.Request, resp: falcon.Response, checksum: str):
        """ Upload binary data to a destination file on the local system """
        # TODO actually validate checksum
        length = req.content_length
        read_bytes = 0
        hash = hashlib.md5()
        with open(join(args.volume, checksum), "wb") as fd:
            while read_bytes < length:
                count = min(4096, length-read_bytes)  # TODO make this configurable (read size)
                read_bytes += 4096
                segment = req.stream.read(count)
                hash.update(segment)
                fd.write(segment)
        local_file = LocalFile(id=hash.hexdigest(), path="")  # NOTE path is probably pointless for now
        stmt, params = local_file.insert_statement(local_file.id, local_file.path)
        cursor = sql_conn.cursor()
        cursor.execute(stmt, params)
        # TODO this should be a method on File
        cursor.execute(f"UPDATE [{File.table_name}] "
                       f"SET [{File.local_file_id.name}]=?, "
                       f"[{File.pending.name}]=0 "
                       f"WHERE [{File.id.name}]='{req.context.file.id.value}'", [hash.hexdigest()])
        sql_conn.commit()
        resp.status = falcon.HTTP_NO_CONTENT

    @require("application/octet-stream")
    @validate_bucket
    @validate_file
    def on_get(self, req: falcon.Request, resp: falcon.Response, checksum: str):
        """ Download binary data associated with a given file object """
        cursor = sql_conn.cursor()
        stmt = LocalFile.find_by_id_statement()
        r = cursor.execute(stmt, [checksum])
        row = r.fetchone()
        if row is None:
            raise falcon.HTTPNotFound(description="Invalid checksum or missing data")
        local_file = LocalFile.from_db_row(row)
        if local_file.id.value != req.context.file.local_file_id.value:
            raise falcon.HTTPNotFound(description="Invalid checksum or missing data")
        fname = join(args.volume, checksum)
        length = getsize(fname)
        resp.content_type = "application/octet-stream"
        f = open(fname, "rb")
        resp.set_stream(f, length)


class FilesResource:
    """ Manages creating, updating and deleting of file metadata, which is associated with
    file binary data in the form of local_files """
    def _get_file(self, id: str) -> File:
        cursor = sql_conn.cursor()
        stmt = File.find_by_id_statement()
        r = cursor.execute(stmt, [id])
        return File.from_db_row(r.fetchone())

    @require("application/json")
    @validate_bucket
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """ Handles Requests to create new files """
        file = File.from_dict(req.media)
        file.bucket_id.value = req.context.bucket.id.value
        file.id.value = str(uuid4())
        cursor = sql_conn.cursor()
        stmt, params = file.insert_statement(file.id, file.bucket_id)
        try:
            cursor.execute(stmt, params)
            sql_conn.commit()
            file = self._get_file(file.id.value)
        except sqlite3.Error as e:
            raise falcon.HTTPBadRequest("Invalid value for bucket", str(e))
        resp.status = falcon.HTTP_201
        resp.media = file.to_dict()


class BucketsResource:

    def _get_bucket(self, name: str) -> Bucket:
        cursor = sql_conn.cursor()
        stmt = Bucket.find_statement(Bucket.name)
        r = cursor.execute(stmt, [name])
        return Bucket.from_db_row(r.fetchone())

    @require("application/json")
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        bucket = Bucket.from_dict(req.media)
        cursor = sql_conn.cursor()
        try:
            stmt = cursor.execute(f"""SELECT {Bucket.select_columns()} FROM {Bucket.table_name}
                WHERE {Bucket.name.name} = '{bucket.name.value}'""")
            if stmt.fetchone() is not None:
                raise falcon.HTTPConflict(description="A bucket with that name already exists")
        except sqlite3.Error as e:
            raise falcon.HTTPInternalServerError(description=str(e))
        try:
            stmt, params = bucket.insert_statement()
            cursor.execute(stmt, params)
            sql_conn.commit()
            bucket = self._get_bucket(bucket.name.value)
        except TypeError as e:
            # this is probably an invalid value for a field
            raise falcon.HTTPBadRequest("Invalid value for bucket", str(e))
        resp.status = falcon.HTTP_201
        resp.media = bucket.to_dict()


app = falcon.API()


files = FilesResource()
buckets = BucketsResource()
data = LocalFilesResource()
# If GETting a file, id is [file].id, if POSTing, if is [local_file].id
# e.g. on GET it is a uuid.v4, on POST it is a md5 sum
app.add_route("/buckets/{bucket}/files", files)
app.add_route("/buckets/{bucket}/files/{file}/data/{checksum}", data)
app.add_route("/buckets", buckets)

httpd = simple_server.make_server("localhost", 4242, app)
httpd.serve_forever()
