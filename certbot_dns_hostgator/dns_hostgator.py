#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import configparser
import dns.resolver

# Load configuration from hostgator.ini
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "hostgator.ini"))

CPANEL_USER = config["cpanel"]["user"]
CPANEL_TOKEN = config["cpanel"]["token"]
DOMAIN = config["cpanel"]["domain"]
CPANEL_HOST = config["cpanel"]["host"]
CPANEL_API = f"https://{CPANEL_HOST}:2083/json-api/cpanel"

# Environment variables provided by Certbot
dns_domain = os.environ.get("CERTBOT_DOMAIN")
dns_token = os.environ.get("CERTBOT_VALIDATION")

# Build correct record name (handles subdomains)
record_name = "_acme-challenge"
if dns_domain != DOMAIN:
    subdomain = dns_domain.replace(f".{DOMAIN}", "")
    record_name = f"_acme-challenge.{subdomain}"

print(f"[+] Managing DNS for domain: {dns_domain}")
print(f"[+] TXT record value to be added: {dns_token}")
print(f"[+] Record name used: {record_name}")

# Save the TXT token as a simple string in a .json file (for reference)
with open("/tmp/value_record.json", "w") as f:
    f.write(dns_token)

# Add TXT record via cPanel API
curl_cmd = [
    "curl", "-k", "-X", "GET", CPANEL_API,
    "-H", f"Authorization: cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
    "-G",
    "--data-urlencode", f"cpanel_jsonapi_user={CPANEL_USER}",
    "--data-urlencode", "cpanel_jsonapi_apiversion=2",
    "--data-urlencode", "cpanel_jsonapi_module=ZoneEdit",
    "--data-urlencode", "cpanel_jsonapi_func=add_zone_record",
    "--data-urlencode", f"domain={DOMAIN}",
    "--data-urlencode", f"name={record_name}",
    "--data-urlencode", "type=TXT",
    "--data-urlencode", f"txtdata={dns_token}",
    "--data-urlencode", "ttl=60"
]

try:
    result = subprocess.run(curl_cmd, check=True, capture_output=True, text=True)
    print("[+] API response:\n", result.stdout)
except subprocess.CalledProcessError as e:
    print("[-] Failed to call cPanel API:")
    print(e.stderr)
    sys.exit(1)

# Wait until the TXT record propagates to DNS
def wait_for_dns_record(fqdn, expected_value, timeout=180, interval=10):
    print(f"[*] Waiting for TXT record {fqdn} to propagate...")
    for _ in range(timeout // interval):
        try:
            answers = dns.resolver.resolve(fqdn, 'TXT')
            for rdata in answers:
                if expected_value in str(rdata):
                    print("[+] TXT record found in DNS!")
                    return True
        except Exception:
            pass
        time.sleep(interval)
    print("[-] TXT record did not propagate in time.")
    return False

fqdn_check = f"_acme-challenge.{dns_domain}".strip(".")
if not wait_for_dns_record(fqdn_check, dns_token):
    print("[-] DNS propagation check failed. Exiting.")
    sys.exit(1)
