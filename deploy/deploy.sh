#!/bin/bash
# Usage: deploy.sh <image-with-tag> <version>
set -u
IMAGE="$1"
VERSION="$2"
NAME="shadow-ml"

PREV_IMAGE=$(docker inspect --format '{{.Config.Image}}' "$NAME" 2>/dev/null || true)

echo "Pulling $IMAGE"
docker pull "$IMAGE" || { echo "Pull failed"; exit 1; }

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --restart unless-stopped -p 80:8000 -e APP_VERSION="$VERSION" "$IMAGE"

for i in $(seq 1 20); do
  if curl -fsS http://localhost/health >/dev/null 2>&1; then
    echo "Deployment healthy: $IMAGE"
    exit 0
  fi
  sleep 3
done

echo "Health check failed - rolling back"
docker logs --tail 30 "$NAME" || true
docker rm -f "$NAME" >/dev/null 2>&1 || true
if [ -n "$PREV_IMAGE" ]; then
  docker run -d --name "$NAME" --restart unless-stopped -p 80:8000 -e APP_VERSION="${PREV_IMAGE##*:}" "$PREV_IMAGE"
  echo "Rolled back to $PREV_IMAGE"
else
  echo "No previous image to roll back to"
fi
exit 1
