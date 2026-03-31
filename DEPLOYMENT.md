# 🚀 Deployment Guide - Shift Scheduler SaaS

## Prerequisites

- Python 3.8+
- Neon PostgreSQL account & connection string
- Gunicorn (for production)
- Nginx (optional, recommended)

---

## Local Development

### 1. Clone and Setup

```bash
# Clone repository
git clone <your-repo>
cd shift-scheduler

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example
cp .env.example .env

# Edit .env with your database connection
nano .env
```

`.env` should contain:
```
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=your-dev-secret-key
```

### 3. Start Development Server

```bash
python web_interface.py
```

Server runs at: **http://localhost:5000**

---

## Production Deployment

### Option 1: VPS (DigitalOcean, Linode, etc.)

#### Step 1: Prepare Server

```bash
# SSH into your server
ssh root@your_server_ip

# Update system
apt update && apt upgrade -y

# Install Python and dependencies
apt install -y python3 python3-pip python3-venv nginx postgresql-client-common

# Create app directory
mkdir -p /var/www/shift-scheduler
cd /var/www/shift-scheduler

# Clone repository
git clone <your-repo> .
```

#### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

#### Step 3: Configure Environment

```bash
# Create .env in production
nano .env
```

Add:
```
DATABASE_URL=postgresql://production_user:strong_password@neon.postgres.database.azure.com/prod_db?sslmode=require
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=generate-strong-random-key
HOST=127.0.0.1
PORT=5000
```

Generate strong secret key:
```python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 4: Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/shift-scheduler.service
```

Paste:
```ini
[Unit]
Description=Shift Scheduler SaaS
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/shift-scheduler
Environment="PATH=/var/www/shift-scheduler/venv/bin"
ExecStart=/var/www/shift-scheduler/venv/bin/gunicorn \
  --workers 4 \
  --worker-class sync \
  --bind 127.0.0.1:5000 \
  --timeout 120 \
  --access-logfile /var/log/shift-scheduler/access.log \
  --error-logfile /var/log/shift-scheduler/error.log \
  web_interface:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo mkdir -p /var/log/shift-scheduler
sudo chown www-data:www-data /var/log/shift-scheduler

sudo systemctl daemon-reload
sudo systemctl enable shift-scheduler
sudo systemctl start shift-scheduler
sudo systemctl status shift-scheduler
```

