from django.utils.translation import ugettext_lazy as _


class NonTranslatableFieldError(Exception):
    def __init__(self, fieldname):
        self.fieldname = fieldname
        message = _('{} is not in translatable fields').format(fieldname)
        super(NonTranslatableFieldError, self).__init__(message)
