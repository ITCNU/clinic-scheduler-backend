#!/bin/bash

# Database backup script
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Backup database
cp clinic_scheduler.db $BACKUP_DIR/clinic_scheduler_$DATE.db

echo "✅ Database backed up to: $BACKUP_DIR/clinic_scheduler_$DATE.db"

# Keep only last 10 backups
ls -t $BACKUP_DIR/clinic_scheduler_*.db | tail -n +11 | xargs -r rm

echo "📁 Kept last 10 backups, removed older ones."
