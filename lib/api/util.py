import falcon


def require(content_type):
    """ A decorator middleware (not a falcon middleware) for enforcing required Accept and Content-Type
    headers based on a provided content-type string. e.g. @require("application/json") """
    def decorator(next):
        def f(self, req: falcon.Request, resp: falcon.Response, **kwargs):
            if req.method in ("POST", "PUT") and content_type not in req.get_header("Content-Type", required=True):
                raise falcon.HTTPUnsupportedMediaType(f"Only {content_type} supported")
            if not req.client_accepts(content_type):
                raise falcon.HTTPNotAcceptable(f"Must accept {content_type}")
            next(self, req, resp, **kwargs)
        return f
    return decorator
