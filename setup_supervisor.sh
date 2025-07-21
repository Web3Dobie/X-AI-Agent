#!/bin/bash
# Hunter Supervisor Setup Script

echo "🐕 Setting up Hunter Scheduler with Supervisor"

# Get current directory and user
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "📍 Working in: $CURRENT_DIR"
echo "👤 User: $CURRENT_USER"

# 1. Install supervisor if not already installed
echo "📦 Installing supervisor..."
sudo apt update
sudo apt install -y supervisor

# 2. Create log directory
echo "📁 Creating log directories..."
sudo mkdir -p /var/log/hunter
sudo chown $CURRENT_USER:$CURRENT_USER /var/log/hunter

# 3. Create supervisor configuration
echo "⚙️ Creating supervisor configuration..."
sudo tee /etc/supervisor/conf.d/hunter-scheduler.conf << EOF
[program:hunter-scheduler]
command=$CURRENT_DIR/venv/bin/python scheduler.py
directory=$CURRENT_DIR
user=$CURRENT_USER
autostart=true
autorestart=true
autorestart_pause=10
startretries=3
stdout_logfile=/var/log/hunter/scheduler.log
stderr_logfile=/var/log/hunter/scheduler_error.log
stdout_logfile_maxbytes=50MB
stderr_logfile_maxbytes=50MB
stdout_logfile_backups=5
stderr_logfile_backups=5
environment=PATH="$CURRENT_DIR/venv/bin"
stopwaitsecs=30
killasgroup=true
stopasgroup=true
EOF

echo "✅ Supervisor configuration created at /etc/supervisor/conf.d/hunter-scheduler.conf"

# 4. Update supervisor
echo "🔄 Updating supervisor..."
sudo supervisorctl reread
sudo supervisorctl update

# 5. Check status
echo "📊 Current supervisor status:"
sudo supervisorctl status

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Common commands:"
echo "  Check status:    sudo supervisorctl status hunter-scheduler"
echo "  Start:           sudo supervisorctl start hunter-scheduler"
echo "  Stop:            sudo supervisorctl stop hunter-scheduler"
echo "  Restart:         sudo supervisorctl restart hunter-scheduler"
echo "  View logs:       sudo supervisorctl tail -f hunter-scheduler"
echo "  Error logs:      sudo tail -f /var/log/hunter/scheduler_error.log"
echo ""
echo "🔧 Next steps:"
echo "1. Stop any existing screen sessions: screen -S Scheduler -X quit"
echo "2. Start the supervisor service: sudo supervisorctl start hunter-scheduler"