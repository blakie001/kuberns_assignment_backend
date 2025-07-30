import paramiko
import time
from io import StringIO

def execute_ssh_commands(ssh, commands, repo_name = None):
    for cmd in commands:
        try:
            print(f"Executing: {cmd[:100]}...")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                error = stderr.read().decode()
                output = stdout.read().decode()

                print(f"Command failed (status {exit_status}): {error[:200]}")
                print(f"Error: {error[:500]}")
                return False
            
            output = stdout.read().decode().strip()
            if output:
                print(f"Output: {output}...")
                
            time.sleep(1)
        except Exception as e:
            print(f"SSH command error: {str(e)}")
            return False
    return True


def deploy_react_app(ssh, repo_url, port, branch, env_vars, repo_name):
    setup_commands = [
        # "sudo apt update -y",
        # "sudo apt install -y curl",
        "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -",
        "sudo apt install -y nodejs",
        "node -v",
        "npm -v",
    ]
    
    if not execute_ssh_commands(ssh, setup_commands, repo_name):
        return False

    build_commands = [
        f"git clone -b {branch} {repo_url} {repo_name}",
        f"cd {repo_name} && npm install",
        f"cd {repo_name} && npm run build",
        f"cd {repo_name} && ls -la build/"
    ]
    
    if not execute_ssh_commands(ssh, build_commands, repo_name):
        return False

    if env_vars:
        env_str = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
        create_env = f"echo '{env_str}' > {repo_name}/.env"
        if not execute_ssh_commands(ssh, [create_env], repo_name):
            return False

    pm2_commands = [
        f"sudo npm install -g serve",
        f"cd {repo_name} && serve -s build -l {port}"
    ]
    
    success = execute_ssh_commands(ssh, pm2_commands, repo_name)
    print("=== React Deployment successful ===")



def deploy_to_ec2(instance_id, repo_url, port, branch="main", env_vars={}, template="react"):
    print("<===| DEPLOY EC2 Started |===>")
    print(f"Target EC2: {instance_id}")
    print(f"Repo: {repo_url} and b = {branch}")
    print(f"Port: {port} | Env vars: {len(env_vars)} | Template: {template}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    private_key_string = """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAxTBCn1tmsMvtGRRb5FkDhF4ne51gW/RSTithwt1F4Lww4my/
J8noWbnEQpKnh+rnfOAMgPd4LHNW6qUcH7/8SZ7am2bBNkUlcsUGDVC5uXU4PZYf
iqjV7kL4N1LPXg6XzzCwp+xF4/bKAWgYW6jOhaMcjUXPPYP+vjgmxcgA/zMY6rfO
Yu+1sgEcXWoQO2aImCu0F/uZcSnR+a21SkiP3f4Tr8WisvW1GLrk74eSeXzbzXrM
GmntLzAxDHctZqDCj0VfFruYbuVyT1fqKW+XX+Xsq+amSdHRwVxBxEYKNBYw5mgE
OQYUyr2as2yhPMCbKcUzsE+8IjSox+WtM8n8kQIDAQABAoIBAFPgbGZmta68f7Us
UM44AuP6POc7ETLsIVp435PJFaE7y7t0sHcXTotkFpSO105cYG1gzFDLc0XNJgqX
gvgKbSFPvgNeWQ9hqEVCg4mEbgvyTaL8yZvsp1s7B2RZCDYlFPQf7PTw7uXCIzkn
8zyB+J8lu85oBHhRPjnhnrSAl9P1Q/IXurD7Oo4kr6VM8ek7XSOogLWxy54pLMOV
tJMZ3cX6hu3LQFFR2ODlXnmynDXkfui3nysl4MwP5vcLO96y3t6IZEoW9sXQV5a7
b0+CINRgo6GtkEQk66PDKQDFKHRnjfFMJ9bo+gyS42yvTQT0co/GnvIsveIy6dxb
KD+LVzECgYEA6nfeXY7RZzGw+zabaOGmhEBF7mPmuGJCyW/Hd05Bt/yWNYDxo3gB
/70fXkRDXCpBZkxYoSBtEBVvf/Z2vLTIaNq89iLNOXstyL3tBYy9SopHazM7WWzo
bfwneI993JuqJrEKg6Ysv+o5/F/2Tzyn7YeRa8Ld2aQd8aRiGYulI30CgYEA10v6
2efHxLjoJmxBHHP+PSja9dStYbJkkX/EGPgCdswSBjNKHDm/WmtDOefyv7Qx7bzy
rGW+MrKedN9JUaDp50m9MlYBX0jfRmXjlAVYG91wXoka8zggbTas9Z3kL063tMwB
aXDH7gUn2czijAksnpI0Fik69/tUv1GH4yiTIaUCgYBqjKp6bapvcL9yibA6C0E2
nFarLK7uX4jmLWvBpchrqddA3SXyGVkfNHyKxA6wVWt+53bnUer+Ah+3UPNIcgcY
zz5LxCjq1DVMIjMR8JEczJYD+zYfP0SopovxV5PkqsC58H5MsTloxTIwpBM0kuXl
JVRKWjWi79fDteX2oeUbqQKBgEpkOZBTs0Y5MhYcr77aIY4WcNoim6o3TuKriCGs
iIVt7AhybngkSAdBKuB2Uf2FkP75m8yP91FjQLdXc+kdtdSyOQqMhzraXjPf/uvl
kNVIBYzUyRgjW6kBDHBuFyt1gqqZFx/M1XhcFbH/RoRmoyFDmXXS10pacKUO0epe
2b/1AoGAOc5rGWA8Jk0T/+y7lwmB1UsX+4pladWv+33dgz5OZ+bt3X81UdHB3WTR
28n0D56V/aKx+2Vg7oNK5tlAjcZvXvzAyLLF6MS8XOu+uOCBKqckoI9SdBvnq7HM
u2AfJQ4nnb0s7WmfeWzKrTKW6Rpx3sZIJ2ZMsRvh2PLSmVqAvPk=
-----END RSA PRIVATE KEY-----"""

    try:
        print("[1/4] Loading private key...")
        private_key = paramiko.RSAKey.from_private_key(StringIO(private_key_string.strip()))
        print("Private key loaded successfully")
    except Exception as e:
        print(f"Failed to load private key: {str(e)}")
        return False
    
    try:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"[2/4] Connecting to instance (attempt {attempt+1})...")
                ssh.connect(
                    hostname=instance_id,
                    username="ubuntu",
                    pkey=private_key,
                    timeout=30,
                    banner_timeout=30
                )
                print("SSH connection established")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"SSH connection failed (attempt {attempt+1}), retrying...")
                time.sleep(10)
        
        repo_name = repo_url.split('/')[-1].replace('.git', '')

        if template.lower() == "react":
            success = deploy_react_app(ssh, repo_url, port, branch, env_vars, repo_name)
        else:
            print(f"Unsupported template: {template}")
            return False
        
        if success:
            print("=== Deployment successful ===")
        else:
            print("=== Deployment failed ===")
            
        return success
        
    except Exception as e:
        print(f"Deployment error: {str(e)}")
        return False
    finally:
        ssh.close()
        print("SSH connection closed")
