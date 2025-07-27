import paramiko
import time
from io import StringIO

def execute_ssh_commands(ssh, commands, repo_name=None):
    for cmd in commands:
        try:
            print(f"Executing: {cmd[:100]}...")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                error = stderr.read().decode()
                output = stdout.read().decode()
                if ("pm2 startup" in cmd and "already inited" in error) or \
                    ("pm2 startup" in cmd and "command not found" in error):
                        print("PM2 already initialized or missing (non-critical)")
                        continue
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
        "sudo apt update -y",
        "sudo apt install -y curl",
        "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -",
        "sudo apt install -y nodejs git build-essential",
        "sudo npm install -g pm2 serve",
        "node -v",
        "npm -v",
        "pm2 --version",
        "serve --version"
    ]
    
    if not execute_ssh_commands(ssh, setup_commands, repo_name):
        return False

    build_commands = [
        f"[ -d {repo_name} ] && rm -rf {repo_name} || echo 'No existing directory'",
        f"git clone -b {branch} {repo_url} {repo_name}",
        f"cd {repo_name} && npm install",
        f"cd {repo_name} && npm run build",
        f"cd {repo_name} && ls -la build/"  # Verify build folder exists
    ]
    
    if not execute_ssh_commands(ssh, build_commands, repo_name):
        return False

    # Create environment variables if provided
    if env_vars:
        env_str = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
        create_env = f"echo '{env_str}' > {repo_name}/.env"
        if not execute_ssh_commands(ssh, [create_env], repo_name):
            return False

    # Create a startup script for the React app
    startup_script = f"""#!/bin/bash
cd /home/ubuntu/{repo_name}
npx serve -s build -l {port}
"""
    
    script_commands = [
        f"echo '{startup_script}' > /home/ubuntu/start-react-app.sh",
        "chmod +x /home/ubuntu/start-react-app.sh"
    ]
    
    if not execute_ssh_commands(ssh, script_commands, repo_name):
        return False

    pm2_commands = [
        "pm2 delete all || echo 'No existing processes to delete'",
        "sudo chown -R ubuntu:ubuntu /home/ubuntu/.pm2",
        
        # Method 1: Try using the startup script
        "pm2 start /home/ubuntu/start-react-app.sh --name react-app",
        
        "sleep 10",  # Give it time to start
        "pm2 list",
        f"pm2 logs react-app --lines 20",
        
        # Check what's listening
        f"netstat -tlnp | grep :{port}",
        f"lsof -i :{port} || echo 'Port {port} not in use'",
        
        # Test the connection
        f"curl -I --connect-timeout 15 http://localhost:{port}/ || echo 'Method 1 failed'",
    ]
    
    success = execute_ssh_commands(ssh, pm2_commands, repo_name)
    
    # If Method 1 failed, try Method 2
    if not success:
        print("Method 1 failed, trying Method 2...")
        alternative_commands = [
            "pm2 delete all || echo 'No processes to delete'",
            
            # Method 2: Direct command approach
            f"cd {repo_name} && pm2 start --name react-app -- npx serve -s build -l {port}",
            
            "sleep 10",
            "pm2 list",
            f"pm2 logs react-app --lines 20",
            f"netstat -tlnp | grep :{port}",
            f"curl -I --connect-timeout 15 http://localhost:{port}/ || echo 'Method 2 failed'",
        ]
        
        success = execute_ssh_commands(ssh, alternative_commands, repo_name)
    
    # If Method 2 failed, try Method 3
    if not success:
        print("Method 2 failed, trying Method 3...")
        final_commands = [
            "pm2 delete all || echo 'No processes to delete'",
            
            # Method 3: Use ecosystem file
            f"""cat > {repo_name}/ecosystem.config.js << 'EOF'
module.exports = {{
  apps: [{{
    name: 'react-app',
    script: 'npx',
    args: 'serve -s build -l {port}',
    cwd: '/home/ubuntu/{repo_name}',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {{
      NODE_ENV: 'production'
    }}
  }}]
}};
EOF""",
            
            f"cd {repo_name} && pm2 start ecosystem.config.js",
            
            "sleep 10",
            "pm2 list",
            f"pm2 logs react-app --lines 20",
            f"netstat -tlnp | grep :{port}",
            f"curl -I --connect-timeout 15 http://localhost:{port}/ || echo 'All methods failed'",
        ]
        
        success = execute_ssh_commands(ssh, final_commands, repo_name)
    
    # Save PM2 configuration if any method succeeded
    if success:
        save_commands = [
            "pm2 save",
            "sudo pm2 startup systemd -u ubuntu --hp /home/ubuntu || echo 'PM2 startup failed (may already exist)'"
        ]
        execute_ssh_commands(ssh, save_commands, repo_name)
    
    return success


def verify_deployment(ssh, port):
    verification_commands = [
        "pm2 list",
        f"pm2 logs react-app --lines 30",
        f"netstat -tlnp | grep :{port}",
        "ps aux | grep serve",
        f"curl -v --connect-timeout 15 http://localhost:{port}/ || echo 'Service not responding'",
        
        # System resources
        "free -h",
        "df -h",
        
        # PM2 status
        "pm2 status",
        "sudo systemctl status pm2-ubuntu.service --no-pager || echo 'PM2 service not found'",
        
        # Check if build folder exists and has content
        "ls -la */build/ || echo 'No build folder found'"
    ]
    return execute_ssh_commands(ssh, verification_commands)


