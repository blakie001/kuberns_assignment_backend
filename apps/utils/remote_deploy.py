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
