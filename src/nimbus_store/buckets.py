import falcon
from .models.bucket import Bucket
from .util import require
from .resource import ApiResource
import sqlite3


def validate_bucket(next):
    def f(self, req: falcon.Request, resp: falcon.Response, bucket: str, **kwargs):
        cursor = self._db.cursor()
        stmt = cursor.execute(Bucket.find_statement(Bucket.name), [bucket])
        row = stmt.fetchone()
        if row is None:
            raise falcon.HTTPNotFound(description=f"No bucket with name '{bucket}' found")
        bucket = Bucket.from_db_row(row)
        req.context.bucket = bucket
        next(self, req, resp, **kwargs)
    return f


class BucketResource(ApiResource):
    """ Methods to act on an individual bucket, e.g. getting, editing or deleting """

    @validate_bucket
    @require("application/json")
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        resp.media = req.context.bucket.to_dict()


class BucketCollectionResource(ApiResource):
    """ Methods to act on the collection, e.g. creating or listing all buckets """

    def _get_bucket(self, name: str) -> Bucket:
        cursor = self._db.cursor()
        stmt = Bucket.find_statement(Bucket.name)
        r = cursor.execute(stmt, [name])
        return Bucket.from_db_row(r.fetchone())

    @require("application/json")
    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """ List all buckets visible to the user """
        cursor = self._db.cursor()
        stmt = Bucket.find_statement()
        rows = cursor.execute(stmt)
        resources = rows.fetchall()  # If this is likely to ever be large, we should paginate this
        buckets = []
        for res in resources:
            buckets.append(Bucket.from_db_row(res).to_dict())
        resp.media = buckets

    @require("application/json")
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        bucket = Bucket.from_dict(req.media)
        cursor = self._db.cursor()
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
            self._db.commit()
            bucket = self._get_bucket(bucket.name.value)
        except TypeError as e:
            # this is probably an invalid value for a field
            raise falcon.HTTPBadRequest("Invalid value for bucket", str(e))
        resp.status = falcon.HTTP_201
        resp.media = bucket.to_dict()
