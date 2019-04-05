## django-json-trans

**This package is still on development stage, not ready for production !!!**

This package provides a lean approach to model translations for Django with PostgreSQL's lovely JSONBField.

Simple usage:

```
# settings.py

INSTALLED_APPS = [
    ...
    'json_trans',
    ...
]

This middleware only needed for translatable admin. Also you can use it in your other parts of project. 
MIDDLEWARE = [
    ...
    'json_trans.middleware.QueryParameterLocaleMiddleware', # django's LocaleMiddleware + ?lang= queries.
    ...
]

LANGUAGE_CODE = 'en-us'  # default language 

LANGUAGES = (  # available languages
    ('en-us', ugettext_lazy('English')),
    ('tr-tr', ugettext_lazy('Turkish')),
)

# models.py
from json_trans.models import TranslatableModel


class Product(TranslatableModel):
    field1 = models.CharField(max_length=255)
    field2 = models.CharField(max_length=255)
    
    class Meta:
        translatable_fields = ('field1', 'field2')
        
        
# create object        
product = Product.objects.create(field1='Field1', field2='Field2')
product.field1
# output is "Field1"

product.translate('lang-code', {'field1': 'Field1-other-lang'})
product.save()
product.field1
# output is Field1-other-lang

# forms.py
from json_trans.forms import SingleLanguageModelForm


class ProductForm(SingleLanguageModelForm):
    class Meta:
        model = Product
        fields = ('field1', 'field2')


# admin.py
from django.contrib import admin
from json_trans.admin import TranslatableModelAdmin


class BlogPostAdmin(TranslatableModelAdmin):
    form = PostAdminForm


admin.site.register(BlogPost, BlogPostAdmin)
```

## More docs will come.
