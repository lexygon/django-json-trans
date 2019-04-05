from django.middleware.locale import LocaleMiddleware
from django.utils import translation


class QueryParameterLocaleMiddleware(LocaleMiddleware):
    def process_request(self, request):
        """
        Overrides the parent class to try getting the language code from
        request parameter.
        """
        if 'lang' in request.GET:
            translation.activate(request.GET['lang'])
            request.LANGUAGE_CODE = translation.get_language()
        else:
            super(QueryParameterLocaleMiddleware, self).process_request(request)
