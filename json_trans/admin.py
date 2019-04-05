from django.contrib import admin
from django.conf import settings
from django.utils.translation import get_language


class TranslatableModelAdmin(admin.ModelAdmin):

    def get_fields(self, request, obj=None):
        gf = super().get_fields(request, obj)
        for f in self.form().translatable_fields:
            if f[0] not in gf:
                gf.append(f[0])
            self.form.declared_fields.update({f[0]: f[1]})
        return gf

    def prepare_extra_context(self, extra_context):
        extra_context = extra_context or {}

        _lang = get_language()
        if _lang == settings.LANGUAGE_CODE:
            extra_context['status'] = True

        extra_context['LANGUAGES'] = settings.LANGUAGES

        return extra_context

    def add_view(self, request, form_url='', extra_context=None):
        return super().add_view(request, form_url, self.prepare_extra_context(extra_context))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return super().change_view(request, object_id, form_url, self.prepare_extra_context(extra_context))
