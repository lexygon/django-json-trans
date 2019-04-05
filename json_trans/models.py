from __future__ import unicode_literals
import os
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import options, ImageField, FileField
from django.db.models.fields.files import ImageFieldFile, FieldFile
from django.utils.translation import get_language
from django.core.files.storage import DefaultStorage

from .exceptions import NonTranslatableFieldError
from .managers import TranslationManager, TranslationMixin


options.DEFAULT_NAMES += ('translatable_fields',)
fs = DefaultStorage()


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, (FieldFile, ImageFieldFile)):
            return o.url
        else:
            return super().default(o)


def save_form_data(instance, data):
    pass


class Language(object):
    def __init__(self, **translations):
        for field, translation in translations.items():
            setattr(self, field, translation)


class TranslatableModel(models.Model, TranslationMixin):
    translations = JSONField(null=True, blank=True, editable=False, default=dict, encoder=JSONEncoder)
    _translated = None

    objects = TranslationManager()

    def __init__(self, *args, **kwargs):
        self._language_code = get_language()
        super(TranslatableModel, self).__init__(*args, **kwargs)

    def __getattribute__(self, name):
        fallback = object.__getattribute__(self, 'fallback')
        attr = object.__getattribute__(self, name)
        opts = object.__getattribute__(self, '_meta')

        default_lang = object.__getattribute__(self, 'default_language_code')
        active_lang = get_language()

        if name not in opts.translatable_fields or default_lang == active_lang:
            return attr

        translated = object.__getattribute__(self, '_translated')

        if translated:
            if hasattr(translated, name):
                _field = self._meta.get_field(name)
                if isinstance(_field, ImageField):
                    return ImageFieldFile(self, _field, getattr(translated, name, attr if fallback else ''))
                elif isinstance(_field, FileField):
                    return FieldFile(self, _field, getattr(translated, name, attr if fallback else ''))
                else:
                    return getattr(translated, name, attr if fallback else '')

            elif hasattr(translated, '__iter__') and (active_lang in translated or name in translated):
                try:
                    return translated.get(active_lang).get(name, '')
                except Exception as e:
                    print('exception happened in model getattribute', e)

        return attr

    def clean_fields(self, exclude=None):
        if exclude is None:
            exclude = []
        errors = {}
        for f in self._meta.fields:
            # only changed here from original method for excluding translatable fields
            if f.name in exclude or f.name in self._meta.translatable_fields:
                continue

            raw_value = getattr(self, f.attname)

            if f.blank and raw_value in f.empty_values:
                continue

            try:
                setattr(self, f.attname, f.clean(raw_value, self))
            except ValidationError as e:
                errors[f.name] = e.error_list

        if errors:
            raise ValidationError(errors)

    def populate_translations(self, translations):
        for field in self._meta.translatable_fields:
            if field not in translations:
                translations[field] = ''

        return translations

    def translate(self, language_code=None, **kwargs):
        self._language_code = self.get_language_code(language_code)

        if not self.is_default_language(self._language_code):
            self.translations = self.translations or {}
            self.translations[self._language_code] = self.translations.get(
                self._language_code, {}
            )

        for name, value in kwargs.items():
            if name not in self._meta.translatable_fields:
                raise NonTranslatableFieldError(name)

            if self.is_default_language(self._language_code):
                setattr(self, name, value)
            else:
                if isinstance(value, InMemoryUploadedFile):

                    setattr(self._meta.fields[-1], 'save_form_data', save_form_data)
                    _file = value

                    save_path = os.path.join(settings.MEDIA_ROOT, 'uploads', _file.name)
                    filename = fs.save(save_path, _file)
                    value = fs.url(filename)

                self.translations.get(self._language_code, {})[name] = value

        if language_code:
            self.language(language_code)

    def reset_language(self):
        self._translated = None
        self._language_code = get_language()

    def language(self, language_code=None):
        self.reset_language()
        fields = self._meta.translatable_fields
        self._language_code = self.get_language_code(language_code)

        if self.is_default_language(language_code):
            return self

        self.default_language = Language(**{f: getattr(self, f, None) for f in fields})
        translations = self.translations or {}

        translations = translations.get(self._language_code, {})

        if (not translations and not self.fallback) or translations:
            translations = self.populate_translations(translations)
            self._translated = Language(**translations)

        return self

    def language_or_none(self, language_code):
        language_code = self.get_language_code(language_code)

        if self.is_default_language(language_code):
            return self.language(language_code)

        if not self.translations or not self.translations.get(language_code):
            return None

        return self.language(language_code)

    def language_as_dict(self, language_code=None):
        if not language_code:
            language_code = self._language_code

        tf = self._meta.translatable_fields
        language_code = self.get_language_code(language_code)

        if self.is_default_language(language_code):
            return {k: v for k, v in self.__dict__.items() if k in tf}

        translations = self.translations or {}

        if translations:
            translations = translations.get(language_code, {})
            return {k: v for k, v in translations.items() if v and k in tf}

        return {}

    def save(self, *args, **kwargs):
        language_code = self._language_code
        self.reset_language()

        if not self.translations:
            self.translations = dict()

        super(TranslatableModel, self).save(*args, **kwargs)

        self.language(language_code)

    class Meta:
        abstract = True
