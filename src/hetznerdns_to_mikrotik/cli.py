"""
CLI for hetznerdns-to-mikrotik
"""

import click
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
def sync(
    api_token: str,
    zones: str,
    record_types: str,
    ttl: int,
    mikrotik: str,
    user: str,
    password: str,
    dry_run: bool,
):
    """
    Sync Hetzner DNS records to Mikrotik RouterOS
    """

    # Filter options
    sync_zone_names = zones.split(",")
    sync_record_types = record_types.split(",")

    # Get records from Mikrotik
    mikrotik_api = routeros_api.RouterOsApiPool(
        host=mikrotik, username=user, password=password, plaintext_login=True, use_ssl=True
    ).get_api()
    static_dns = mikrotik_api.get_resource("/ip/dns/static")
    local_records = get_mikrotik_dns_records(static_dns, sync_record_types)

    # Get records from Hetzner DNS
    dns_api = HetznerApi(api_token)
    remote_records = get_hetzner_dns_records(dns_api, sync_zone_names, sync_record_types)

    # Compare records
    local_records_uids = set(local_records.keys())
    remote_records_uids = set(remote_records.keys())
    click.echo(f"Found {len(remote_records.values())} remote records")
    for record in remote_records.values():
        click.echo("- " + str(record))
    click.echo(f"Found {len(local_records.values())} local records")
    for record in local_records.values():
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
                        name=rrset["name"] + "." + zone["name"],
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
