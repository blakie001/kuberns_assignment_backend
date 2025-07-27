import boto3
import io
import json
import paramiko

def get_ssh_key_from_aws():
    
    print("ssh key fetching ")
    secret_name = "kuberns/ssh/private_key"
    region_name = "us-east-1"

    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)

    raw_key = response["SecretString"]

    if raw_key.startswith("{"):
        import json
        raw_key = json.loads(raw_key)["EC2_SSH_PRIVATE_KEY"]

    key_stream = io.StringIO(raw_key)
    private_key = paramiko.RSAKey.from_private_key(key_stream)

    return private_key
