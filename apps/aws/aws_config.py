import boto3
from django.conf import settings


class AWSService:
    def __init__(self):
        self.aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
    
    def get_ec2_client(self, region):
        return boto3.client(
            "ec2",
            region_name = region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )