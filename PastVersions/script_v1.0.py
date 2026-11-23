"""
This a past version of the script before implementing the GUI and options to download optional stuff
It works but won't download any dynamic endpoint and has now way to downalod any of them without 
removing them from the DYNAMIC_ENDPOINT tuples
"""

import json
import time # have a rest time between requests to avoid rate limiting
import sys
import argparse
import re
import requests # to make http requests to the API
import traceback 
from pathlib import Path # build files and folders

start = time.time() # Start a timer

API = "https://api.guildwars2.com"
PAGE_SIZE = 200 # The maximum page size for the API is 300, so we will use that to minimize the number of requests we need to make
                # The refill rate for tokens is 5 tokens per second, 300 per minute


# Endpoints in which data is not static and needs to be updated frequently or on a seasonal basis.
DYNAMIC_ENDPOINTS = (
    "commerce/",
    "wvw/matches",
    "wvw/guilds",
    "wvw/timers",
    "achievements/daily",
    "events-state",
    "wizardsvault"
)

# Endpoint flags -
# a - needs a auth key
# d - disabled for now
# l - You can pass a specific language ID using the query parameter ?lang=<langId> at the end of the API URL
#   includ: en, de, es, fr, zh

ALWAYS_SKIP_FLAGS = {"a", "d"}

# The following endpoints awlays require a auth key
AUTH_PREFIXES = (
    "account",
    "characters"
)

# Never Fetch these endpoints, they are not needed for our use case and can be gotten from other endpoints.
NEVER_FETCH = {
    "guild/search",
    "recipes/search",
    "home",
    "mounts",
    "pvp",
    "homestead",
}


session = requests.Session()
session.headers["X-Schema-Version"] = "latest" # Get the latest version

def get(path, **params):
    url = f"{API}/{path.lstrip('/')}"

    for attempts in range(6):
        try:
            output = session.get(url, params=params, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching ({e}), retrying...", file=sys.stderr)
            time.sleep(2 ** attempts)  # Exponential backoff
            
            continue
        if output.status_code == 429:
            wait = int(output.headers.get("Retry-After", 15))
            print(f"Rate limited, waiting {wait}, seconds...")
            time.sleep(wait)
            
            continue

        if output.status_code >= 500:
            print(f"Serever error ({output.status_code}), retrying...", file=sys.stderr)
            time.sleep(2 ** attempts)

            continue
        time.sleep(0.2) # Sleep for 200ms to avoid rate limiting
        return output.status_code, output
    return 0, None

def fetch(path, **params):
    status, output = get(path, **params)
    if output is None:
        return status,None, {}
    try:
        return status, output.json(), output.headers
    except ValueError:
        return status, None, output.headers

def list_endpoint(): # Discovers and lists all available enpoints
    
    status, output = get("v2")

    if status != 200 or output is None: #Check if request was successful.
        sys.exit(f"Could not fetch endpoint list, status code: {status}")

    seen, endpoints = set(), [] # seen tracks enpoints visited, enpoints stores the endpoints and their flags
    in_list = False 

    for line in output.text.splitlines():
        if "paths are exposed" in line:
            in_list = True
            continue

        if not in_list:
            continue

        if line.startswith("Key:"):
            break

        m = re.match(r"\s*/v2/(\S+)(?:\s+\[([a-z,]+)\])?\s*$", line)
        if not m:
            continue

        path = m.group(1)
        flags = {f.strip() for f in m.group(2).split(",")} if m.group(2) else set()

        if path not in seen:
            seen.add(path)
            endpoints.append((path, flags))

    return endpoints

def fetch_all(path, ids, lang):
    status, body, headers = fetch(path, page=0, page_size=PAGE_SIZE, lang = lang)

    if status == 200 and isinstance(body, list) and "X-Page-Total" in headers:
        results = list(body)
        total_pages = int(headers["X-Page-Total"])

        for page in range(1, total_pages):
            status, body, headers = fetch(path, page=page, page_size=PAGE_SIZE, lang = lang)

            if status != 200 or not isinstance(body, list):
                print(f"Error fetching page {page} of {path}, status code: {status}", file=sys.stderr)
                break

            results.extend(body)
        return results

    results = []

    for i in range (0, len(ids), PAGE_SIZE):
        chunk = ids[i:i + PAGE_SIZE]
        status, body, headers = fetch(path, ids=",".join(map(str, chunk)), lang = lang)

        if status == 200 and isinstance(body, list):
            results.extend(body)

        else:
            return ids
    return results

# Build Path
def out_file(folder, name):
    return folder / f"{name.replace('/', '__')}.json"

# Save data to json file and stores them 
def save(folder, name, data):
    out_file(folder, name).write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
    )

def download(name, folder, lang):
    if out_file(folder, name).exists():
        print(f" = {name}: already downloaded")
        return False

    status, body, _ = fetch(f"/v2/{name}", lang=lang)
    if status != 200 or body is None:
        print(f"    - {name}: skipped (status {status})")
        return False

    if isinstance(body, list) and body:
        body = fetch_all(f"/v2/{name}", body, lang)

    save(folder, name, body)
    count = len(body) if isinstance(body,(list, dict)) else 1
    print(f" + {name}: saved ({count} entries)")
    
    return True

def run(langs, out_root, include_dynamic):
    endpoints = list_endpoint()
    print(f"{len(endpoints)} endpoints listed by /v2")

    wanted = []

    for path, flags in endpoints:
        if flags & ALWAYS_SKIP_FLAGS:
            print(f" - {path}: skipped (auth / disabled)")
        
        elif path.startswith(AUTH_PREFIXES):
            print(f" - {path}: skipped (account data)")

        elif ":" in path:
            print(f" - {path}: skipped (needs id)")

        elif path in NEVER_FETCH:
            print(f" - {path}: skipped (parent/ needs search term)")

        elif not include_dynamic and path.startswith(DYNAMIC_ENDPOINTS):
            print(f" - {path}: skipped (dynamic)")

        else: 
            wanted.append((path, "l" in flags ))

    print(f"{len(wanted)} enpoints to download\n")

    common = out_root / "common"
    common.mkdir(parents=True, exist_ok=True)
    print("[common] language-independent endpoints")
    for path, locale_aware in wanted:
        if not locale_aware:
            download(path, common, None)

    status, body, _ = fetch("/v2/emblem")
    if status == 200 and isinstance(body, list):
        for sub in body:
            if isinstance(sub, str):
                download(f"emblem/{sub}", common, None)

    for lang in langs: 
        folder = out_root / lang
        folder.mkdir(parents=True, exist_ok=True)
        print(f"\n[{lang}] locale_aware endpoints")
        
        for path, locale_aware in wanted:
            if locale_aware:
                download(path, folder, lang)

        cont_file = out_file(folder, "continents")
        if cont_file.exists():
            continents = json.loads(cont_file.read_text(encoding="utf-8"))
            for c in continents:
                cid = c["id"] if isinstance(c, dict) else c
                name = f"continents/{cid}/floors"
                if out_file(folder, name).exists():
                    continue
                status, floor_ids, _ = fetch(f"/v2/{name}")
                if status == 200 and isinstance(floor_ids, list):
                    save(folder, name, fetch_all(f"/v2/{name}", floor_ids, lang))
                    print(f" + {name} saved")
                else:
                    print(f" - {name} skipped (status {status})")

class Tee: # Takes output and sends it to both terminal and a log file
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for s in self.streams:
            s.write(text)

    def flush(self):
        for s in self.streams:
            s.flush()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default = "gw2_data", help = "output directory")
    ap.add_argument("--lang", nargs = "+", default = ["en"], 
                    choices = ["en", "es", "de", "fr", "zh"])
    ap.add_argument("--include-dynamic", action = "store_true", 
                    help = "download enpoints which data refreshes at some point eaither seasonal or daily")
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_path = out_root / f"download_log_{stamp}.txt"
    log_file = open(log_path, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stdout = Tee(sys.__stderr__, log_file)
    
    try:
        print(f"Language: {', '.join(args.lang)} | include dynamic: {args.include_dynamic}")
        run(args.lang, Path(args.out), args.include_dynamic)
        print("\nDone.")

    except KeyboardInterrupt:
        print("\nStopped by User")

    except Exception:
        traceback.print_exc() #Crash gets logged in file
    finally:
        # Timer Calculations:
        end = time.time() # End Timer
        elapsed = int(end - start)

        hours = elapsed//3600
        minutes = (elapsed % 3600)//60
        seconds = elapsed % 60

        formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
        print("it took", formatted_time, "time")

        sys.stdout = sys.__stdout__
        sys.stdout = sys.__stderr__
        log_file.close()
        print(f"Log saved to {log_path}")

if __name__ == "__main__":
    main()
    