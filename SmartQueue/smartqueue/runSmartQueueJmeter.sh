#!/bin/bash

# Usage: ./runSmartQueueJmeter.sh <small|medium|large>
set -u

LOAD_LEVEL="${1:-}"
if [[ -z "$LOAD_LEVEL" ]]; then
  echo "Usage: $0 <small|medium|large>"
  exit 1
fi

HOST="localhost"
PORT=8000

case "$LOAD_LEVEL" in
  small)
    THREAD=20       
    DURATION=120     
    RAMP=10         
    ;;
  medium)
    THREAD=50
    DURATION=180
    RAMP=20
    ;;
  large)
    THREAD=100
    DURATION=300
    RAMP=30
    ;;
  *)
    echo "Error: invalid load level '$LOAD_LEVEL'. Use: small | medium | large"
    exit 1
    ;;
esac

echo "HOST=${HOST}"
echo "PORT=${PORT}"
echo "THREAD=${THREAD}"
echo "DURATION=${DURATION}"
echo "RAMP=${RAMP}"

mkdir -p logs
TS="$(date +%Y%m%d-%H%M%S)"
LOG="logs/jmeter_${LOAD_LEVEL}_${TS}.log"
JTL="logs/jmeter_${LOAD_LEVEL}_${TS}.jtl"

echo "[LOAD] starting JMeter… log: ${LOG}, jtl: ${JTL}"

jmeter -n \
  -t jmeter/SmartQueue.jmx \
  -JHOST=${HOST} \
  -JPORT=${PORT} \
  -JTHREAD=${THREAD} \
  -JDURATION=${DURATION} \
  -JRAMP=${RAMP} \
  -l "${JTL}" \
  -j "${LOG}"

echo "[LOAD] finished. JTL: ${JTL}"
