from django.urls import path
from .views import webapp_handler, check_deployment_status

urlpatterns = [
    path("webapp/", webapp_handler),
    path('api/deployments/status/<str:task_id>/', check_deployment_status),

]
