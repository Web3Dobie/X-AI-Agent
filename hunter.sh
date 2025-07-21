#!/bin/bash
# Hunter Project Management Script
# Usage: ./hunter.sh [start|stop|restart|status|logs|errors]

PROJECT_DIR=$(pwd)
SERVICE_NAME="hunter-scheduler"

case "$1" in        
    start)
        echo "🚀 Starting Hunter Scheduler..."
        sudo supervisorctl start $SERVICE_NAME
        sudo supervisorctl status $SERVICE_NAME
        ;;
        
    stop)
        echo "🛑 Stopping Hunter Scheduler..."
        sudo supervisorctl stop $SERVICE_NAME
        sudo supervisorctl status $SERVICE_NAME
        ;;
        
    restart)
        echo "🔄 Restarting Hunter Scheduler..."
        sudo supervisorctl restart $SERVICE_NAME
        sudo supervisorctl status $SERVICE_NAME
        ;;
        
    status)
        echo "📊 Hunter Scheduler Status:"
        sudo supervisorctl status $SERVICE_NAME
        ;;
        
    logs)
        echo "📋 Hunter Scheduler Logs (Ctrl+C to exit):"
        sudo supervisorctl tail -f $SERVICE_NAME
        ;;
        
    errors)
        echo "🚨 Hunter Scheduler Error Logs:"
        sudo tail -20 /var/log/hunter/scheduler_error.log
        ;;
        
    *)
        echo "🐕 Hunter Project Management"
        echo "Usage: $0 {start|stop|restart|status|logs|errors}"
        exit 1
        ;;
esac
