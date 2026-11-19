"""
CLI for hetznerdns-to-mikrotik
"""

import random
import time

import click
import dns.exception
import dns.resolver
import requests
import routeros_api
from routeros_api.resource import RouterOsResource

from hetznerdns_to_mikrotik.hetzner import HetznerApi
from hetznerdns_to_mikrotik.model import Record

MIKROTIK_RECORD_COMMENT = "hetznerdns_to_mikrotik"


@click.group()
def main():
    """
    Main CLI group
    """


@main.command()
@click.option("--api-token", "-a", help="Hetzner DNS API key", required=True, envvar="API_TOKEN")
@click.option("--zones", "-z", help="Comma separated list of zones to sync", required=True, envvar="ZONES")
@click.option(
    "--record-types",
    "-r",
    help="Comma separated list of record types to sync",
    default="A,AAAA,CNAME",
    envvar="RECORD_TYPES",
)
@click.option("--ttl", "-t", help="TTL for local records", default=600, envvar="TTL")
@click.option("--user", "-u", help="Mikrotik User", required=True, envvar="USER")
@click.option("--password", "-p", help="Mikrotik Password", required=True, envvar="PASSWORD")
@click.option("--mikrotik", "-m", help="Mikrotik Host", required=True, envvar="MIKROTIK")
@click.option("--dry-run", "-d", is_flag=True, help="Dry run mode", default=False)
@click.option("--watch", "-w", is_flag=True, help="Keep running and re-sync periodically", envvar="WATCH")
@click.option(
    "--watch-interval",
    help="Seconds between syncs in watch mode",
    default=600,
    show_default=True,
    type=click.IntRange(min=1),
    envvar="WATCH_INTERVAL",
)
@click.option(
    "--healthchecksio-url",
    help="Healthchecks.io-style base URL. Pinged at <url>/start before each sync, <url> on success, <url>/fail on failure",
    envvar="HEALTHCHECKSIO_URL",
)
@click.option(
    "--nameservers",
    help="Space or comma separated Hetzner nameservers, queried for the SOA serial in watch mode",
    default="helium.ns.hetzner.de,oxygen.ns.hetzner.com,hydrogen.ns.hetzner.com",
    show_default=True,
    envvar="HETZNER_NAMESERVERS",
)
def sync(
    api_token: str,
    zones: str,
    record_types: str,
    ttl: int,
    mikrotik: str,
    user: str,
    password: str,
    dry_run: bool,
    watch: bool,
    watch_interval: int,
    healthchecksio_url: str | None,
    nameservers: str,
):
    """
    Sync Hetzner DNS records to Mikrotik RouterOS

    In watch mode, a sync only happens when a zone's SOA serial changed since the last successful sync.
    """

    nameserver_list = nameservers.replace(",", " ").split()
    zone_list = zones.split(",")
    synced_serials: dict[str, int | None] = {}

    def run_once() -> bool:
        ping_healthchecksio(healthchecksio_url, "/start")
        try:
            # Fetch before syncing, so a change that happens during the sync is picked up next time
            serials = get_serials(zone_list, nameserver_list) if watch else {}
            changed = [
                zone
                for zone in zone_list
                if not watch or serials[zone] is None or serials[zone] != synced_serials.get(zone)
            ]
            if changed:
                click.echo(f"Syncing zones: {', '.join(changed)}")
                sync_once(api_token, zone_list, changed, record_types, ttl, mikrotik, user, password, dry_run)
                # only remembered after a successful sync
                synced_serials.update({zone: serials[zone] for zone in changed} if watch else {})
            else:
                click.echo(f"Serials unchanged ({serials}). No need to sync.")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            click.echo(f"Sync failed: {exc!r}", err=True)
            ping_healthchecksio(healthchecksio_url, "/fail")
            return False
        ping_healthchecksio(healthchecksio_url, "")
        return True

    if not watch:
        if not run_once():
            raise SystemExit(1)
        return

    try:
        while True:
            run_once()  # a failed sync is simply retried on the next iteration
            click.echo(f"Sleeping for {watch_interval} seconds")
            time.sleep(watch_interval)
    except KeyboardInterrupt:
        click.echo("Interrupted, exiting")


