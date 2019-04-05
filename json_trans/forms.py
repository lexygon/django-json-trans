import copy
from collections import OrderedDict

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.models import InlineForeignKeyField
from django.utils.translation import get_language

LANGUAGES = OrderedDict(settings.LANGUAGES)
DEFAULT_LANGUAGE_CODE = settings.LANGUAGE_CODE


def construct_instance(form, instance, fields=None, exclude=None, translatable_fields=None, lang=DEFAULT_LANGUAGE_CODE):
    """
    Construct and return a model instance from the bound ``form``'s
    ``cleaned_data``, but do not save the returned instance to the database.
    """
    from django.db import models
    opts = instance._meta

    if not translatable_fields:
        translatable_fields = []

    cleaned_data = form.cleaned_data
    file_field_list = []
    for f in opts.fields:
        if not f.editable or isinstance(f, models.AutoField) or f.name not in cleaned_data:
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        # Leave defaults for fields that aren't in POST data, except for
        # checkbox inputs because they don't appear in POST data if not checked.
        if f.has_default() and form[f.name].field.widget.value_omitted_from_data(form.data, form.files, form.add_prefix(f.name)):
            continue
        # Defer saving file-type fields until after the other fields, so a
        # callable upload_to can use the values from other fields.
        if isinstance(f, models.FileField):
            file_field_list.append(f)
        else:
            if f.attname not in translatable_fields:
                f.save_form_data(instance, cleaned_data[f.name])

    for f in file_field_list:
        f.save_form_data(instance, cleaned_data[f.name])

    return instance


class TranslatableModelFormMixin(object):
    _mode = 'single'  # single or multi

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_language = get_language()
        self.translatable_field_names = self._meta.model._meta.translatable_fields

        self.translatable_fields = []

        self.form_fields = copy.deepcopy(self.fields) or self._meta.model._meta.fields

        for name, field in self.form_fields.items():
            if name in self.translatable_field_names:
                if self._mode == 'multi':
                    for code, lang in LANGUAGES.items():
                        if code != DEFAULT_LANGUAGE_CODE:
                            new_field = copy.deepcopy(field)
                            new_field.required = False
                            new_field.name = f'{name}__trans__{code.replace("-", "_")}'
                            new_field.label = f'{field.label} ({LANGUAGES.get(code).upper()})'
                            new_field.widget.attrs['placeholder'] = name
                            self.translatable_fields.append((new_field.name, new_field))

                    self.fields[name].label += f' ({LANGUAGES.get(DEFAULT_LANGUAGE_CODE).upper()})'

        self.fields.update(self.translatable_fields)

    def get_translation_data(self):
        data = self.cleaned_data
        return {key: data[key] for key in data if '__trans__' in key}

    def get_single_translation_data(self):
        data = self.cleaned_data
        return {key: data[key] for key in data if key in self.translatable_field_names}

    def _post_clean(self):

        translatable_fields = self.get_translation_data() if self._mode == 'multi' else self.get_single_translation_data()

        for name, data in translatable_fields.items():
            if self._mode == 'multi':
                splitted_name = name.split('__trans__')
                lang_code = splitted_name[-1]
                field_name = splitted_name[0]

                self.instance.translate(lang_code, **{field_name: data})

            else:
                self.instance.translate(self.active_language, **{name: data})

        opts = self._meta

        exclude = self._get_validation_exclusions()

        for name, field in self.fields.items():
            if isinstance(field, InlineForeignKeyField):
                exclude.append(name)

        try:
            self.instance = construct_instance(self, self.instance, opts.fields, opts.exclude, translatable_fields, self.active_language)
        except ValidationError as e:
            self._update_errors(e)

        try:
            self.instance.full_clean(exclude=exclude, validate_unique=False)
        except ValidationError as e:
            self._update_errors(e)

        # Validate uniqueness if needed.
        if self._validate_unique:
            self.validate_unique()


class TranslatableModelForm(TranslatableModelFormMixin, ModelForm):

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')

        if instance:
            trans_data = self.set_translation_fields(instance)
            initial = kwargs.get('initial')
            if initial:
                initial.update(trans_data)
            else:
                kwargs['initial'] = trans_data

        super().__init__(*args, **kwargs)

    def set_translation_fields(self, instance):
        result = {}
        translations = instance.translations

        field_names = self._meta.fields

        if self._mode == 'multi':
            for field_name in field_names:
                if field_name in self.translatable_field_names:
                    for lang, lang_code in LANGUAGES.items():
                        try:
                            result[f'{field_name}__trans__{lang_code}'] = translations.get(lang_code).get(field_name)
                        except AttributeError:
                            # result[f'{field_name}__{lang_code}'] = None
                            pass

        return result


class SingleLanguageModelForm(TranslatableModelForm):
    def clean(self):
        data = super(SingleLanguageModelForm, self).clean()
        return data


class MultiLanguageModelForm(TranslatableModelForm):
    _mode = 'multi'
