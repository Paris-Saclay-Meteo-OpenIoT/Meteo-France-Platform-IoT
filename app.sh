#!/bin/bash

case "${1:-start}" in
    start)
        command -v docker > /dev/null || exit 1
        sudo docker system prune -f // attention selon le besoin, -f force la suppression sans confirmation.
        sudo docker-compose up -d
        ;;
    stop)
        sudo docker-compose down
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac
