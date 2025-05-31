
# certbot-dns-hostgator

A minimal Certbot DNS-01 automation solution for HostGator cPanel using the JSON API.  
This repository contains two scripts:
1. **dns_hostgator.py** – Automates the creation of the `_acme-challenge` TXT record for Let's Encrypt DNS-01 challenges.  
2. **dns_cleanup.py** – Removes the `_acme-challenge` TXT record previously created by `dns_hostgator.py`.

## Description

- **dns_hostgator.py**:  
  - Parses the domain from `hostgator.ini` for automatic zone detection.  
  - Adds a TXT record via HostGator's cPanel JSON API based on the `CERTBOT_DOMAIN` and `CERTBOT_VALIDATION` environment variables provided by Certbot.  
  - Automatically detects authoritative nameservers for the domain using a `dig` query.  
  - Waits for DNS propagation using the authoritative NS IPs, ensuring accurate and fast validation.  
  - Saves the validation token temporarily to `/tmp/value_record.json`.

- **dns_cleanup.py**:  
  - Reads the validation token from `/tmp/value_record.json`.  
  - Fetches all TXT records in the DNS zone using cPanel's `fetchzone_records` API call.  
  - Filters the records to find the one matching the token.  
  - Removes the matching record via cPanel's `remove_zone_record` API call.  
  - Cleans up temporary files (`/tmp/value_record.json`, `/tmp/zone_records_raw.json`, `/tmp/zone_records_formatted.json`).

## Features

- Adds and removes `_acme-challenge` TXT records automatically.  
- Automatically resolves NS IPs for accurate DNS propagation checks.  
- Supports wildcard certificates.  
- Simple configuration via `hostgator.ini`.  
- No external dependencies beyond `curl`, `python3`, and `python3-dnspython`.

## Requirements

- Python 3  
- `curl` installed  
- A HostGator account with:  
  - cPanel access  
  - An API token with DNS zone edit permissions

## Dependencies

Before running the scripts, install the following package for DNS checks:

```bash
sudo apt update && sudo apt install python3-dnspython -y
```

> **Note**: `python3-dnspython` is required to validate DNS propagation using Python's `dns.resolver`.

## Setup

1. Clone this repository:

    ```bash
    git clone https://github.com/fabionfsc/certbot-dns-hostgator.git
    cd certbot-dns-hostgator
    ```

2. Edit the configuration file `hostgator.ini` in the same directory:

    ```ini
    [cpanel]
    user = your_cpanel_username
    token = your_cpanel_api_token
    domain = yourdomain.com
    host = yourcpanel.hostgator.com.br
    ```

    > **Warning**: Do **not** commit `hostgator.ini` to any public repository. It contains sensitive credentials.

3. Make both scripts executable:

    ```bash
    chmod +x dns_hostgator.py dns_cleanup.py
    ```

## Usage

### 1. Adding the TXT record

Run Certbot with `dns_hostgator.py` as the manual authentication hook:

```bash
certbot certonly --manual --preferred-challenges dns --manual-auth-hook "/full/path/to/dns_hostgator.py" -d '*.yourdomain.com' --agree-tos --no-eff-email --email your.email@example.com
```

- `dns_hostgator.py` will:
  - Add `_acme-challenge.<subdomain>` TXT record using the cPanel API.
  - Automatically resolve NS IPs and check propagation against them.
  - Wait until the TXT record is resolvable before Certbot proceeds.

### 2. Cleaning up the TXT record

After Certbot completes validation, run:

```bash
python3 /full/path/to/dns_cleanup.py
```

- `dns_cleanup.py` will:
  - Read the validation token from `/tmp/value_record.json`.
  - Fetch all TXT records in your DNS zone.
  - Find and delete the matching record.
  - Remove temporary files (`/tmp/value_record.json`, `/tmp/zone_records_raw.json`, `/tmp/zone_records_formatted.json`).

## Notes

- Both scripts rely purely on cPanel's JSON API via HTTP `curl` calls.
- If DNS propagation is slow, increase the timeout or interval inside `dns_hostgator.py`.
- Ensure that your API token has permission to edit DNS zones.
- The script automatically detects the correct DNS zone and resolves the authoritative nameservers.

## Example Workflow

1. **Request certificate** (adds TXT record and waits for propagation):

    ```bash
    certbot certonly --manual --preferred-challenges dns --manual-auth-hook "/home/user/certbot-dns-hostgator/certbot_dns_hostgator/dns_hostgator.py" -d 'webmail.yourdomain.com' --agree-tos --no-eff-email --email user@example.com
    ```

2. **Remove the validation TXT record**:

    ```bash
    python3 /home/user/certbot-dns-hostgator/dns_cleanup.py
    ```

## Disclaimer

This project is unofficial and not affiliated with HostGator.
