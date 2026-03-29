GROUP=9
if [ "$GROUP" -eq 0 ]; then
    echo "Error: please update your group number!"
    exit 1  
fi
HOST=$(oc get route acmeair-main-route -n acmeair-group${GROUP} --template='{{ .spec.host }}')
PORT=80


# no prefix
curl -i "http://$HOST/booking/loader/load"
