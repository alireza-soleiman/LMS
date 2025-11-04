from django.contrib import admin
from .models import Project, Stakeholder, Problem , MasterIndicator, Indicator

# This "registers" our models, making them visible and manageable
# in the admin interface.
admin.site.register(Project)
admin.site.register(Stakeholder)
admin.site.register(Problem)


@admin.register(MasterIndicator)
class MasterIndicatorAdmin(admin.ModelAdmin):
    list_display = ("category", "criterion", "name", "unit")
    search_fields = ("name", "criterion", "description")
    list_filter = ("category",)

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "criterion", "accepted", "added_by_student")
    search_fields = ("name", "criterion", "description", "project__title")
    list_filter = ("accepted", "project", "category")
