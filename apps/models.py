from django.db import models

class WebApp(models.Model):

    ttl_days = models.IntegerField(
        default=7
    )

    REGION_CHOICES=[
        ('us-east-1', 'US East (N. Virginia)'),
        ('us-west-1', 'US West (N. California)'),
        ('eu-west-1', 'EU (Ireland)'),
        ('ap-southeast-1', 'Asia Pacific (Singapore)'),
    ]
    TEMPLATE_CHOICES = [
        ('react', 'React'),
        ('vue', 'Vue'),
        ('angular', 'Angular'),
        ('node', 'Node.js'),
        ('django', 'Django'),
        ('flask', 'Flask'),
    ]
    PLAN_CHOICES = [
        ('starter', 'Starter'),
        ('pro', 'Pro'),
    ]
    
    name = models.CharField(
        max_length=100,
        unique=True
    )
    owner = models.CharField(
        max_length=100
    )
    region = models.CharField(
        max_length=100,
        choices=REGION_CHOICES,
        default='us-east-1'
    )
    template = models.CharField(
        max_length=100,
        choices=TEMPLATE_CHOICES
    )
    plan = models.CharField(
        max_length=100,
        choices=PLAN_CHOICES,
        default='starter'
    )
    githubOrg = models.CharField(
        max_length=255,
    )
    githubRepo = models.CharField(
        max_length=255,
    )
    githubBranch = models.CharField(
        max_length=255,
        default='main'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class Environment(models.Model):
    webapp = models.ForeignKey(
        WebApp,
        on_delete=models.CASCADE,
        related_name='environments'
        # max_length=100,
    )
    branch = models.CharField(
        max_length=100,
        default='main'
    )
    port = models.IntegerField(
        default=3000
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def __str__(self):
        return f"{self.webapp.name} - {self.branch}"

class EnvironmentVariables(models.Model):
    environment = models.ForeignKey(
        Environment,
        on_delete=models.CASCADE,
        related_name='variables'
    )
    key = models.CharField(
        max_length=100
    )
    value = models.CharField(
        max_length=500
    )

    def __str__(self):
        return f"{self.key}={self.value}"

class Instance(models.Model):
    is_active = models.BooleanField(
        default=True
    )

    security_group_id = models.CharField(
        max_length=100,
        blank=True
    )

    last_health_check = models.DateTimeField(
        null=True
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('deploying', 'Deploying'),
        ('active', 'Active'),
        ('failed', 'Failed')
    ]
    environment = models.ForeignKey(
        'Environment',
        on_delete=models.CASCADE,
        related_name='instances',
    )
    cpu = models.IntegerField()
    memory = models.IntegerField()
    storage = models.IntegerField()
    status = models.CharField(
        max_length=255,
        choices=STATUS_CHOICES,
        default= 'pending',
    )
    awsInstanceId = models.CharField(
        max_length=255,
    )
    publicId = models.CharField(
        max_length=255
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    def __str__(self):
        return f"{self.environment.webapp.name} - {self.environment.branch}"

    
class DeploymentLogs(models.Model):
    STATUS_CHOICES = [
        ('created', "Created"),
        ('provisioning', "Provisioning"),
        ('configuring', 'Configuring'),
        ('deploying', "Deploying"),
        ('completed', "Completed"),
        ('failed', 'Failed')
    ]
    instance = models.ForeignKey(
        'Instance',
        on_delete=models.CASCADE,
        null=True,
        related_name='deployementlogs'
    )
    webapp = models.ForeignKey(
        'WebApp',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    status = models.CharField(
        choices=STATUS_CHOICES,
        max_length=100
    )
    message = models.CharField(
        max_length=255
    )
    is_error = models.BooleanField(
        default=False
    )
    created_at = models.DateTimeField(
        auto_now_add= True
    )
    
    def __str__(self):
        return f"{self.timestamp} - {self.message[:50]}"