from celery import shared_task
from apps.models import WebApp, Environment, Instance, DeploymentLogs
from apps.aws.instance import create_ec2_instance
from .remote_deploy import deploy_to_ec2
import time

@shared_task(bind=True)
def deploy_webapp_task(self, webapp_id):
    webapp = WebApp.objects.get(id = webapp_id)
    
    try:

        webapp.status = "deploying"
        webapp.save()


        github_org = webapp.githubOrg
        github_repo = webapp.githubRepo
        github_branch = webapp.githubBranch or "main"
        repo_url = f"https://github.com/{github_org}/{github_repo}.git"

        deployment_urls = []
        for env in webapp.environments.all():
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': f"Creating EC2 instance for {env.branch}",
                    'environment_id': env.id
                }
            )

            try:
                instance = create_ec2_instance(
                    {"region": webapp.region},
                    env
                )
            except Exception as e:
                DeploymentLogs.objects.create(
                    instance=None,
                    webapp=webapp,
                    message=f"EC2 creation failed: {str(e)}",
                    is_error=True
                )
                raise

            time.sleep(60)

            self.update_state(
                state='PROGRESS',
                meta={
                    'status': f"Deploying to {instance.publicId}",
                    'instance_id': instance.id
                }
            )

            if not instance.publicId:
                instance.status = "failed"
                instance.save()
                raise ValueError(f"EC2 instance {instance.id} has no public IP")

            self.update_state(
                state='PROGRESS',
                meta={'status': f"Deploying to {instance.publicId}"}
            )

            env_vars = {var.key: var.value for var in env.variables.all()}

            try:
                success = deploy_to_ec2(
                    instance_id=instance.publicId,
                    repo_url=repo_url,
                    port=env.port or 3000,
                    branch=env.branch or github_branch,
                    env_vars=env_vars,
                    template=webapp.template
                )
                if not success:
                    instance.status = "deployment_failed"
                    instance.save()
                    raise Exception(f"Deployment failed for {instance.publicId}")
                
                deployment_urls.append(f"http://{instance.publicId}:{env.port or 3000}")
                

                DeploymentLogs.objects.create(
                    instance=instance,
                    message=f"Deployment completed successfully to {instance.publicId}"
                )

            except Exception as e:
                instance.status = "failed"
                instance.save()
                DeploymentLogs.objects.create(
                    instance=instance,
                    message=f"Deployment error: {str(e)}",
                    is_error=True
                )
                raise

            webapp.status = "active"
            webapp.deployment_urls = deployment_urls
            webapp.save()

            return {
                'webapp_id': webapp.id,
                'status': 'active',
                'urls': deployment_urls,
                'message': 'Deployment completed successfully'
            }
        
    except Exception as e:
        webapp.status = "failed"
        webapp.save()
        DeploymentLogs.objects.create(
            webapp=webapp,
            message=f"Deployment task failed: {str(e)}",
            is_error=True
    )
        webapp.status = "failed"
        webapp.save()
        
        
        raise self.retry(exc=e, countdown=60, max_retries=3)