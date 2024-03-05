import pytz
from threading import current_thread

from django.utils import timezone
from django.utils.translation import activate

_requests = {}


def get_request():
    t = current_thread()
    if t not in _requests:
        return None
    return _requests[t]


def set_request(request):
    _requests[current_thread()] = request


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

        # All lru objects cleared
        from sales.models.catalog import Catalog
        Catalog().get_full_ancestor.cache_clear()

        # Code to be executed for each request/response after
        # the view is called.

        return response


class SettingTranslateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if request.user.is_authenticated is True:
            if user.lang:
                activate(user.lang)
        return self.get_response(request)


class SettingTimeZoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        tz = None
        if request.user.is_authenticated is True:
            if user.company and user.company.company_timezone:
                tz = user.company.company_timezone
        if tz:
            timezone.activate(tz)
        else:
            timezone.deactivate()
        return self.get_response(request)