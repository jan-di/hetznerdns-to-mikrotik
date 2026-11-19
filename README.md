# HetznerDNS to MikroTik

This project allows you to synchronize DNS records from Hetzner Cloud DNS to a MikroTik router. It automates the process of updating MikroTik's DNS settings based on the records in your Hetzner DNS account.

## Features

- Synchronizes dns zones from Hetzner DNS to MikroTik.
- Supported Record types: A, AAAA, CNAME
- Supports filtering by zone names.

## Requirements

- Python 3.15 or higher
- MikroTik router with API access enabled
- Hetzner DNS API token

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/yourusername/hetznerdns-to-mikrotik.git
    cd hetznerdns-to-mikrotik
    ```

2. Install the required Python packages:

    ```sh
    uv sync
    ```

Package will probably be published on pypi later.

## Usage

To use the script, you can run the following command:

```sh
python hdns2mikrotik [arguments]
```

### Arguments

All arguments can be specified on command line or environment variables.

- `--api-token` (required): Your Hetzner DNS API token.
- `--mikrotik` (required): The hostname or IP address of your MikroTik router.
- `--user` (required): The username for MikroTik API access.
- `--password` (required): The password for MikroTik API access.
- `--zones` (optional): Comma-separated list of DNS zones to synchronize. If not specified, all zones will be synchronized.
- `--record-types` (optional): Comma-separated list of DNS record types to synchronize (default: A, AAAA, CNAME).

- `--watch` / `-w` (optional): Keep running and re-sync periodically instead of exiting after one sync. A zone is only re-synced when its SOA serial changed since the last successful sync, a failed sync is retried on the next iteration.
- `--watch-interval` (optional): Seconds between syncs in watch mode (default: 600).
- `--nameservers` (optional): Comma or space separated Hetzner nameservers, one of which is picked at random to read the SOA serial in watch mode (default: the three Hetzner nameservers; env `HETZNER_NAMESERVERS`).
- `--healthchecksio-url` (optional): Healthchecks.io-style base URL. Pinged at `<url>/start` before each sync, `<url>` on success and `<url>/fail` on failure.

Example usage:

```sh
hdns2mikrotik --api-token your_token --mikrotik 192.168.88.1 --user hdns2mikrotik --password your_password --zones example.com,example.org --record-types A,AAAA
```

## MikroTik user

The tool connects to the RouterOS API over SSL (`api-ssl`, port 8729), so the `api-ssl` service must be enabled with a certificate assigned. It reads, adds and removes entries under `/ip/dns/static`, so the user needs only these policies: `api`, `read` and `write`.

Create a dedicated group and user instead of using `admin`:

```
/user group add name=hdns2mikrotik policy=api,read,write
/user add name=hdns2mikrotik group=hdns2mikrotik password=<password> address=<ip-of-the-host-running-this-tool>
```

The `address` option restricts logins to the machine running the sync. RouterOS policies are not path-specific, so `write` allows changes beyond DNS. The tool only touches static DNS entries whose comment is `hetznerdns_to_mikrotik`, other entries are left alone.

## Docker

The image runs `sync` in watch mode by default (`WATCH=true`), so it keeps running and re-syncs when a zone's serial changes. Configuration is done via environment variables, see [.env.example](.env.example).

```sh
docker run -d --env-file .env docker.io/jandi/hetznerdns-to-mikrotik:latest
```

A hardened setup is shown in [compose.example.yaml](compose.example.yaml).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or support, please open an issue on the GitHub repository.
