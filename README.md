# HetznerDNS to MikroTik

This project allows you to synchronize DNS records from Hetzner DNS to a MikroTik router. It automates the process of updating MikroTik's DNS settings based on the records in your Hetzner DNS account.

## Features

- Synchronizes various record types (defaults to A, AAAA, and CNAME) from Hetzner DNS to MikroTik.
- Supports filtering by zone names.

## Requirements

- Python 3.13 or higher
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
    poetry install
    ```

Package will probably be published on pypi later.

## Usage

To use the script, you can run the following command:

```sh
python sync_dns.py [arguments]
```

### Arguments

All arguments can be specified on command line or environment variables.

- `--hetzner-token` (required): Your Hetzner DNS API token.
- `--mikrotik-host` (required): The hostname or IP address of your MikroTik router.
- `--mikrotik-user` (required): The username for MikroTik API access.
- `--mikrotik-password` (required): The password for MikroTik API access.
- `--zones` (optional): Comma-separated list of DNS zones to synchronize. If not specified, all zones will be synchronized.
- `--record-types` (optional): Comma-separated list of DNS record types to synchronize (default: A, AAAA, CNAME).
- `--interval` (optional): Interval in seconds between synchronization runs (default: 300).

Example usage:

```sh
hdns2mikrotik --hetzner-token your_token --mikrotik-host 192.168.88.1 --mikrotik-user admin --mikrotik-password your_password --zones example.com,example.org --record-types A,AAAA --interval 600
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or support, please open an issue on the GitHub repository.
