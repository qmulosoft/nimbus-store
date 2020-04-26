import falcon
from .models.file import File
from .models.local_file import LocalFile
from .buckets import validate_bucket
from .files import validate_file
from .util import require
from .resource import ApiResource
import hashlib
from os.path import getsize, join


class LocalFileResource(ApiResource):
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
        with open(join(self._root, checksum), "wb") as fd:
            while read_bytes < length:
                count = min(4096, length-read_bytes)  # TODO make this configurable (read size)
                read_bytes += 4096
                segment = req.stream.read(count)
                hash.update(segment)
                fd.write(segment)
        local_file = LocalFile(id=hash.hexdigest(), path="")  # NOTE path is probably pointless for now
        stmt, params = local_file.insert_statement(local_file.id, local_file.path)
        cursor = self._db.cursor()
        cursor.execute(stmt, params)
        # TODO this should be a method on File
        cursor.execute(f"UPDATE [{File.table_name}] "
                       f"SET [{File.local_file_id.name}]=?, "
                       f"[{File.pending.name}]=0 "
                       f"WHERE [{File.id.name}]='{req.context.file.id.value}'", [hash.hexdigest()])
        self._db.commit()
        resp.status = falcon.HTTP_NO_CONTENT

    @require("application/octet-stream")
    @validate_bucket
    @validate_file
    def on_get(self, req: falcon.Request, resp: falcon.Response, checksum: str):
        """ Download binary data associated with a given file object """
        cursor = self._db.cursor()
        stmt = LocalFile.find_by_id_statement()
        r = cursor.execute(stmt, [checksum])
        row = r.fetchone()
        if row is None:
            raise falcon.HTTPNotFound(description="Invalid checksum or missing data")
        local_file = LocalFile.from_db_row(row)
        if local_file.id.value != req.context.file.local_file_id.value:
            raise falcon.HTTPNotFound(description="Invalid checksum or missing data")
        fname = join(self._root, checksum)
        length = getsize(fname)
        resp.content_type = "application/octet-stream"
        f = open(fname, "rb")
        resp.set_stream(f, length)
