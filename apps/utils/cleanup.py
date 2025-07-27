import boto3
from apps.models import Instance
from django.utils import timezone
from datetime import timedelta


def terminate_expired_instances():
    
    expired_instances = Instance.objects.filter(
        created_at__lte=timezone.now() - timedelta(days=7),
        is_active=True
    )
    
    for instance in expired_instances:
        try:
            ec2 = boto3.client('ec2', region_name=instance.environment.webapp.region)
            ec2.terminate_instances(InstanceIds=[instance.awsInstanceId])
            
            if instance.security_group_id:
                try:
                    ec2.delete_security_group(GroupId=instance.security_group_id)
                except:
                    pass
                    
            instance.is_active = False
            instance.save()
            
        except Exception as e:
            print(f"Failed to terminate {instance.awsInstanceId}: {str(e)}")