from rest_framework import serializers
from .models import WebApp, Environment, EnvironmentVariables, Instance, DeploymentLogs
from .aws.instance import create_ec2_instance

class EnvironmentVariablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentVariables
        
        fields = ["key", "value"]

class EnvironmentSerializer(serializers.ModelSerializer):
    variables = EnvironmentVariablesSerializer(many = True, required = False)

    class Meta:
        model = Environment
        fields = ["branch", "port", "variables"]

class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instance
        fields = ["cpu", "memory", "storage", "status", "awsInstanceId", "publicId"]


class DeploymentLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeploymentLogs
        fields = ["status", "message", "created_at"]


class WebAppSerializer(serializers.ModelSerializer):
    environments = EnvironmentSerializer(many = True)

    class Meta:
        model = WebApp
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'owner']

    def create(self, validate_data):
        environment_data = validate_data.pop("environments")
        webapp = WebApp.objects.create(**validate_data)

        for env_data in environment_data:
            variable_data = env_data.pop("variables", [])
            environment = Environment.objects.create(webapp = webapp, **env_data)

            for var_data in variable_data:
                EnvironmentVariables.objects.create(environment = environment, **var_data)
            

            instance_data = {
                "region" : "us-east-1"
            }
            create_ec2_instance(instance_data, environment)
                
        return webapp
