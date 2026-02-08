# Deployment

Deployment strategies, infrastructure setup, and production configuration.

## Deployment Options

### Phase 1: Simple Hosting (Current)

**Platforms:**
- Railway
- Render
- Fly.io
- DigitalOcean App Platform
- Heroku

**Characteristics:**
- Single instance
- Socket Mode (no public URL needed)
- SQLite storage
- Environment variables
- $5-20/month

### Phase 2: AWS Lambda (Planned)

**Infrastructure:**
- AWS Lambda functions
- API Gateway / Lambda Function URLs
- DynamoDB for token storage
- AWS Secrets Manager
- CloudWatch logs

**Characteristics:**
- Serverless
- Auto-scaling
- Pay per request
- HTTP mode (webhooks)
- Production-grade

## Railway Deployment

### Setup

1. **Create Railway account:** https://railway.app

2. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

3. **Initialize project:**
   ```bash
   railway init
   railway link
   ```

4. **Configure environment:**
   ```bash
   # Set variables via CLI
   railway variables set REDDIT_CLIENT_ID=xxx
   railway variables set REDDIT_CLIENT_SECRET=xxx
   # ... set all required variables

   # Or upload .env file
   railway variables set --env-file .env
   ```

5. **Deploy:**
   ```bash
   railway up
   ```

### Configuration Files

**railway.json:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python -m reddit_listener",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

**Procfile (alternative):**
```
worker: python -m reddit_listener
```

### Monitoring

```bash
# View logs
railway logs

# Check status
railway status
```

## Render Deployment

### Setup

1. **Create Render account:** https://render.com

2. **Create new Web Service:**
   - Connect GitHub repository
   - Or deploy from Docker image

3. **Configure service:**
   - **Build Command:** `pip install -e .`
   - **Start Command:** `python -m reddit_listener`
   - **Environment:** Python 3.9+

4. **Set environment variables:**
   - Add all required variables in Render dashboard
   - Or use `.env` file upload

### render.yaml

```yaml
services:
  - type: worker
    name: reddit-listener
    env: python
    buildCommand: pip install -e .
    startCommand: python -m reddit_listener
    envVars:
      - key: REDDIT_CLIENT_ID
        sync: false
      - key: REDDIT_CLIENT_SECRET
        sync: false
      - key: SLACK_BOT_TOKEN
        sync: false
      - key: SLACK_APP_TOKEN
        sync: false
      - key: SLACK_SIGNING_SECRET
        sync: false
      - key: OPENROUTER_API_KEY
        sync: false
      - key: ENCRYPTION_KEY
        sync: false
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY src/ ./src/

# Run application
CMD ["python", "-m", "reddit_listener"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  reddit-listener:
    build: .
    env_file: .env
    restart: unless-stopped
    volumes:
      - ./data:/app/data  # For SQLite database
```

### Commands

```bash
# Build image
docker build -t reddit-listener .

# Run container
docker run -d --env-file .env reddit-listener

# With docker-compose
docker-compose up -d

# View logs
docker logs -f <container_id>
```

## AWS Lambda Deployment (Phase 2)

### Architecture

```
Slack → API Gateway → Lambda → DynamoDB
                       ↓
                   OpenRouter/Reddit APIs
```

### Lambda Function

**handler.py:**
```python
import json
from reddit_listener.slack.app import app
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

SlackRequestHandler.clear_all_log_handlers()
handler = SlackRequestHandler(app=app)

def lambda_handler(event, context):
    """AWS Lambda handler"""
    return handler.handle(event, context)
```

### Deployment Package

```bash
# Create deployment package
pip install -t package/ -r requirements.txt
cd package
zip -r ../lambda.zip .
cd ..
zip -g lambda.zip handler.py
zip -r lambda.zip src/

# Upload to Lambda
aws lambda update-function-code \
  --function-name reddit-listener \
  --zip-file fileb://lambda.zip
```

### Lambda Configuration

**Runtime settings:**
- **Runtime:** Python 3.9
- **Handler:** handler.lambda_handler
- **Memory:** 512 MB (adjust based on usage)
- **Timeout:** 300 seconds (5 min max)
- **Environment:** Set all required variables

**Layers (optional):**
```bash
# Create layer for dependencies
mkdir python
pip install -t python/ -r requirements.txt
zip -r layer.zip python/

# Upload layer
aws lambda publish-layer-version \
  --layer-name reddit-listener-deps \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.9
```

### API Gateway Setup

1. Create REST API or HTTP API
2. Create POST route: `/slack/events`
3. Integrate with Lambda function
4. Configure authorization (none, Slack verifies)
5. Deploy API
6. Update Slack webhook URL

### DynamoDB Setup

```python
import boto3

dynamodb = boto3.resource('dynamodb')

# Create table
table = dynamodb.create_table(
    TableName='reddit-listener-tokens',
    KeySchema=[
        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
    ],
    AttributeDefinitions=[
        {'AttributeName': 'user_id', 'AttributeType': 'S'}
    ],
    BillingMode='PAY_PER_REQUEST'
)
```

### Secrets Manager

```python
import boto3
import json

def get_secrets():
    """Retrieve secrets from AWS Secrets Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='reddit-listener/prod')
    return json.loads(response['SecretString'])

# Use in Lambda
secrets = get_secrets()
REDDIT_CLIENT_SECRET = secrets['reddit_client_secret']
```

### CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Reddit Listener Infrastructure

