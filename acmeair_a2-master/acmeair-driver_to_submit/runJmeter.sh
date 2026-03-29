#!/bin/bash

# Usage: ./runJmeter.sh <small|medium|large>
set -u

LOAD_LEVEL="${1:-}"
if [[ -z "$LOAD_LEVEL" ]]; then
  echo "Usage: $0 <small|medium|large>"
  exit 1
fi

GROUP=9
if [ "$GROUP" -eq 0 ]; then
    echo "Error: please update your group number!"
    exit 1  
fi
HOST=$(oc get route acmeair-main-route -n acmeair-group${GROUP} --template='{{ .spec.host }}')
PORT=80

# THREAD=10
# USER=999
# DURATION=60
# RAMP=0
# DELAY=0

# Switch-case profiles
case "$LOAD_LEVEL" in
  small)
    THREAD=100
    USER=999
    DURATION=300
    RAMP=60
    DELAY=1
    ;;
  medium)
    THREAD=300
    USER=3000
    DURATION=300
    RAMP=120
    DELAY=2
    ;;
  large)
    THREAD=600
    USER=5000
    DURATION=300
    RAMP=180
    DELAY=2
    ;;
  *)
    echo "Error: invalid load level '$LOAD_LEVEL'. Use: small | medium | large"
    exit 1
    ;;
esac

echo HOST=${HOST}
echo PORT=${PORT}
echo THREAD=${THREAD}
echo USER=${USER}
echo DURATION=${DURATION}
echo RAMP=${RAMP}
echo DELAY=${DELAY}

curl http://${HOST}/booking/loader/load
echo ""
curl http://${HOST}/flight/loader/load
echo ""
curl http://${HOST}/customer/loader/load?numCustomers=10000
echo ""

mkdir -p logs
TS="$(date +%Y%m%d-%H%M%S)"
LOG="logs/jmeter_${LOAD_LEVEL}_${TS}.log"
JTL="logs/jmeter_${LOAD_LEVEL}_${TS}.jtl"

echo "[LOAD] starting JMeter… log: ${LOG}"

jmeter -n -t acmeair-jmeter/scripts/AcmeAir-microservices-mpJwt.jmx \
 -DusePureIDs=true \
 -JHOST=${HOST} \
 -JPORT=${PORT} \
 -JTHREAD=${THREAD} \
 -JUSER=${USER} \
 -JDURATION=${DURATION} \
 -JRAMP=${RAMP} \
 -JDELAY=${DELAY}

echo "[LOAD] finished. JTL: ${JTL}"