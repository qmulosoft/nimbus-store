#!/usr/bin/env python3.6

import argparse
import sqlite3
import falcon
from lib.models.bucket import Bucket
from lib.api.buckets import BucketCollectionResource, BucketResource, validate_bucket
from lib.api.files import FileCollectionResource, validate_file
from lib.api.local_files import LocalFileResource
from lib.models.file import File
from lib.models.local_file import LocalFile
from wsgiref import simple_server

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


app = falcon.API()


files = FileCollectionResource(sql_conn)
bucket_collection = BucketCollectionResource(sql_conn)
buckets = BucketResource(sql_conn)
data = LocalFileResource(sql_conn, args.volume)
# If GETting a file, id is [file].id, if POSTing, if is [local_file].id
# e.g. on GET it is a uuid.v4, on POST it is a md5 sum
app.add_route("/buckets/{bucket}/files", files)
app.add_route("/buckets/{bucket}/files/{file}/data/{checksum}", data)
app.add_route("/buckets", bucket_collection)
app.add_route("/buckets/{bucket}", buckets)

httpd = simple_server.make_server("localhost", 4242, app)
httpd.serve_forever()