Resources:
  LambdaFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: reddit-listener
      Runtime: python3.9
      Handler: handler.lambda_handler
      Code:
        S3Bucket: my-deployment-bucket
        S3Key: lambda.zip
      MemorySize: 512
      Timeout: 300
      Environment:
        Variables:
          STAGE: prod

  TokensTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: reddit-listener-tokens
      KeySchema:
        - AttributeName: user_id
          KeyType: HASH
      AttributeDefinitions:
        - AttributeName: user_id
          AttributeType: S
      BillingMode: PAY_PER_REQUEST

  ApiGateway:
    Type: AWS::ApiGatewayV2::Api
    Properties:
      Name: reddit-listener-api
      ProtocolType: HTTP

  # ... more resources
```

## Environment Configuration

### Production Environment Variables

```bash
# Reddit API
REDDIT_CLIENT_ID=<production_client_id>
REDDIT_CLIENT_SECRET=<production_secret>
REDDIT_USER_AGENT=reddit_listener:v1.0.0 (by /u/your_username)
REDDIT_REDIRECT_URI=https://your-domain.com/callback

# Slack API
SLACK_BOT_TOKEN=xoxb-<production_token>
SLACK_APP_TOKEN=xapp-<production_token>  # For Socket Mode
SLACK_SIGNING_SECRET=<production_secret>

# OpenRouter API
OPENROUTER_API_KEY=<production_key>

# Security
ENCRYPTION_KEY=<strong_production_key>

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Staging Environment

```bash
# Same structure but with staging credentials
ENVIRONMENT=staging
LOG_LEVEL=DEBUG
```

## Monitoring & Logging

### Application Logging

```python
import logging
import sys

def setup_logging(environment: str):
    """Configure logging for deployment environment"""
    level = logging.DEBUG if environment == 'development' else logging.INFO
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Add file handler for non-Lambda environments
    if environment != 'lambda':
        handlers.append(logging.FileHandler('reddit_listener.log'))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
```

### CloudWatch (AWS)

```python
import watchtower

logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group='reddit-listener',
    stream_name='prod'
))
```

### Metrics

```python
import time

class MetricsCollector:
    """Collect application metrics"""
    
    def __init__(self):
        self.metrics = {
            'requests_total': 0,
            'requests_success': 0,
            'requests_failed': 0,
            'avg_response_time': 0
        }
    
    def record_request(self, success: bool, duration: float):
        self.metrics['requests_total'] += 1
        if success:
            self.metrics['requests_success'] += 1
        else:
            self.metrics['requests_failed'] += 1
        
        # Update average
        total = self.metrics['requests_total']
        current_avg = self.metrics['avg_response_time']
        self.metrics['avg_response_time'] = (
            (current_avg * (total - 1) + duration) / total
        )
```

## Health Checks

### Endpoint

```python
from slack_bolt import App

app = App(token=SLACK_BOT_TOKEN)

@app.event("app_mention")
async def handle_health_check(event, say):
    """Health check via Slack"""
    if "health" in event['text'].lower():
        await say("✅ Bot is healthy and running!")
```

### External Monitoring

Use services like:
- UptimeRobot
- Pingdom
- AWS CloudWatch Alarms

## Backup & Recovery

### SQLite Database Backup

```bash
# Create backup
sqlite3 tokens.db ".backup tokens_backup.db"

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
sqlite3 tokens.db ".backup backups/tokens_$DATE.db"
find backups/ -mtime +30 -delete  # Delete backups older than 30 days
```

### DynamoDB Backup

```python
import boto3

def backup_dynamodb_table(table_name: str):
    """Create on-demand backup of DynamoDB table"""
    client = boto3.client('dynamodb')
    response = client.create_backup(
        TableName=table_name,
        BackupName=f'{table_name}-backup-{int(time.time())}'
    )
    return response['BackupDetails']['BackupArn']
```

## Scaling Considerations

### Vertical Scaling
- Increase Lambda memory (up to 10 GB)
- Increase container resources
- Upgrade hosting plan

### Horizontal Scaling
- Multiple Lambda instances (automatic)
- DynamoDB auto-scaling
- OpenRouter rate limits (upgrade plan)

### Performance Optimization
- Cache Reddit API responses (Redis)
- Optimize LLM prompts (reduce tokens)
- Batch operations where possible
- Connection pooling

## Cost Estimation

### Railway/Render (Phase 1)
- **Hosting:** $10-20/month
- **Total:** ~$15/month (with usage)

### AWS Lambda (Phase 2)
- **Lambda:** $0.20 per 1M requests + compute time
- **DynamoDB:** $0.25 per GB storage + requests
- **API Gateway:** $1 per 1M requests
- **Estimated:** $10-50/month (depends on usage)

### API Costs
- **Reddit API:** Free (with rate limits)
- **OpenRouter:** ~$0.008 per query
- **Slack API:** Free

## Security Checklist

- [ ] HTTPS enabled
- [ ] Environment variables secured
- [ ] API keys rotated from defaults
- [ ] Encryption key generated securely
- [ ] Minimal IAM permissions (AWS)
- [ ] Secrets Manager configured (AWS)
- [ ] Logging sanitized (no secrets)
- [ ] Rate limiting enabled
- [ ] Monitoring and alerts configured
- [ ] Backup strategy in place

## Troubleshooting Deployment

See [Troubleshooting Guide](troubleshooting.md) for common deployment issues.

## Next Steps

- Review [Security](security.md) for production hardening
- Set up [Monitoring](troubleshooting.md#monitoring)
- Configure [Backups](#backup--recovery)
- Test [Disaster Recovery](#backup--recovery)
