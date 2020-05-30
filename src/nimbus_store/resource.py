

class ApiResource:
    """ Base Class for HTTP API resources """

    def __init__(self, db, root_path: str):
        """ Must provide a database connection """
        self._db = db
        self._root = root_path
