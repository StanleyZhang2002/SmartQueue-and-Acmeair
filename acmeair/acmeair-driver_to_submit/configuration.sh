#!/bin/bash
# configuration.sh— edit YAML CPU(m), Memory(Mi), Replicas; optionally only 1 service; then oc apply
# Creates a .bak backup of each YAML before modifying it.
set -euo pipefail

cpu="500"      # milli-cores
memory="512"   # MiB
replica="1"
service=""     # e.g., acmeair-*-service

# Parse args (supports named style: cpu=500 memory=512 replica=2 service=acmeair-customerservice)
while [[ $# -gt 0 ]]; do
    case "$1" in
        cpu=*) cpu="${1#cpu=}"; shift;;
        memory=*) memory="${1#memory=}"; shift;;
        replica=*) replica="${1#replica=}"; shift;;
        service=*) service="${1#service=}"; shift;;
        *) echo "Invalid arg: $1"; exit 1;;
    esac
done

time_stamp="$(date +%Y%m%d-%H%M%S)"

# Target YAMLs
files=("deploy-acmeair-mainservice-java.yaml"
       "deploy-acmeair-authservice-java.yaml"
       "deploy-acmeair-flightservice-java.yaml"
       "deploy-acmeair-customerservice-java.yaml"
       "deploy-acmeair-bookingservice-java.yaml")

for file in "${files[@]}"; do
    [[ ! -f "$file" ]] && continue

    svc=$(echo "$file" | grep -oE "acmeair-.*?service" | head -1)
    # If a specific service was requested, skip non-matching files
    if [[ -n "$service" && "$service" != "$svc" ]]; then
        continue
    fi

    echo "[PATCH] $file ($svc)  -> backups to ${file}.bak"

    sed -i".bak.${time_stamp}" -E \
        -e "s/^([[:space:]]*)replicas:[[:space:]]*[0-9]+/\1replicas: ${replica}/" \
        -e "s/(cpu:[[:space:]]*\"?)[0-9]+m(\"?)/\1${cpu}m\2/g" \
        -e "s/(memory:[[:space:]]*\"?)[0-9]+Mi(\"?)/\1${memory}Mi\2/g" \
        "$file"

    # Apply the updated YAML to the current OpenShift project
    oc apply -f "$file"
done

echo "[DONE] Applied. Backups are alongside the YAMLs."
