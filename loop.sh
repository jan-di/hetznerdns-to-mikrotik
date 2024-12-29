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
    random_nameserver=$(echo "$HETZNER_NAMESERVERS" | tr ' ' '\n' | shuf | head -n 1)
    serial=$(get_serial "$ZONE" "$random_nameserver")

    if [ "$serial" != "$old_serial" ]; then
        echo "Serial of $ZONE changed from $old_serial to $serial. Trigger sync."

        poetry run hdns2mikrotik sync --zones "$ZONE"

        old_serial="$serial"
    else
        echo "Serial of $ZONE is still $serial. No need to sync."
    fi

    echo "Sleeping for $INTERVAL seconds"
    sleep "$INTERVAL"
done