def deploy_to_ec2(instance_id, repo_url, port, branch="main", env_vars={}, template="react"):
    print("<===| DEPLOY EC2 Started |===>")
    print(f"Target EC2: {instance_id}")
    print(f"Repo: {repo_url} and b = {branch}")
    print(f"Port: {port} | Env vars: {len(env_vars)} | Template: {template}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    private_key_string = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAtHlaon6fPLwULbLjrexqbEQvIFjo4BaA+4liC/xWXiHOkWAh
b6XdCYZT9+9QytpmTrlnY+WU/XCKGVs5iDobpfXHESqbMAufTMAXsjnsBxnzXk7W
+FsBfaKGgU938gfCp+nZpY7Ny/8Q5km9itVu0hNm+rmUPLqnyp4YMRVmmAuFzUjs
wfrD7NtcGKgZHLq1ie8Jy95HYxGstRyMfFa6p7rI2n5zYInDTMxowfikugqa+gk0
nXBGUTe8CwjPeNpzoKW9Uah1r6jy34odvnc2jyMxB1Qqk4xGZIbOWO44aBiiMy8m
lBsHPXbz+J1vgZEgaG9yQJCZ/gm0uR0CyjsW0QIDAQABAoIBAHJtc1MON8aZda3X
+9YdzQhiXwMCfH0Ap71UyS7SSqyagM/aBLk2kCRm4DyWp0JHIZEOqwhC26mpvlX/
akX+meMrJ5Gx0v2ukM1oCl49rXJ/OLh2AoUrppFTCDda/LEfzIMMmawIFGIgkkWB
QcWSOBbIqIWWPvAWZSbqAGq2p/sEWrjaTLkxr5ayDKkXlpU6jMF+fkwnplwFjK0x
7UXIB2va+Mb1OFMkBowAG+rNTE4p1q7cJ2hbUbV6wKzSetT85qbMaiJq36TuyDVN
yfiKBXF0a+KgVmxFRYD+/QiJRoa+QU76vOuzRh8fgdIx3crH4FfuWm966tNv0Kr0
7kPSiaUCgYEA2IJpg06be38/f3kgaHE2m/3CRXLN9e+JYGgCL1suBKyIVrOtahLi
nbIYVA8KBSQPTgu2bsbFnX+JIJEY3oR5D2LeCaOLWcq3HZ86xG7wzSqaAQTz81iO
s79eViuHRsX7ijiHUjaZgVQZG5BfpMQaiYRDmWFNq/Nsspoh5xdIXCcCgYEA1WRS
pwTLpyE1/Z0Ii565sVfpRT2E48jo0KrtqHjJ2gdhdha8otv1kEW5MEzHSTVhGkXC
LVGG8eGeAliOm9iqI/38CdC+WWYadN1nha3Cw1f+SkEHpc6Xz11KC7A/5XQGp9tu
rSYmYAOW2gRaG2sD5JYfM/LG1kVYs+k2O2qXOEcCgYEAngFup1kyt0oCOTFYqWAW
Dnl+0dga3yTVCPpevdi5GMghJ8UxBXyKzbMvdgkTsvTCBp8doHKHvY1Zsd6yW5Iq
F0R77mTgScNbJ88QwFKGgfRZN+05a5pxalR6sEBMFSZfkFv4xdL67BtHx4nxgvlq
tHlGLCWK3bZk2WMK4u9m63kCgYB75I1gTxZ2aH/SSXQGrBcf8eyLuNYI8kLJtBPb
tpVrMtHRIA5Rd+ew5epJMqqZxJYmDM5aRXVVxipZLlVOApN15iaJBFsfyHof09Qg
9uuXQuVu8yafi7z0NjOhaakPbTfYCTzO5tFs+WiCF/jA5ncSJl7jaFctXIHNot9L
y+0UTQKBgQCtjVdO7eL0cipqXcLCNcJYQf6OmQkd3oGWZDZHD01S+vipp7LfbXoE
bAsjDJjul9km+fjZAujv9iVXXDeD5MzwubUc6ajr649oMD0qte8q7nEpUOBOZIqy
rOhJ7p/yOtRnmVB7WtVDzY+nXfjghh1ipcV1kzxrI/E1Klb2GSuURA==
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
            print("[4/4] Verifying deployment...")
            success = verify_deployment(ssh, port)
        
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


# Quick diagnostic function you can call manually if needed
def diagnose_deployment_issue(instance_id, port, private_key_string):
    """Run this to diagnose why the deployment isn't working"""
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        private_key = paramiko.RSAKey.from_private_key(StringIO(private_key_string.strip()))
        ssh.connect(hostname=instance_id, username="ubuntu", pkey=private_key, timeout=30)
        
        diagnostic_commands = [
            "whoami",
            "pwd",
            "ls -la",
            "pm2 list",
            f"pm2 logs react-app --lines 50",
            "ps aux | grep serve",
            "ps aux | grep node",
            f"netstat -tlnp | grep :{port}",
            "netstat -tlnp | head -20",
            f"lsof -i :{port}",
            "ls -la */build/",
            f"curl -v http://localhost:{port}/",
            "free -h",
            "df -h"
        ]
        
        execute_ssh_commands(ssh, diagnostic_commands)
        
    except Exception as e:
        print(f"Diagnostic error: {str(e)}")
    finally:
        ssh.close()