cleanup() {
    echo -e "Exit existing Pods"
    podman-compose down
    exit 1
}


trap cleanup SIGINT

# Start containers (always restart policy)
podman-compose up --build --force-recreate -d

# Show status
podman logs -f excite_api