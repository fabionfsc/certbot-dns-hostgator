#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import configparser

# Paths
TOKEN_FILE = "/tmp/value_record.json"
RAW_OUTPUT = "/tmp/zone_records_raw.json"
FORMATTED_OUTPUT = "/tmp/zone_records_formatted.json"

# Load configuration from hostgator.ini
config_path = os.path.join(os.path.dirname(__file__), "hostgator.ini")
config = configparser.ConfigParser()
config.read(config_path)

try:
    CPANEL_USER = config["cpanel"]["user"]
    CPANEL_TOKEN = config["cpanel"]["token"]
    DOMAIN = config["cpanel"]["domain"]
    CPANEL_HOST = config["cpanel"]["host"]
except KeyError as e:
    print(f"[-] Missing config value: {e}")
    sys.exit(1)

CPANEL_API = f"https://{CPANEL_HOST}:2083/json-api/cpanel"

# Read the token value
if not os.path.isfile(TOKEN_FILE):
    print(f"[-] Token file not found: {TOKEN_FILE}")
    sys.exit(1)

with open(TOKEN_FILE, "r") as f:
    token = f.read().strip()

print(f"[+] Looking for TXT record with token: {token}")

# Step 1: Fetch all TXT zone records via fetchzone_records
curl_fetchzone = [
    "curl", "-ks",
    "-H", f"Authorization: cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
    "-G", CPANEL_API,
    "--data-urlencode", f"cpanel_jsonapi_user={CPANEL_USER}",
    "--data-urlencode", "cpanel_jsonapi_apiversion=2",
    "--data-urlencode", "cpanel_jsonapi_module=ZoneEdit",
    "--data-urlencode", "cpanel_jsonapi_func=fetchzone_records",
    "--data-urlencode", f"domain={DOMAIN}",
    "--data-urlencode", "type=TXT"
]

try:
    # Save raw output to file
    with open(RAW_OUTPUT, "wb") as raw_f:
        subprocess.run(curl_fetchzone, check=True, stdout=raw_f)
    with open(RAW_OUTPUT, "r") as raw_f:
        data = json.load(raw_f)
except subprocess.CalledProcessError as e:
    print(f"[-] Failed to fetch zone records: {e}")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"[-] Failed to parse JSON: {e}")
    print("[DEBUG] Raw output:")
    with open(RAW_OUTPUT, "r") as raw_f:
        print(raw_f.read())
    sys.exit(1)

# Extract records list
try:
    records = data["cpanelresult"]["data"]
    if not isinstance(records, list):
        print("[-] Unexpected data structure: 'data' is not a list")
        sys.exit(1)
except KeyError:
    print("[-] Unexpected JSON structure, 'data' missing")
    sys.exit(1)

# Step 2: Format and save filtered records for clarity
formatted = []
for rec in records:
    if isinstance(rec, dict) and rec.get("type") == "TXT":
        formatted.append({
            "line": rec.get("line"),
            "name": rec.get("name"),
            "txtdata": rec.get("txtdata"),
            "ttl": rec.get("ttl")
        })

with open(FORMATTED_OUTPUT, "w") as fmt_f:
    json.dump(formatted, fmt_f, indent=2)

print(f"[+] Formatted TXT records saved to {FORMATTED_OUTPUT}")

# Step 3: Find matching TXT record
target_line = None
for rec in formatted:
    if rec.get("txtdata") == token:
        target_line = rec.get("line")
        print(f"[+] Found matching TXT record: name={rec.get('name')}, line={target_line}")
        break

if not target_line:
    print("[-] No matching TXT record found.")
    sys.exit(1)

# Step 4: Delete the matching TXT record by line
curl_delete = [
    "curl", "-ks",
    "-H", f"Authorization: cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
    "-G", CPANEL_API,
    "--data-urlencode", f"cpanel_jsonapi_user={CPANEL_USER}",
    "--data-urlencode", "cpanel_jsonapi_apiversion=2",
    "--data-urlencode", "cpanel_jsonapi_module=ZoneEdit",
    "--data-urlencode", "cpanel_jsonapi_func=remove_zone_record",
    "--data-urlencode", f"domain={DOMAIN}",
    "--data-urlencode", f"line={target_line}"
]

try:
    result = subprocess.check_output(curl_delete, stderr=subprocess.STDOUT, text=True)
    print(f"[+] Delete API response:\n{result}")
except subprocess.CalledProcessError as e:
    print(f"[-] Failed to delete TXT record: {e.output}")
    sys.exit(1)

# === BEGIN: Temporary files cleanup ===
for file_path in [TOKEN_FILE, RAW_OUTPUT, FORMATTED_OUTPUT]:
    try:
        os.remove(file_path)
        print(f"[+] Removed temporary file: {file_path}")
    except FileNotFoundError:
        # File already deleted or never created; ignore
        pass
    except Exception as e:
        print(f"[-] Failed to remove {file_path}: {e}")
# === END: Temporary files cleanup ===

print("[+] Cleanup complete.")