#### Step 5: Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/shift-scheduler
```

Paste:
```nginx
upstream shift_scheduler {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (use Let's Encrypt with certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Logging
    access_log /var/log/nginx/shift-scheduler-access.log;
    error_log /var/log/nginx/shift-scheduler-error.log;

    # Max upload size
    client_max_body_size 10M;

    # Reverse proxy
    location / {
        proxy_pass http://shift_scheduler;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 120;
        proxy_send_timeout 120;
        proxy_read_timeout 120;
    }

    # Static files (if needed)
    location /static/ {
        alias /var/www/shift-scheduler/static/;
        expires 30d;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/shift-scheduler /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 6: Setup SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

### Option 2: Heroku

#### Step 1: Install Heroku CLI

```bash
curl https://cli-assets.heroku.com/install.sh | sh
heroku login
```

#### Step 2: Create Procfile

```bash
echo "web: gunicorn -w 4 web_interface:app" > Procfile
```

#### Step 3: Create runtime.txt

```bash
echo "python-3.11.4" > runtime.txt
```

#### Step 4: Deploy

```bash
# Create Heroku app
heroku create shift-scheduler

# Set environment variables
heroku config:set DATABASE_URL="postgresql://..."
heroku config:set FLASK_ENV="production"
heroku config:set SECRET_KEY="your-secret-key"

# Deploy
git push heroku main

# Check logs
heroku logs -t
```

---

### Option 3: Railway.app

#### Step 1: Connect Repository

1. Go to [railway.app](https://railway.app)
2. Create new project
3. Connect GitHub repository

#### Step 2: Configure Environment

Add environment variables in Railway dashboard:
```
DATABASE_URL=postgresql://...
FLASK_ENV=production
SECRET_KEY=...
```

#### Step 3: Deploy

Push to main branch - auto-deploys via GitHub integration.

---

## Monitoring & Maintenance

### View Logs

```bash
# Systemd service
sudo journalctl -u shift-scheduler -f

# Nginx
sudo tail -f /var/log/nginx/shift-scheduler-error.log
sudo tail -f /var/log/nginx/shift-scheduler-access.log

# Application
tail -f /var/log/shift-scheduler/error.log
```

### Restart Service

```bash
sudo systemctl restart shift-scheduler
sudo systemctl restart nginx
```

### Check Database Connection

```bash
# SSH into server
psql $DATABASE_URL -c "SELECT 1;"
```

### Monitor Resources

```bash
# CPU and memory
top -u www-data

# Disk space
df -h

# Database size
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
```

---

## Backup Strategy

### Neon PostgreSQL Automatic Backups

Neon provides automatic backups. To restore:

1. Log into Neon dashboard
2. Navigate to your project
3. Click "Restore from backup"
4. Select point-in-time

### Manual Database Backup

```bash
# Dump database
pg_dump $DATABASE_URL > backup.sql

# Restore from dump
psql $DATABASE_URL < backup.sql

# Upload to cloud storage
aws s3 cp backup.sql s3://your-bucket/backups/
```

### Code Backup

```bash
# Git push ensures code is backed up
git push origin main

# Additionally, backup to cloud
tar czf shift-scheduler.tar.gz .
aws s3 cp shift-scheduler.tar.gz s3://your-bucket/
```

---

## Performance Tuning

### Gunicorn Workers

```bash
# Workers = (2 x CPU_CORES) + 1
# For 2 cores: 5 workers

--workers 5
```

### Connection Pooling

SQLAlchemy is already configured with:
```python
create_engine(..., pool_pre_ping=True)
```

### Nginx Caching

```nginx
location /api/shifts {
    proxy_cache_valid 200 5m;
    add_header X-Cache-Status $upstream_cache_status;
}
```

### Database Indexing

Already done in models:
```python
business_id = Column(..., index=True)
shift_id = Column(..., index=True)
worker_id = Column(..., index=True)
```

---

## Security Hardening

### 1. Update Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

### 2. Set Strong Secret Key

```python
SECRET_KEY = secrets.token_urlsafe(32)
```

### 3. Enable HTTPS Only

In `.env`:
```
FLASK_ENV=production
```

### 4. Database Credentials

Never commit to git:
```bash
# .gitignore
.env
*.db
venv/
```

### 5. Firewall Rules

```bash
# Allow only HTTP/HTTPS
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw enable
```

### 6. Rate Limiting (Future)

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

---

## Scaling for High Traffic

### 1. Horizontal Scaling

Run multiple Gunicorn instances behind load balancer:
```bash
# Instance 1
gunicorn -w 4 -b 127.0.0.1:5001 web_interface:app

# Instance 2
gunicorn -w 4 -b 127.0.0.1:5002 web_interface:app
```

Update Nginx upstream:
```nginx
upstream shift_scheduler {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
}
```

### 2. Database Pooling

Increase pool size:
```python
create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40
)
```

### 3. Caching

Add Redis for session storage:
```python
from flask_session import Session
import redis

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost')
```

---

## Troubleshooting Deployment

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check Gunicorn is running: `systemctl status shift-scheduler` |
| Database connection timeout | Verify DATABASE_URL and whitelist server IP in Neon |
| High CPU usage | Increase workers or optimize queries |
| Out of disk space | Check log rotation: `logrotate -f /etc/logrotate.d/shift-scheduler` |
| SSL certificate error | Renew: `sudo certbot renew --force-renewal` |

---

## Monitoring Tools

### Application Monitoring
- **Sentry** (error tracking): Add SDK to Flask
- **New Relic** (APM)
- **DataDog** (comprehensive monitoring)

### Log Aggregation
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **Papertrail**

### Uptime Monitoring
- **Pingdom**
- **UptimeRobot**
- **StatusPage.io**

---

## Disaster Recovery

### Data Loss Prevention

1. **Neon Backups**: Enabled by default (7-day retention)
2. **Git Version Control**: Code is tracked
3. **Regular Exports**: Periodic database dumps

### Recovery Procedure

1. Restore database from Neon backup
2. Redeploy application code from git
3. Run migrations if needed
4. Verify data integrity

---

## Cost Optimization

### Development
- Neon free tier ($0)
- VPS from $5/month
- Total: ~$5-10/month

### Production
- Neon Pro: ~$25/month
- VPS (2GB RAM): ~$12/month
- Domain: ~$12/month
- SSL: Free (Let's Encrypt)
- Total: ~$50/month

### Cost Reduction
- Use Heroku free tier for testing
- Archive old data to reduce DB size
- Use CDN for static assets

---

## Support

For deployment issues:
1. Check logs: `systemctl status shift-scheduler`
2. Verify environment variables: `printenv | grep DATABASE`
3. Test database connection: `psql $DATABASE_URL -c "SELECT 1"`
4. Review Nginx configuration: `nginx -t`

---

**Last Updated**: March 27, 2025  
**Version**: 2.0  
**Status**: Production Ready ✅
