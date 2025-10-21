# Render Deployment Guide for Clinic Scheduler

## Overview
This guide will help you deploy your FastAPI clinic scheduler application to Render, a modern cloud platform that's perfect for your educational application.

## Prerequisites
- GitHub account
- Render account (free tier available)
- Your code pushed to GitHub

## Step 1: Prepare Your Repository

### 1.1 Create a Render-specific requirements.txt
Create a `requirements.txt` file in your project root (if not already present):

```
fastapi
uvicorn[standard]
sqlalchemy
alembic
psycopg[binary]
python-jose[cryptography]
passlib[bcrypt]
python-multipart
pydantic
pydantic-settings
python-dotenv
jinja2
aiofiles
email-validator
pandas
openpyxl
```

### 1.2 Create a render.yaml file
Create a `render.yaml` file in your project root:

```yaml
services:
  - type: web
    name: clinic-scheduler
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        value: postgresql://username:password@hostname:port/database
      - key: SECRET_KEY
        value: your-secret-key-change-this-in-production
      - key: DEBUG
        value: False
    healthCheckPath: /health

  - type: pserv
    name: clinic-scheduler-db
    plan: free
    databaseName: clinic_scheduler
    user: clinic_user
```

### 1.3 Update your app configuration
Update `app/config.py` to use environment variables:

```python
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./clinic_scheduler.db")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # App
    app_name: str = "CNU Dental Clinic Scheduler"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Step 2: Deploy to Render

### 2.1 Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Connect your GitHub repository

### 2.2 Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure the service:
   - **Name**: `clinic-scheduler`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

### 2.3 Create PostgreSQL Database
1. Click "New +" → "PostgreSQL"
2. Configure the database:
   - **Name**: `clinic-scheduler-db`
   - **Plan**: Free
   - **Database Name**: `clinic_scheduler`
   - **User**: `clinic_user`

### 2.4 Configure Environment Variables
In your web service settings, add these environment variables:

```
DATABASE_URL=postgresql://clinic_user:password@hostname:port/clinic_scheduler
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=False
```

## Step 3: Database Migration

### 3.1 Create Migration Script
Create a `migrate.py` file in your project root:

```python
import os
import subprocess
import sys

def run_migration():
    """Run database migrations"""
    try:
        # Run Alembic migrations
        result = subprocess.run(['alembic', 'upgrade', 'head'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Database migration completed successfully")
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
```

### 3.2 Update Build Command
Change your build command in Render to:
```
pip install -r requirements.txt && python migrate.py
```

## Step 4: Custom Domain (Optional)

### 4.1 Add Custom Domain
1. Go to your service settings
2. Click "Custom Domains"
3. Add your domain (e.g., `clinic-scheduler.yourdomain.com`)
4. Follow the DNS configuration instructions

### 4.2 SSL Certificate
Render automatically provides SSL certificates for custom domains.

## Step 5: Monitoring and Logs

### 5.1 View Logs
- Go to your service dashboard
- Click "Logs" tab
- Monitor application performance and errors

### 5.2 Health Checks
Your app should respond to `/health` endpoint for monitoring.

## Step 6: Production Configuration

### 6.1 Security Settings
- Change `SECRET_KEY` to a strong, random value
- Set `DEBUG=False` in production
- Use HTTPS only

### 6.2 Performance Optimization
- Consider upgrading to paid plan for better performance
- Enable auto-scaling if needed
- Monitor database performance

## Troubleshooting

### Common Issues:

1. **Build Failures**
   - Check `requirements.txt` syntax
   - Ensure all dependencies are listed
   - Check Python version compatibility

2. **Database Connection Issues**
   - Verify `DATABASE_URL` format
   - Check database service status
   - Ensure migrations ran successfully

3. **Application Crashes**
   - Check logs for error messages
   - Verify environment variables
   - Test locally with same configuration

### Getting Help:
- Render Documentation: [render.com/docs](https://render.com/docs)
- Render Community: [community.render.com](https://community.render.com)
- Support: Available on paid plans

## Cost Breakdown

### Free Tier Limits:
- **Web Service**: 750 hours/month
- **PostgreSQL**: 1 GB storage, 1 GB RAM
- **Custom Domain**: Included
- **SSL**: Included

### Paid Plans:
- **Starter**: $7/month (more hours, better performance)
- **Standard**: $25/month (dedicated resources)

## Next Steps After Deployment

1. **Test Your Application**
   - Verify all features work
   - Test user registration/login
   - Check database operations

2. **Set Up Monitoring**
   - Configure health checks
   - Set up error alerts
   - Monitor performance metrics

3. **Backup Strategy**
   - Regular database backups
   - Code repository backups
   - Environment configuration backups

4. **Update Process**
   - Push changes to GitHub
   - Render auto-deploys from main branch
   - Test in staging environment first

## Security Considerations

1. **Environment Variables**
   - Never commit secrets to code
   - Use Render's environment variable system
   - Rotate secrets regularly

2. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Regular security updates

3. **Application Security**
   - Keep dependencies updated
   - Use HTTPS only
   - Implement proper authentication

## Support and Maintenance

- **Free Tier**: Community support
- **Paid Plans**: Priority support
- **Documentation**: Comprehensive guides available
- **Community**: Active user community

---

**Ready to deploy? Follow the steps above and your clinic scheduler will be live on Render!**
