#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import configparser
import dns.resolver

# Load external configuration from hostgator.ini
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
    # Abort if cPanel API fails
    sys.exit(1)

# Function to fetch authoritative nameserver IPs for a given domain
def get_ns_ips(domain_name):
    """
    Query the NS records for 'domain_name' and resolve each NS hostname to its A record(s).
    Returns a list of IPv4 addresses (strings). If something fails, returns an empty list.
    """
    ips = []
    try:
        # Step 1: Query NS records
        ns_answers = dns.resolver.resolve(domain_name, "NS")
        ns_hosts = [rdata.to_text().rstrip(".") for rdata in ns_answers]
    except Exception as e:
        print(f"[-] Error fetching NS records for {domain_name}: {e}")
        return ips

    # Step 2: Resolve each NS hostname into one or more A records
    for ns_host in ns_hosts:
        try:
            a_answers = dns.resolver.resolve(ns_host, "A")
            for rdata in a_answers:
                ips.append(rdata.to_text())
        except Exception as e:
            print(f"[!] Warning: could not resolve A record for NS {ns_host}: {e}")
            # Continua para o próximo nameserver
            continue

    return ips

# Attempt to get the authoritative nameserver IPs for DOMAIN
auth_ns_ips = get_ns_ips(DOMAIN)

if auth_ns_ips:
    print(f"[+] Found authoritative NS IPs for {DOMAIN}: {auth_ns_ips}")
else:
    print(f"[!] Could not discover authoritative NS IPs for {DOMAIN}. Falling back to public DNS.")
    # Fallback to Google + Cloudflare public DNS
    auth_ns_ips = ["8.8.8.8", "1.1.1.1"]

# Wait until the TXT record propagates to DNS
def wait_for_dns_record(fqdn, expected_value, resolver_ips, timeout=300, interval=10):
    """
    Wait up to 'timeout' seconds for the TXT record 'fqdn' to appear with 'expected_value'.
    Uses the provided resolver_ips list. Returns True if found, False on timeout.
    """
    resolver = dns.resolver.Resolver()
    resolver.nameservers = resolver_ips
    print(f"[*] Waiting for TXT record {fqdn} to propagate (timeout={timeout}s) using {resolver_ips}...")
    max_loops = timeout // interval

    for _ in range(max_loops):
        try:
            answers = resolver.resolve(fqdn, "TXT")
            for rdata in answers:
                if expected_value in str(rdata):
                    print("[+] TXT record found in DNS!")
                    return True
        except Exception:
            # Ignorar qualquer exceção e tentar de novo após sleep
            pass
        time.sleep(interval)

    print("[-] TXT record did not propagate in time.")
    return False

fqdn_check = f"_acme-challenge.{dns_domain}".strip(".")

# If the record doesn't propagate, we opt to continue with exit code 0 (Certbot não vai reclamar)
if not wait_for_dns_record(fqdn_check, dns_token, auth_ns_ips, timeout=300, interval=10):
    print("[-] DNS propagation check failed. Continuing anyway (exit 0).")
    sys.exit(0)

# If we get here, the TXT was encontrado no authoritative NS
sys.exit(0)
