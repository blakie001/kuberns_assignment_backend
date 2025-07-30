from .aws_config import AWSService
from apps.models import Instance, DeploymentLogs
import time


def create_security_group(ec2_client, group_name):
    try:
        
        existing = ec2_client.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [group_name]}]
        )
        if existing['SecurityGroups']:
            return existing['SecurityGroups'][0]['GroupId']
            
            
        response = ec2_client.create_security_group(
            GroupName=group_name,
            Description='Webapp security group'
        )
        sg_id = response['GroupId']
        
        
        ec2_client.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 3000, 'ToPort': 3000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ]
        )
        return sg_id
        
    except Exception as e:
        print(f"Security group error: {str(e)}")
        raise
    


def create_ec2_instance(instance_data, environment_obj):

    aws = AWSService()

    ec2 = aws.get_ec2_client(instance_data["region"])

    try:

        sg_id = create_security_group(ec2, f"webapp-{environment_obj.id}-sg")

        response = ec2.run_instances(
            ImageId = "ami-0f918f7e67a3323f0",
            InstanceType = 't2.micro',
            MinCount = 1,
            MaxCount = 1,
            KeyName='react',
            SecurityGroupIds=[sg_id],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f"webapp-{environment_obj.id}"},
                        {'Key': 'Environment', 'Value': str(environment_obj.id)}
                    ]
                }
            ],
        )
            # UserData=f"""#!/bin/bash
            # apt-get update -y
            # apt-get install -y awscli
            # """



        instance = response["Instances"][0]
        instance_id = instance["InstanceId"]

        new_instance = Instance.objects.create(
            environment = environment_obj,
            cpu = 1,
            memory = 1,
            storage = 8,
            awsInstanceId = instance_id,
            publicId = "",
            status = "deploying",
            is_active = True,
            security_group_id=sg_id
        )

        DeploymentLogs.objects.create(
            instance = new_instance,
            webapp = environment_obj.webapp,
            message = f"EC2 Instance {instance_id} created",
            is_error = False
        )


        waiter = ec2.get_waiter("instance_running")
        waiter.wait(InstanceIds = [instance_id])

        print("Instance is running, waiting for public IP...")

        public_ip = None
        for _ in range(30):
            desc = ec2.describe_instances(InstanceIds=[instance_id])
            instance_data = desc["Reservations"][0]["Instances"][0]
            public_ip = instance_data.get("PublicIpAddress")

            if public_ip:
                break
            time.sleep(5)

        if not public_ip:
            raise Exception("Failed to fetch Public IP after retries.")


        new_instance.publicId = public_ip
        new_instance.status = "Running"
        new_instance.save()

        time.sleep(45)

        return new_instance
    
    except Exception as error:
        print("Error Creating Instance", str(error))
        if 'new_instance' in locals():
            new_instance.status = "failed"
            new_instance.save()
        raise error
    