def get_serials(zones: list[str], nameservers: list[str]) -> dict[str, int | None]:
    """
    Get the SOA serial of each zone from a random Hetzner nameserver. None if it cannot be determined,
    which forces a sync.
    """
    nameserver = random.choice(nameservers)
    result: dict[str, int | None] = {}
    try:
        ns_ip = dns.resolver.resolve(nameserver, "A")[0].address
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [ns_ip]
    except dns.exception.DNSException as exc:
        click.echo(f"Could not resolve nameserver {nameserver}: {exc!r}", err=True)
        return {zone: None for zone in zones}

    for zone in zones:
        try:
            result[zone] = resolver.resolve(zone, "SOA", lifetime=10)[0].serial
        except dns.exception.DNSException as exc:
            click.echo(f"Could not get SOA serial of {zone} from {nameserver}: {exc!r}", err=True)
            result[zone] = None
    return result


def ping_healthchecksio(base_url: str | None, suffix: str):
    """
    Ping the healthcheck URL. Never raises, a broken healthcheck must not break the sync.
    """
    if not base_url:
        return
    try:
        requests.get(base_url.rstrip("/") + suffix, timeout=10).raise_for_status()
    except requests.RequestException as exc:
        click.echo(f"Healthcheck ping failed: {exc!r}", err=True)


def sync_once(
    api_token: str,
    all_zones: list[str],
    sync_zone_names: list[str],
    record_types: str,
    ttl: int,
    mikrotik: str,
    user: str,
    password: str,
    dry_run: bool,
):
    """
    Perform a single sync run for the given zones. Raises on any failure.
    """

    sync_record_types = record_types.split(",")

    pool = routeros_api.RouterOsApiPool(
        host=mikrotik, username=user, password=password, plaintext_login=True, use_ssl=True
    )
    mikrotik_api = pool.get_api()
    try:
        sync_records(
            mikrotik_api.get_resource("/ip/dns/static"),
            HetznerApi(api_token),
            all_zones,
            sync_zone_names,
            sync_record_types,
            ttl,
            dry_run,
        )
    finally:
        pool.disconnect()


def sync_records(
    static_dns: RouterOsResource,
    dns_api: HetznerApi,
    all_zones: list[str],
    sync_zone_names: list[str],
    sync_record_types: list[str],
    ttl: int,
    dry_run: bool,
):
    """
    Compare Hetzner and Mikrotik records of the given zones and apply the difference.
    Records belonging to other zones are left untouched.
    """
    local_records = {
        uid: record
        for uid, record in get_mikrotik_dns_records(static_dns, sync_record_types).items()
        if find_zone(record.name, all_zones) in sync_zone_names
    }
    remote_records = get_hetzner_dns_records(dns_api, sync_zone_names, sync_record_types)

    # Compare records
    local_records_uids = set(local_records.keys())
    remote_records_uids = set(remote_records.keys())
    click.echo(f"Found {len(remote_records.values())} remote records")
    for record in sorted(remote_records.values(), key=record_sort_key):
        click.echo("- " + str(record))
    click.echo(f"Found {len(local_records.values())} local records")
    for record in sorted(local_records.values(), key=record_sort_key):
        click.echo("- " + str(record))

    # Remove records that are not in remote
    records_to_remove = local_records_uids - remote_records_uids
    click.echo(f"Removing {len(records_to_remove)} records")
    for record_uid in records_to_remove:
        record = local_records[record_uid]
        click.echo(f"Removing record {record}{' (dry run)' if dry_run else ''}")
        if not dry_run:
            remove_record(static_dns, record)

    # Add missing records
    records_to_add = remote_records_uids - local_records_uids
    click.echo(f"Adding {len(records_to_add)} records")
    for record_uid in records_to_add:
        record = remote_records[record_uid]
        click.echo(f"Adding record {record} {' (dry run)' if dry_run else ''}")
        if not dry_run:
            add_record(static_dns, record, ttl)


