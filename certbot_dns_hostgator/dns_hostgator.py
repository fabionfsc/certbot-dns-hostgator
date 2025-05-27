#!/usr/bin/env python3

import os
import subprocess
import time
import configparser

# Load external configuration file located in the same directory as the script
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "hostgator.ini"))

CPANEL_USER = config["cpanel"]["user"]
CPANEL_TOKEN = config["cpanel"]["token"]
DOMAIN = config["cpanel"]["domain"]
CPANEL_HOST = config["cpanel"]["host"]
CPANEL_API = "https://{CPANEL_HOST}:2083/json-api/cpanel"

# Retrieve data provided by Certbot via environment variables
dns_domain = os.environ.get("CERTBOT_DOMAIN")
dns_token = os.environ.get("CERTBOT_VALIDATION")
record_name = "_acme-challenge"

# Debug output for tracking variables
print(f"[+] Managing DNS for domain: {dns_domain}")
print(f"[+] TXT record value to be added: {dns_token}")

# Construct the curl command to add a TXT record via cPanel API
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

# Execute the curl command and handle potential errors
try:
    result = subprocess.run(curl_cmd, check=True, capture_output=True, text=True)
    print("[+] API response:\n", result.stdout)
except subprocess.CalledProcessError as e:
    print("[-] Failed to call cPanel API:")
    print(e.stderr)
    exit(1)

# Pause to allow DNS record propagation
print("[*] Waiting for DNS propagation...")
time.sleep(30)
