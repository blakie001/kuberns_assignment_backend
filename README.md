EC2 Management Platform

A backend platform that automates EC2 instance provisioning, It includes automated background jobs for resource cleanup and usage tracking.

Tech Stack USed:
Backend	       -  Django (Python)
Database	     -  PostgreSQL
Task Queue	   -  Celery
Scheduler      -	Celery.schedules
Cloud Provider -	AWS EC2
Frontend       -  ReactJs


    Features :
    
    --> User Action:
            Create a WebApp + Environment via API.
            Trigger /deploy endpoint.
    
    --> Backend:
            Launch EC2.
            Connect via Paramiko.
            Setup env, Git pull, run app via PM2.
            Save deployment logs .
    
    --> Validation:
            curl localhost:<port> ensures the app is up.
            If failure, instance is terminated and status marked.
    
    --> Auto-Termination:
            Celery periodically checks for expired instances.
            Terminates them and updates status.
    



Api's :
POST : Create New WebApp  (/webapp)
GET : Get ALl WebApps     (/webapp)
GET :	Get logs of a deployed instance ( /api/instances/{id}/logs/)


Setup  :-

git clone github.com/blakie001/kuberns_assignment_backend
cd kuberns_assignment_backend
python3 -m venv venv
source venv/bin/activate

# Run Django
python manage.py migrate
python manage.py runserver

# Start Redis
redis-server

# Start Celery worker (2nd terminal)
celery -A kuberns worker --loglevel=info




Flow Summary :
User Input (GitHub Repo, Branch, Env's, Port, etc.)
    ↓
Validation (Serializer)
    ↓
Task Queued via Celery -> Redis (Message Broker)
    ↓
Celery Worker Consumes Task



Worker Flow : 
[1] Provision EC2 Instance (boto3)
    ↓
[2] Fetch SSH Private Key from AWS Secrets Manager
    ↓
[3] Create SSH Connection
    ↓
[4] Git Clone Repo + Install Deps + PM2 Setup
    ↓
[5] Schedule health check: curl -I http://localhost:{port}
        ↳ If success → Store DeploymentLogs (success)
        ↳ If failed  → Retry (Celery retry), Store Logs (failure)
    ↓
[6] Save instance metadata: public IP, instance ID, state, logs
    ↓
[7] Schedule periodic task to check and terminate expired instances (Celery Beat)
