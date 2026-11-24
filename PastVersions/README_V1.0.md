# Guild Wars 2 API Downloader (`script_v1.0.py`)

This script is an automated tool designed to discover, fetch, and download data from the official Guild Wars 2 API (`https://api.guildwars2.com`). It systematically pulls endpoint data and saves it locally as structured JSON files.

## Features

* **Endpoint Auto-Discovery:** Automatically queries the `/v2` root to discover and list all exposed API paths and tracks visited endpoints to avoid duplicates.

* **Latest Schema:** Automatically requests the `"latest"` schema version (`X-Schema-Version`) for all API calls to ensure up-to-date data formats.

* **Resilient Fetching & Rate Limit Handling:**

  * The API token refill rate is 5 tokens per second, or 300 per minute. To safely navigate this, the script natively rests for 200ms between requests.

  * Built-in handling for HTTP 429 (Rate Limit) errors by reading the `Retry-After` header and waiting accordingly.

  * Implements exponential backoff (e.g., `time.sleep(2 ** attempts)`) for server-side (500+) or general request errors.

* **Pagination Management:** Automatically paginates through large datasets using a page size of 200 items per request to minimize the total number of requests, staying safely under the API's maximum of 300.

* **Smart Exclusion & Filtering:** By default, it parses endpoint flags to skip unneeded data:

  * **`a` (Auth Required):** Skips endpoints requiring an account authentication key (e.g., `/account`, `/characters`).

  * **`d` (Disabled):** Skips endpoints temporarily disabled by the API.

  * **Search/Parent Endpoints:** Skips endpoints like `guild/search`, `home`, `pvp`, or `mounts` because they require specific search terms or are not needed for this use case and can be derived elsewhere.

  * **Dynamic Data:** Unless overridden, skips endpoints with data that is not static and needs to be updated frequently or on a seasonal basis (e.g., Trading Post commerce, WvW stats, daily achievements, Wizard's Vault).

* **Locale Awareness (`l` flag):** Identifies endpoints supporting localized data and can fetch them in English (`en`), German (`de`), Spanish (`es`), French (`fr`), and Chinese (`zh`) via the `?lang=<langId>` query parameter.

* **Deep Fetching:** Contains specific logic to traverse and download nested endpoints, such as `emblem` sub-categories and `continents/{id}/floors`.

## Usage

Run the script from your command line:

```bash
python script_v1.0.py [options]
```

> **Note:** Due to rate limits and the volume of data, downloading all the base default information can take up to 30 minutes.

### Command-Line Arguments

* `--out`: Specifies the output directory where the JSON files will be saved. **Default:** `gw2_data`.

* `--lang`: A space-separated list of languages to fetch for locale-aware endpoints. **Choices:** `en`, `es`, `de`, `fr`, `zh`. **Default:** `en`.

* `--include-dynamic`: A flag that instructs the script to download dynamic endpoints containing data that refreshes at some point, either seasonal or daily.

### Examples

**Basic Run (English only, default folder, no dynamic endpoints):**

```bash
python script_v1.0.py
```

**Fetch multiple languages into a custom folder:**

```bash
python script_v1.0.py --out ./my_gw2_archive --lang en es de
```

**Fetch everything, including dynamic data (e.g., Trading Post, WvW):**

```bash
python script_v1.0.py --include-dynamic
```

## Output Structure

When the script runs, it organizes the downloaded JSON files into specific subdirectories within your chosen output folder:

* **`common/`**: Stores data from language-independent endpoints.

* **Locale Folders (`en/`, `es/`, etc.)**: Stores data from locale-aware endpoints. A separate folder is generated for every language passed to the `--lang` argument.

Files are named based on their API path, with any slashes (`/`) replaced by double underscores (`__`) to maintain a flat file structure within the directories. For example, the `/v2/continents/1/floors` endpoint will be saved as `continents__1__floors.json`.

At the end of execution, the script calculates and outputs the total elapsed time formatted in `HH:MM:SS`.

---
*Note: This script requires Python 3 and the `requests` library. You can install the required dependency via pip: `pip install requests`.*