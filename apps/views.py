import os
import time
from .models import WebApp, Environment, Instance
from .serializers import WebAppSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from .aws.instance import create_ec2_instance
from .utils.remote_deploy import deploy_to_ec2
from .utils.celery_tasks import deploy_webapp_task

@api_view(['GET', 'POST'])
def webapp_handler(request):
    if request.method == 'POST':
        try:
            serializer = WebAppSerializer(data=request.data)
            if serializer.is_valid():
                webapp = serializer.save()


                task = deploy_webapp_task.delay(webapp.id)
                
                return Response({
                    "status": "deployment_started",
                    "webapp_id": webapp.id,
                    "task_id": task.id,
                    "check_status_url": f"/api/deployments/status/{task.id}/"
                }, status=status.HTTP_202_ACCEPTED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    elif request.method == 'GET':
        try:
            webapps = WebApp.objects.all()
            serializer = WebAppSerializer(webapps, many=True)
            return Response(serializer.data, status= status.HTTP_200_OK)
        except Exception as error:
            print("Error Fetching All Webapps", str(error))
            return Response({"error": str(error)}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)
        




@api_view(['GET'])
def check_deployment_status(request, task_id):
    from celery.result import AsyncResult
    task = AsyncResult(task_id)
    
    if task.state == 'FAILURE':
        return Response(
            {"status": "failed", "error": str(task.result)},
            status=status.HTTP_200_OK
        )
    
    return Response({
        "status": task.state,
        "progress": task.info.get('status', '') if task.state == 'PROGRESS' else None,
        "result": task.result if task.ready() else None
    })
