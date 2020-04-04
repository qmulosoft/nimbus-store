from .model import Model, Field


class File(Model):

    table_name = "file"
    fields = {
        "id": Field("A UUID v4", str, writable=False),
        "name": Field("the name of the file", str),
        "mime": Field("the MIME type of the file", str),
        "path": Field("the virtual path where the file is stored", str),
        "pending": Field("whether the associated local file has been written to disk or not", bool, writable=False),
        "created": Field("the time the file was created, automatically set by DB", str, writable=False),
        "last_updated": Field("the time the file was last modified in any way", str, writable=False),
        "local_file_id": Field("the if of the associated local file", str, writable=False),
        "bucket_id": Field("the id of the bucket associated with this file", int, writable=False)
    }