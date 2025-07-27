import requests
import time
from apps.models import Instance, DeploymentLogs
from celery import shared_task
from .recovery import recover_instance

def check_instance_health(instance):

    try:
        #  SSH access  :-
        if not verify_ssh_connection(instance.publicId):
            return False

        # application endpoint
        url = f"http://{instance.publicId}:{instance.environment.port}"
        try:
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False
            
    except Exception as e:
        DeploymentLogs.objects.create(
            instance=instance,
            message=f"Health check failed: {str(e)}",
            is_error=True
        )
        return False



def verify_ssh_connection(public_ip):


    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((public_ip, 22))
    return result == 0



def monitor_deployments():
    
    @shared_task
    def check_all_instances():
        instances = Instance.objects.filter(status="running")
        for instance in instances:
            if not check_instance_health(instance):
                instance.status = "unhealthy"
                instance.save()
                
                recover_instance.delay(instance.id)