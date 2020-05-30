import falcon
import sqlite3
from .buckets import BucketCollectionResource, BucketResource
from .files import FileCollectionResource, FilesResource
from .local_files import LocalFileResource


class API(falcon.API):
    """ The HTTP REST API for the storage service. """

    def __init__(self, sql_conn: sqlite3.Connection, volume: str):
        super().__init__()
        file_collection = FileCollectionResource(sql_conn, volume)
        files = FilesResource(sql_conn, volume)
        bucket_collection = BucketCollectionResource(sql_conn, volume)
        buckets = BucketResource(sql_conn, volume)
        data = LocalFileResource(sql_conn, volume)
        # If GETting a file, id is [file].id, if POSTing, if is [local_file].id
        # e.g. on GET it is a uuid.v4, on POST it is a md5 sum
        self.add_route("/buckets/{bucket}/files", file_collection)
        self.add_route("/buckets/{bucket}/files/{file}/data/{checksum}", data)
        self.add_route("/buckets/{bucket}/files/{file}", files)
        self.add_route("/buckets", bucket_collection)
        self.add_route("/buckets/{bucket}", buckets)
