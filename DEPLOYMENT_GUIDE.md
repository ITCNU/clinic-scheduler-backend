# Clinic Scheduler - LAN Deployment Guide

## Option 1: Simple LAN Deployment (Recommended)

### Prerequisites
- A computer/server on your LAN with Python 3.8+
- PostgreSQL database server (local or remote)
- All users can access this computer via network
- Database credentials configured in `.env` file

### Step 1: Server Setup

1. **Install Python and Dependencies**
   ```bash
   # On the server computer
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Setup PostgreSQL Database**
   ```bash
   # Install PostgreSQL (if not already installed)
   # Ubuntu/Debian:
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # CentOS/RHEL:
   sudo yum install postgresql postgresql-server
   ```

3. **Create Database and User**
   ```sql
   # Connect as postgres user
   sudo -u postgres psql
   
   # Create database and user
   CREATE DATABASE clinic_scheduler;
   CREATE USER app_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE clinic_scheduler TO app_user;
   ALTER SCHEMA public OWNER TO app_user;
   GRANT USAGE, CREATE ON SCHEMA public TO app_user;
   ```

4. **Configure Environment**
   Create `.env` file in your app directory:
   ```env
   DATABASE_URL=postgresql+psycopg://app_user:your_password@localhost:5432/clinic_scheduler
   SECRET_KEY=your-secret-key-here
   ```

5. **Run Database Migrations**
   ```bash
   alembic upgrade head
   ```

6. **Configure Network Access**
   Your `run.py` is already configured correctly with `host="0.0.0.0"` which allows LAN access.

7. **Start the Server**
   ```bash
   python run.py
   ```

8. **Find Server IP Address**
   ```bash
   # Windows
   ipconfig
   
   # Linux/Mac
   ifconfig
   ```
   Look for your LAN IP (usually starts with 192.168.x.x or 10.x.x.x)

### Step 2: Client Access

Users can access the application at:
```
http://[SERVER_IP]:8000
```

Example: `http://192.168.1.100:8000`

### Step 3: Firewall Configuration

**Windows Server:**
1. Open Windows Defender Firewall
2. Click "Allow an app or feature through Windows Defender Firewall"
3. Add Python or allow port 8000

**Linux Server:**
```bash
# Ubuntu/Debian
sudo ufw allow 8000

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## Option 2: Production Deployment with Reverse Proxy

### Using Nginx (Recommended for Production)

1. **Install Nginx**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install nginx
   
   # CentOS/RHEL
   sudo yum install nginx
   ```

2. **Create Nginx Configuration**
   ```bash
   sudo nano /etc/nginx/sites-available/clinic-scheduler
   ```

   Add this configuration:
   ```nginx
   server {
       listen 80;
       server_name your-server-ip-or-domain;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       location /static/ {
           alias /path/to/your/app/static/;
       }
   }
   ```

3. **Enable the Site**
   ```bash
   sudo ln -s /etc/nginx/sites-available/clinic-scheduler /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. **Run App as Service**
   Create `/etc/systemd/system/clinic-scheduler.service`:
   ```ini
   [Unit]
   Description=Clinic Scheduler App
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/path/to/your/app
   Environment=PATH=/path/to/your/app/venv/bin
   ExecStart=/path/to/your/app/venv/bin/python run.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable the service:
   ```bash
   sudo systemctl enable clinic-scheduler
   sudo systemctl start clinic-scheduler
   ```

## Option 3: Docker Deployment

### Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

### Create docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: clinic_scheduler
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  clinic-scheduler:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://app_user:your_password@postgres:5432/clinic_scheduler
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
```

### Deploy with Docker
```bash
docker-compose up -d
```

## Option 4: Windows Service (Windows Server)

1. **Install NSSM (Non-Sucking Service Manager)**
   Download from: https://nssm.cc/download

2. **Create Service**
   ```cmd
   nssm install ClinicScheduler
   ```
   - Path: `C:\Python39\python.exe` (or your Python path)
   - Startup directory: `C:\path\to\your\app`
   - Arguments: `run.py`

3. **Start Service**
   ```cmd
   nssm start ClinicScheduler
   ```

## Security Considerations

1. **HTTPS Setup** (Recommended for production)
   - Use Let's Encrypt for free SSL certificates
   - Configure Nginx with SSL

2. **Database Security**
   - Regular backups of PostgreSQL database
   - Use strong passwords for database users
   - Configure PostgreSQL authentication properly

3. **Access Control**
   - Configure firewall rules
   - Use VPN if accessing from outside LAN

## Monitoring and Maintenance

1. **Log Management**
   ```bash
   # View logs
   tail -f /var/log/nginx/access.log
   journalctl -u clinic-scheduler -f
   ```

2. **Backup Script**
   ```bash
   #!/bin/bash
   # PostgreSQL backup
   pg_dump -h localhost -U app_user clinic_scheduler > backup/clinic_scheduler_$(date +%Y%m%d).sql
   
   # Or for binary backup
   pg_dump -h localhost -U app_user -Fc clinic_scheduler > backup/clinic_scheduler_$(date +%Y%m%d).dump
   ```

3. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

## Troubleshooting

1. **Port Already in Use**
   ```bash
   # Find process using port 8000
   netstat -tulpn | grep :8000
   # Kill process
   kill -9 [PID]
   ```

2. **Permission Issues**
   ```bash
   # Make sure Python has read/write access
   chmod 755 /path/to/your/app
   chown -R www-data:www-data /path/to/your/app
   ```

3. **Database Connection Issues**
   - Check PostgreSQL service is running: `sudo systemctl status postgresql`
   - Verify database credentials in `.env` file
   - Test connection: `psql -h localhost -U app_user -d clinic_scheduler`

## Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup PostgreSQL database
sudo -u postgres createdb clinic_scheduler
sudo -u postgres createuser app_user

# 3. Configure environment (.env file)
echo "DATABASE_URL=postgresql+psycopg://app_user:password@localhost:5432/clinic_scheduler" > .env

# 4. Run migrations
alembic upgrade head

# 5. Start server
python run.py

# 6. Access from other computers
# http://[YOUR_IP]:8000
```

## Network Configuration Examples

### For Windows Network:
- Server IP: `192.168.1.100`
- Access URL: `http://192.168.1.100:8000`

### For Corporate Network:
- Server IP: `10.0.0.50`
- Access URL: `http://10.0.0.50:8000`

### With Domain Name:
- Configure DNS or hosts file
- Access URL: `http://clinic-scheduler.company.local`
