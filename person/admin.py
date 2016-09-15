from django.contrib import admin

from parliament.models import Person


class PersonAdmin(admin.ModelAdmin):
    list_display = ('fullname', 'forename', 'surname', 'surname_prefix', 'initials', 'birthdate', 'wikidata_id')


admin.site.register(Person, PersonAdmin)