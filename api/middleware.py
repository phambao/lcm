from threading import current_thread

_requests = {}


def get_request():
    t = current_thread()
    if t not in _requests:
        return None
    return _requests[t]


class CacheRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        _requests[current_thread()] = request

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        self.process_request(request)
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response