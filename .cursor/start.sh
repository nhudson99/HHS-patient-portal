#!/bin/bash
# Start Docker daemon and bring up the production-like compose stack.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  cp .env.docker.example .env
fi

DOCKER_CMD=(docker)
if ! docker info >/dev/null 2>&1; then
  if sudo docker info >/dev/null 2>&1; then
    DOCKER_CMD=(sudo docker)
  fi
fi

start_docker_daemon() {
  if "${DOCKER_CMD[@]}" info >/dev/null 2>&1; then
    return 0
  fi

  if command -v service >/dev/null 2>&1 && sudo service docker start >/dev/null 2>&1; then
    :
  else
  # Non-systemd / cloud-agent VMs: start dockerd manually with fuse-overlayfs
  # (required for docker-in-docker; see Cursor cloud-agent Docker docs)
    if ! command -v fuse-overlayfs >/dev/null 2>&1; then
      sudo apt-get update -qq
      sudo apt-get install -y -qq fuse-overlayfs iptables >/dev/null 2>&1 || true
      if command -v update-alternatives >/dev/null 2>&1; then
        sudo update-alternatives --set iptables /usr/sbin/iptables-legacy 2>/dev/null || true
        sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy 2>/dev/null || true
      fi
    fi

    sudo mkdir -p /etc/docker
    if [ ! -f /etc/docker/daemon.json ]; then
      printf '%s\n' '{' '  "storage-driver": "fuse-overlayfs"' '}' | sudo tee /etc/docker/daemon.json >/dev/null
    fi

    if ! pgrep -x dockerd >/dev/null 2>&1; then
      sudo nohup dockerd >/tmp/dockerd.log 2>&1 &
    fi
  fi

  for _ in $(seq 1 45); do
    if "${DOCKER_CMD[@]}" info >/dev/null 2>&1 || sudo docker info >/dev/null 2>&1; then
      if ! docker info >/dev/null 2>&1; then
        DOCKER_CMD=(sudo docker)
      fi
      return 0
    fi
    sleep 1
  done

  echo "Docker daemon failed to start. See /tmp/dockerd.log" >&2
  return 1
}

start_docker_daemon

# Release 5432 if the host PostgreSQL service is still running (legacy native setup).
if command -v ss >/dev/null 2>&1 && ss -tln | grep -q ':5432 '; then
  if command -v pg_ctlcluster >/dev/null 2>&1; then
    sudo pg_ctlcluster 16 main stop 2>/dev/null || true
  fi
fi

COMPOSE_CMD=("${DOCKER_CMD[@]}" compose)
"${COMPOSE_CMD[@]}" up -d --build

for _ in $(seq 1 90); do
  if curl -sf http://localhost:3000/health >/dev/null 2>&1; then
    echo "Stack ready: http://localhost:80 (nginx) / http://localhost:3000 (api)"
    exit 0
  fi
  sleep 2
done

echo "Warning: API health check did not pass within timeout; containers may still be starting." >&2
"${COMPOSE_CMD[@]}" ps
