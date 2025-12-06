# HetznerDNS to MikroTik

This project allows you to synchronize DNS records from Hetzner Cloud DNS to a MikroTik router. It automates the process of updating MikroTik's DNS settings based on the records in your Hetzner DNS account.

## Features

- Synchronizes dns zones from Hetzner DNS to MikroTik.
- Supported Record types: A, AAAA, CNAME
- Supports filtering by zone names.

## Requirements

- Python 3.14 or higher
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
python hdns2mikrotik [arguments]
```

### Arguments

All arguments can be specified on command line or environment variables.

- `--api-token` (required): Your Hetzner DNS API token.
- `--mikrotik` (required): The hostname or IP address of your MikroTik router.
- `--username` (required): The username for MikroTik API access.
- `--password` (required): The password for MikroTik API access.
- `--zones` (optional): Comma-separated list of DNS zones to synchronize. If not specified, all zones will be synchronized.
- `--record-types` (optional): Comma-separated list of DNS record types to synchronize (default: A, AAAA, CNAME).

Example usage:

```sh
hdns2mikrotik --api-token your_token --mikrotik 192.168.88.1 --username admin --password your_password --zones example.com,example.org --record-types A,AAAA
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or support, please open an issue on the GitHub repository.
