from celery import Celery
from celery.schedules import crontab

app = Celery('apps')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'health-check-every-5-min': {
        'task': 'apps.utils.health_check.monitor_deployments',
        'schedule': crontab(minute='*/5'),
    },
    'cleanup-daily': {
        'task': 'apps.utils.cleanup.terminate_expired_instances',
        'schedule': crontab(hour=3, minute=0),  # Daily At 3AM
    },
}