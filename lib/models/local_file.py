from .model import Model, Field


class LocalFile(Model):

    table_name = "local_file"
    fields = {
        "id": Field("A UUID v4", str, writable=False),
        "path": Field("the virtual path where the file is stored", str, writable=False),
    }