def record_sort_key(record: Record) -> tuple[str, str, str]:
    """
    Sort records by type, then name, then value
    """
    return (record.record_type, record.name, record.value or "")


def find_zone(name: str, zones: list[str]) -> str | None:
    """
    Find the zone a record name belongs to. The longest matching zone wins, so records of a
    subzone are not attributed to its parent zone.
    """
    matches = [zone for zone in zones if name == zone or name.endswith("." + zone)]
    return max(matches, key=len, default=None)


def add_record(static_dns_resource: RouterOsResource, record: Record, ttl: int):
    """
    Add a DNS record to Mikrotik RouterOS
    """

    match record.record_type:
        case "A" | "AAAA":
            static_dns_resource.add(
                name=record.name,
                address=record.value,
                type=record.record_type,
                ttl=str(ttl),
                comment=MIKROTIK_RECORD_COMMENT,
            )
        case "CNAME":
            static_dns_resource.add(
                name=record.name,
                cname=record.value,
                type=record.record_type,
                ttl=str(ttl),
                comment=MIKROTIK_RECORD_COMMENT,
            )


def remove_record(static_dns_resource: RouterOsResource, record: Record):
    """
    Remove a DNS record from Mikrotik RouterOS
    """

    match record.record_type:
        case "A" | "AAAA":
            resources = static_dns_resource.get(
                name=record.name, type=record.record_type, address=record.value, comment=MIKROTIK_RECORD_COMMENT
            )
        case "CNAME":
            resources = static_dns_resource.get(
                name=record.name, type=record.record_type, cname=record.value, comment=MIKROTIK_RECORD_COMMENT
            )
    for resource in resources:
        static_dns_resource.remove(id=resource["id"])


def get_mikrotik_dns_records(static_dns_resource: RouterOsResource, sync_record_types: list[str]) -> dict[str, Record]:
    """
    Fetch DNS records from Mikrotik RouterOS
    """
    result_records = {}

    for recordraw in static_dns_resource.call("print"):

        if recordraw["type"] not in sync_record_types:
            continue
        if recordraw.get("comment", "") != MIKROTIK_RECORD_COMMENT:
            continue
        record = Record(record_type=recordraw["type"], name=recordraw["name"], ttl=recordraw["ttl"])
        match record.record_type:
            case "A" | "AAAA":
                record.value = recordraw["address"]
            case "CNAME":
                record.value = recordraw["cname"]

        result_records[record.get_uid()] = record
    return result_records


def get_hetzner_dns_records(
    dns_api: HetznerApi, sync_zone_names: list[str], sync_record_types: list[str]
) -> dict[str, Record]:
    """
    Fetch DNS records from Hetzner DNS API
    """

    result_records = {}
    remote_zones = dns_api.list_zones_v1()
    for zone in remote_zones["zones"]:
        if zone["name"] not in sync_zone_names:
            continue

        page = 1
        while True:
            rrset_response = dns_api.list_rrsets_v1(zone["id"], page=page)
            for rrset in rrset_response["rrsets"]:
                if rrset["type"] not in sync_record_types:
                    continue

                for rrset_record in rrset["records"]:
                    record = Record(
                        record_type=rrset["type"],
                        name=zone["name"] if rrset["name"] == "@" else rrset["name"] + "." + zone["name"],
                        value=rrset_record["value"],
                        ttl=rrset_record.get("ttl"),
                    )

                    if record.record_type == "CNAME":
                        # Normalize CNAME records
                        if record.value.endswith("."):
                            record.value = record.value[:-1]
                        else:
                            record.value = record.value + "." + zone["name"]

                result_records[record.get_uid()] = record

            if rrset_response["meta"]["pagination"]["next_page"] is None:
                break
            page += 1

    return result_records


if __name__ == "__main__":
    main()
