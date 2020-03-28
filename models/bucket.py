from .model import Model, Field


class Bucket(Model):
    """ Buckets are top-level folders. Typically an app uses a discrete bucket.
    For instance, an image manager may use a bucket called images. Buckets must be unique. """

    table_name = "bucket"
    fields = {
        "id": Field("autoincrement", int, writable=False),
        "name": Field("The name of the bucket (must be globally unique)", str),
        "desc": Field("A description of the bucket's purpose or scope", str)
    }
