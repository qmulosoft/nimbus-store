

class ApiResource:
    """ Base Class for HTTP API resources """

    def __init__(self, db):
        """ Must provide a database connection """
        self._db = db
