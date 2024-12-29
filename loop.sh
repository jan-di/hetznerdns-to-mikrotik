#!/bin/sh

if [ -z "$ZONE" ]; then
    echo "ZONE is not set"
    exit 2
fi

if [ -z "$HETZNER_NAMESERVERS" ]; then
    HETZNER_NAMESERVERS="helium.ns.hetzner.de oxygen.ns.hetzner.com hydrogen.ns.hetzner.com"
fi

if [ -z "$INTERVAL" ]; then
    INTERVAL=600
fi

old_serial=""

get_serial() {
    _domain="$1"
    _nameserver="$2"
    _serial="$(nslookup  -type=SOA "$_domain" "$_nameserver" | grep -oE "serial = (\d+)" | cut -d= -f2 | xargs)"
    echo "$_serial"
}

while true; do

    if [ -n "$HEALTHCHECK_START_URL" ]; then
        curl -fsS "$HEALTHCHECK_START_URL"
    fi
    
    success=1
    random_nameserver=$(echo "$HETZNER_NAMESERVERS" | tr ' ' '\n' | shuf | head -n 1)
    serial=$(get_serial "$ZONE" "$random_nameserver")

    if [ "$serial" != "$old_serial" ]; then
        echo "Serial of $ZONE changed from $old_serial to $serial. Trigger sync."

        if ! poetry run hdns2mikrotik sync --zones "$ZONE"
        then
            echo "Failed to sync $ZONE"
            success=0
        fi
    

        old_serial="$serial"
    else
        echo "Serial of $ZONE is still $serial. No need to sync."
    fi

    # check if success
    if [ "$success" = "1" ]; then
        if [ -n "$HEALTHCHECK_SUCCESS_URL" ]; then
            curl -fsS "$HEALTHCHECK_SUCCESS_URL"
        fi
    else
        if [ -n "$HEALTHCHECK_FAILURE_URL" ]; then
            curl -fsS "$HEALTHCHECK_FAILURE_URL"
        fi
    fi

    echo "Sleeping for $INTERVAL seconds"
    sleep "$INTERVAL"
done
