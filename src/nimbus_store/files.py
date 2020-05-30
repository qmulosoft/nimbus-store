import falcon
from .models.file import File
from .models.local_file import LocalFile
from .buckets import validate_bucket
from .util import require
from .resource import ApiResource
import sqlite3
from uuid import uuid4
from os import remove
from os.path import join


def validate_file(next):
    def f(self, req: falcon.Request, resp: falcon.Response, file: str, **kwargs):
        cursor = self._db.cursor()
        stmt = cursor.execute(File.find_statement(File.id), [file])
        row = stmt.fetchone()
        if row is None:
            raise falcon.HTTPNotFound(description=f"No file with id '{id}' found")
        file = File.from_db_row(row)
        req.context.file = file
        next(self, req, resp, **kwargs)
    return f


class FilesResource(ApiResource):
    """ Manages getting, deleting and updating single File resources """

    @require("application/json")
    @validate_bucket
    @validate_file
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        resp.media = req.context.file.to_dict()

    @require("application/json")
    @validate_bucket
    @validate_file
    def on_delete(self, req: falcon.Request, resp: falcon.Response):
        stmt = File.delete_statement(req.context.file.id)
        cursor = self._db.cursor()
        r = cursor.execute(stmt, [req.context.file.id.value])
        if r.rowcount != 1:
            self._db.rollback()
            resp.status = falcon.HTTP_CONFLICT
            resp.error = {"message": f"{r.rowcount} rows affected upon DELETE execution"}
        # If this was the only File associated with the related LocalFile, delete that LocalFile
        self.garbage_collect(req.context.file.local_file_id.value)
        self._db.commit()
        resp.status = falcon.HTTP_NO_CONTENT

    def garbage_collect(self, local_file_id):
        """ A File's data is only deleted if it is the only/last file referencing it when deleted. If it is, delete the
         local file data from the store """
        cursor = self._db.cursor()
        stmt = File.find_statement(File.local_file_id)
        r = cursor.execute(stmt, [local_file_id])
        if r.fetchone() is None:  # There are no other Files associated with this LocalFile, so delete the data on disk
            stmt = LocalFile.delete_statement(LocalFile.id)
            cursor.execute(stmt, [local_file_id])
            remove(join(self._root, local_file_id))
            self._db.commit()


class FileCollectionResource(ApiResource):
    """ Manages creating, updating and deleting of file metadata, which is associated with
    file binary data in the form of local_files """
    def _get_file(self, id: str) -> File:
        cursor = self._db.cursor()
        stmt = File.find_by_id_statement()
        r = cursor.execute(stmt, [id])
        return File.from_db_row(r.fetchone())

    @require("application/json")
    @validate_bucket
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """ Handles requests to list all files in a given bucket """
        cursor = self._db.cursor()
        stmt = File.find_statement(File.bucket_id)
        rows = cursor.execute(stmt, [req.context.bucket.id.value])
        files = []
        for row in rows.fetchall():
            files.append(File.from_db_row(row).to_dict())
        resp.media = files

    @require("application/json")
    @validate_bucket
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """ Handles Requests to create new files """
        file = File.from_dict(req.media)
        file.bucket_id.value = req.context.bucket.id.value
        file.id.value = str(uuid4())
        cursor = self._db.cursor()
        stmt, params = file.insert_statement(file.id, file.bucket_id)
        try:
            cursor.execute(stmt, params)
            self._db.commit()
            file = self._get_file(file.id.value)
        except sqlite3.Error as e:
            raise falcon.HTTPBadRequest("Invalid value for file", str(e))
        resp.status = falcon.HTTP_201
        resp.media = file.to_dict()

