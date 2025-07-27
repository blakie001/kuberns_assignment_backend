from .remote_deploy import deploy_to_ec2
from celery import shared_task
from ..aws.instance import create_ec2_instance

@shared_task
def recover_instance(instance_id):
    """Attempt to restart failed deployments"""
    from apps.models import Instance, DeploymentLogs
    
    instance = Instance.objects.get(id=instance_id)
    environment = instance.environment
    webapp = environment.webapp
    
    try:
        # restart app
        success = deploy_to_ec2(
            instance_id=instance.publicId,
            repo_url=f"https://github.com/{webapp.githubOrg}/{webapp.githubRepo}.git",
            port=environment.port,
            branch=environment.branch,
            template=webapp.template
        )
        
        if success:
            instance.status = "running"
            instance.save()
            return
            
            
        instance.status = "recovering"
        instance.save()
        
        new_instance = create_ec2_instance(
            {"region": webapp.region},
            environment
        )
        
        environment.instances.exclude(id=new_instance.id).update(is_active=False)
        
    except Exception as e:
        DeploymentLogs.objects.create(
            instance=instance,
            message=f"Recovery failed: {str(e)}",
            is_error=True
        )