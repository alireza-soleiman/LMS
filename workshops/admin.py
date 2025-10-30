from django.contrib import admin
from .models import Project, Stakeholder, Problem

# This "registers" our models, making them visible and manageable
# in the admin interface.
admin.site.register(Project)
admin.site.register(Stakeholder)
admin.site.register(Problem)