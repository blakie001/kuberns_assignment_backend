from django.contrib import admin
from .models import WebApp, Environment, Instance, DeploymentLogs

admin.site.register(WebApp)
admin.site.register(Environment)
admin.site.register(Instance)
admin.site.register(DeploymentLogs)
