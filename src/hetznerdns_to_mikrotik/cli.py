import click
import routeros_api
from routeros_api.resource import RouterOsResource
from hetznerdns_to_mikrotik.hetzner import DnsApi
from hetznerdns_to_mikrotik.model import Record

MIKROTIK_RECORD_COMMENT = "hetznerdns_to_mikrotik"

@click.group()
def main():
    pass

@main.command()
@click.option('--api-token', "-a", help='Hetzner DNS API key', required=True, envvar='API_TOKEN')
@click.option('--zones', "-z", help='Comma separated list of zones to sync', required=True, envvar='ZONES')
@click.option('--record-types', "-r", help='Comma separated list of record types to sync', default="A,AAAA,CNAME", envvar='RECORD_TYPES')
@click.option('--ttl', "-t", help='TTL for local records', default=600, envvar='TTL')
@click.option('--user', "-u", help='Mikrotik User', required=True, envvar='USER')
@click.option('--password', "-p", help='Mikrotik Password', required=True, envvar='PASSWORD')
@click.option('--mikrotik', "-m", help='Mikrotik Host', required=True, envvar='MIKROTIK')
def sync(api_token: str, zones: str, record_types: str, ttl: str, mikrotik: str, user: str, password: str):
    # Filter options
    sync_zone_names = zones.split(',') if zones else None
    sync_record_types = record_types.split(',') if record_types else None

    # Get records from Mikrotik
    mikrotik_api = routeros_api.RouterOsApiPool(host=mikrotik, username=user, password=password, plaintext_login=True, use_ssl=True).get_api()
    static_dns = mikrotik_api.get_resource('/ip/dns/static')
    local_records = get_mikrotik_dns_records(static_dns, sync_zone_names, sync_record_types)

    # Get records from Hetzner DNS
    dns_api = DnsApi(api_token)
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
        click.echo(f"Removing record {record}")
        remove_record(static_dns, record)

    # Add missing records
    records_to_add = remote_records_uids - local_records_uids
    click.echo(f"Adding {len(records_to_add)} records")
    for record_uid in records_to_add:
        record = remote_records[record_uid]
        click.echo(f"Adding record {record}")
        add_record(static_dns, record, ttl)

def add_record(static_dns_resource: RouterOsResource, record: Record, ttl: int):
    match record.record_type:
        case 'A' | 'AAAA':
            static_dns_resource.add(name=record.name, address=record.content, type=record.record_type, ttl=str(ttl), comment=MIKROTIK_RECORD_COMMENT)
        case 'CNAME':
            static_dns_resource.add(name=record.name, cname=record.content, type=record.record_type, ttl=str(ttl), comment=MIKROTIK_RECORD_COMMENT)

def remove_record(static_dns_resource: RouterOsResource, record: Record):
    match record.record_type:
        case 'A' | 'AAAA':
            resources = static_dns_resource.get(name=record.name, type=record.record_type, address=record.content, comment=MIKROTIK_RECORD_COMMENT)
        case 'CNAME':
            resources = static_dns_resource.get(name=record.name, type=record.record_type, cname=record.content, comment=MIKROTIK_RECORD_COMMENT)
    for resource in resources:
        static_dns_resource.remove(id=resource['id'])

def get_mikrotik_dns_records(static_dns_resource: RouterOsResource, sync_zone_names: str, sync_record_types: str) -> dict[str, Record]:
        result_records = {}

        for recordraw in static_dns_resource.call('print'):

            if recordraw['type'] not in sync_record_types:
                continue
            if recordraw.get('comment', "") != MIKROTIK_RECORD_COMMENT:
                continue
            record = Record(
                record_type=recordraw['type'],
                name=recordraw['name'],
                ttl=recordraw['ttl']
            )
            match record.record_type:
                case 'A' | 'AAAA':
                    record.content = recordraw['address']
                case 'CNAME':
                    record.content = recordraw['cname']
            
            result_records[record.get_uid()] = record
        return result_records

def get_hetzner_dns_records(dns_api: DnsApi, sync_zone_names: str, sync_record_types: str) -> dict[str, Record]:
    result_records = {}
    remote_zones = dns_api.get_zones_v1()
    for zone in remote_zones["zones"]:
        if zone['name'] not in sync_zone_names:
            continue

        records = dns_api.get_records_v1(zone['id'])
        for record in records['records']:
            if record['type'] not in sync_record_types:
                continue

            record = Record(
                record_type=record['type'],
                name=record['name'] + '.' + zone['name'],
                content=record['value'],
                ttl=record.get('ttl')
            )

            result_records[record.get_uid()] = record
    
    return result_records

if __name__ == '__main__':
    main()