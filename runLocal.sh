# Clean up any previous pod with same name to avoid 'already exists' errors
podman-compose down && echo Dead

# Start containers (always restart policy)
podman-compose up --build --force-recreate -d

# Show status
podman logs -f excite_api