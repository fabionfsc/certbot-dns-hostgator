# certbot-dns-hostgator

A minimal Certbot DNS-01 automation script for HostGator cPanel using the JSON API.

## Description

This script automates the creation of the `_acme-challenge` TXT record required for the Let's Encrypt DNS-01 challenge. It's designed to be used with Certbot's `--manual-auth-hook` option. Cleanup is not included by design — records must be manually removed if desired.

## Features

- Adds a TXT record via HostGator's cPanel JSON API
- Works with wildcard certificates
- Simple configuration via `.ini` file
- No external dependencies beyond `curl` and `python3`

## Requirements

- Python 3
- `curl` installed
- A HostGator account with:
  - cPanel access
  - An API token with DNS zone edit permissions

## Setup

1. Clone this repository:

```bash
git clone https://github.com/yourusername/certbot-dns-hostgator.git
cd certbot-dns-hostgator
```

2. Create a configuration file named `hostgator.ini` in the same directory:

```ini
[cpanel]
user = your_cpanel_username
token = your_cpanel_api_token
domain = yourdomain.com
host = yourcpanel.hostgator.com.br
```

> ⚠️ Do **not** commit this file to any public repository.

3. Make the script executable:

```bash
chmod +x dns_hostgator.py
```

## Usage

Run Certbot using the script as the authentication hook:

```bash
certbot certonly \
  --manual \
  --preferred-challenges dns \
  --manual-auth-hook "/full/path/to/dns_hostgator.py" \
  -d '*.yourdomain.com' \
  --agree-tos \
  --no-eff-email \
  --email your.email@example.com
```

## Notes

- The script **does not** implement `manual-cleanup`. DNS records will persist unless manually deleted via the cPanel interface or API.
- You can increase the sleep timer if your DNS takes longer to propagate.

## Disclaimer

This project is unofficial and not affiliated with HostGator. Use at your own risk.

---