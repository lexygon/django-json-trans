from collections import OrderedDict

from django.conf import settings
from django.db import models
from django.db.models.expressions import RawSQL
from django.db.models.query import ModelIterable
from django.utils.translation import get_language

LANGUAGES = OrderedDict(settings.LANGUAGES)
LANGUAGE_CODE = settings.LANGUAGE_CODE
FALLBACK = False  # settings.FALLBACK


class TranslationMixin(object):
    default_language_code = LANGUAGE_CODE
    fallback = FALLBACK

    def get_language_code(self, language_code=None):
        if not language_code:
            language_code = get_language()

        if language_code in LANGUAGES.keys():
            return language_code
        else:
            return self.default_language_code

    def is_default_language(self, language_code):
        language_code = self.get_language_code(language_code)
        return language_code == LANGUAGE_CODE


class TranslationModelIterable(ModelIterable):
    def __iter__(self):
        for obj in super(TranslationModelIterable, self).__iter__():
            if self.queryset._language_code:
                obj.language(self.queryset._language_code)
            yield obj


class TranslationQuerySet(models.QuerySet, TranslationMixin):
    _language_code = None

    def __init__(self, model=None, query=None, using=None, hints=None):
        super(TranslationQuerySet, self).__init__(model, query, using, hints)
        self._iterable_class = TranslationModelIterable
        self._language_code = self.get_language_code()

    def language_or_default(self, language_code=None):
        language_code = self.get_language_code(language_code)
        self._language_code = language_code
        return self

    def language(self, language_code=None):
        language_code = self.get_language_code(language_code)
        self._language_code = language_code
        results = self.language_or_default(language_code)

        if self.is_default_language(language_code):
            return results

        return results.filter(translations__has_key=language_code)

    def _clone(self, *args, **kwargs):
        clone = super(TranslationQuerySet, self)._clone(*args, **kwargs)
        clone._language_code = self._language_code
        return clone

    def filter(self, *args, **kwargs):
        if not self.is_default_language(self._language_code):
            for key, value in kwargs.items():
                if key.split('__')[0] in self.model._meta.translatable_fields:
                    del kwargs[key]
                    key = 'translations__{}__{}'.format(self._language_code, key)
                    kwargs[key] = value

        return super(TranslationQuerySet, self).filter(*args, **kwargs)

    def order_by_json_path(self, json_path, language_code=None, order='asc'):
        """
        Orders a queryset by the value of the specified `json_path`.
        More about the `#>>` operator and the `json_path` arg syntax:
        https://www.postgresql.org/docs/current/static/functions-json.html
        More about Raw SQL expressions:
        https://docs.djangoproject.com/en/dev/ref/models/expressions/#raw-sql-expressions
        Usage example:
            MyModel.objects.language('en_us').filter(is_active=True).order_by_json_path('title')
        """
        language_code = (language_code or self._language_code or self.get_language_code(language_code))
        json_path = '{%s,%s}' % (language_code, json_path)

        # Our jsonb field is named `translations`.
        raw_sql_expression = RawSQL("translations#>>%s", (json_path,))

        if order == 'desc':
            raw_sql_expression = raw_sql_expression.desc()

        return self.order_by(raw_sql_expression)


class TranslationManager(models.Manager, TranslationMixin):
    _queryset_class = TranslationQuerySet

    def get_queryset(self, language_code=None):
        qs = self._queryset_class(self.model, using=self.db, hints=self._hints)
        language_code = self.get_language_code(language_code)
        qs.language(language_code)

        return qs

    def language_or_default(self, language_code):
        language_code = self.get_language_code(language_code)

        return self.get_queryset(language_code).language_or_default(language_code)

    def language(self, language_code=None):
        language_code = self.get_language_code(language_code)

        return self.get_queryset(language_code).language(language_code)

    def order_by_json_path(self, json_path, language_code=None, order='asc'):
        """
        Makes the method available through the manager (i.e. `Model.objects`).
        Usage example:
            MyModel.objects.order_by_json_path('title', order='desc')
            MyModel.objects.order_by_json_path('title', language_code='en_us', order='desc')
        """
        return self.get_queryset(language_code).order_by_json_path(json_path, language_code, order)
