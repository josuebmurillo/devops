#!/bin/sh
set -eu

SOURCE_KUBECONFIG="/k3s/kubeconfig.yaml"
KUBECONFIG="/tmp/kubeconfig.yaml"
attempt=0

while [ ! -s "$SOURCE_KUBECONFIG" ]; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 120 ]; then
        echo "Timed out waiting for K3s kubeconfig at $SOURCE_KUBECONFIG" >&2
        exit 1
    fi
    sleep 2
done

sed 's#https://127\.0\.0\.1:6443#https://k3s-server:6443#' \
    "$SOURCE_KUBECONFIG" > "$KUBECONFIG"
export KUBECONFIG

exec "$@"