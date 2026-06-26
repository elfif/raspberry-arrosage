# Redis Settings Manager

This project contains scripts to write and read an array of 8 integer values to/from Redis with the key name `settings`.

## Scripts

1. **`redis_settings_writer.py`** - Writes the settings array to Redis
2. **`redis_settings_reader.py`** - Reads and displays the settings array from Redis

## Data Structure

The script creates an array with the following values:
- **First 7 elements**: `3600` (default value)
- **Last element**: `0`

Result: `[3600, 3600, 3600, 3600, 3600, 3600, 3600, 0]`

## Prerequisites

- Python 3.6+
- Redis server running
- Required Python packages (already in your requirements.txt):
  - `redis==5.0.1`

## Configuration

Edit `redis_config.py` to customize your Redis connection settings:

```python
REDIS_HOST = 'localhost'      # Redis server hostname or IP
REDIS_PORT = 6379            # Redis server port
REDIS_DB = 0                 # Redis database number
REDIS_PASSWORD = None        # Redis password (if required)
```

## Usage

### Writing Settings to Redis

```bash
python3 redis_settings_writer.py
```

### Reading Settings from Redis

```bash
python3 redis_settings_reader.py
```

### Expected Output - Writer Script

```
🚀 Redis Settings Writer Script
========================================
🔧 Configuration:
   Host: localhost
   Port: 6379
   Database: 0
   Password: None

✅ Successfully connected to Redis
✅ Successfully wrote settings to Redis key 'settings'
📊 Data: [3600, 3600, 3600, 3600, 3600, 3600, 3600, 0]
🔑 Key: settings
💾 Value type: <class 'list'>
📏 Array length: 8

🔄 Verifying data...
📖 Current settings in Redis:
   Key: settings
   Value: [3600, 3600, 3600, 3600, 3600, 3600, 3600, 0]

✅ Script completed successfully!
```

### Expected Output - Reader Script

```
📖 Redis Settings Reader Script
========================================
🔧 Configuration:
   Host: localhost
   Port: 6379
   Database: 0
   Password: None

✅ Successfully connected to Redis

📊 Settings Data:
==================================================
🔑 Key: settings
📏 Array length: 8
💾 Data type: <class 'list'>

   [ 0]: 3600
   [ 1]: 3600
   [ 2]: 3600
   [ 3]: 3600
   [ 4]: 3600
   [ 5]: 3600
   [ 6]: 3600
   [ 7]:    0 ← Last element

📈 Summary:
   First 7 values: [3600, 3600, 3600, 3600, 3600, 3600, 3600]
   Last value: 0
   All values are 3600: True
   Last value is 0: True
✅ Data matches expected pattern!

✅ Script completed successfully!
```

## Verification

You can verify the data was written correctly using Redis CLI:

```bash
redis-cli
> GET settings
"[3600,3600,3600,3600,3600,3600,3600,0]"
```

## Error Handling

The script includes comprehensive error handling for:
- Connection failures
- Authentication issues
- Data writing/reading errors

## Customization

To modify the default values or array size, edit the constants in `redis_config.py`:

```python
SETTINGS_DEFAULT_VALUE = 3600  # Change default value
SETTINGS_LAST_VALUE = 0        # Change last value
SETTINGS_ARRAY_SIZE = 8        # Change array size
```

## Troubleshooting

1. **Connection Error**: Make sure Redis is running and accessible
2. **Authentication Error**: Set the correct password in `redis_config.py`
3. **Permission Error**: Ensure your user has access to the Redis server

## Relay Activity History (SQLite)

In addition to the live Redis state, every relay open/close cycle is
persisted to a small SQLite database for reporting (dashboards, past
runs). Redis remains the state manager; SQLite is the durable log.

### Storage

- File: `data/history.db` (git-ignored, plus `history.db-wal` / `history.db-shm`)
- Pragmas: `journal_mode=WAL`, `synchronous=NORMAL` (Pi / SD-card friendly)
- One row per relay activity, inserted **when the relay is closed** so the
  recorded `duration_s` is the actual time the relay stayed open.

### Schema

```sql
CREATE TABLE relay_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    relay_id    INTEGER NOT NULL,   -- 0..7
    opened_at   INTEGER NOT NULL,   -- unix epoch seconds (UTC)
    duration_s  INTEGER NOT NULL,
    mode        TEXT    NOT NULL    -- 'auto' | 'semi_auto' | 'manual'
);
```

### Inspect with the CLI

```bash
sqlite3 data/history.db 'SELECT * FROM relay_activity ORDER BY id DESC LIMIT 10;'
```

### API

- `GET /history?page=1&page_size=100&relay_id=&start=&end=` — paginated
  list, newest first. `start` / `end` are unix seconds (UTC).
- `GET /history/stats?period=month&year=2026&month=4` — aggregate totals
  and per-relay breakdown. `period=year&year=2026` also supported.

Period boundaries (`start_at` / `end_at`) for `/history/stats` are
computed in the Pi's local timezone, so "April" means the whole local
calendar month.

## Network management

The backend prefers **Ethernet** as the LAN uplink, accepts a
user-configured **Wi-Fi client** profile via the HTTP API, and falls
back to a WPA2 **Wi-Fi AP** on `wlan0` when neither works. A daemon
thread inside `loop/main.py` polls NetworkManager every
`POLL_INTERVAL_S` and toggles the AP profile with hysteresis.

### Environment file

Runtime settings (AP SSID/PSK/channel, interfaces, thresholds) live in
a single root-readable env file. The easiest way to create it is the
bundled helper, which generates a random 24-char AP PSK and prints it
once:

```bash
sudo ./init-network-env.sh
```

Any value can be overridden via the environment, e.g.:

```bash
sudo AP_SSID=arrosage-field AP_CHANNEL=11 ./init-network-env.sh
```

The script refuses to overwrite an existing file; pass `FORCE=1` to
replace it (the current PSK will be lost). If you prefer to write the
file by hand:

```bash
sudo install -d -m 0755 /etc/arrosage
sudo tee /etc/arrosage/network.env > /dev/null <<'EOF'
# Wi-Fi AP fallback (WPA2-PSK). Used ONLY when no LAN is reachable.
AP_SSID=arrosage-setup
AP_PSK=change-me-strong-password
AP_CHANNEL=6
AP_IFACE=wlan0

# Wired LAN interface to check first.
LAN_IFACE=eth0

# Watchdog tuning.
POLL_INTERVAL_S=10
FAIL_THRESHOLD=3
SUCCESS_THRESHOLD=3
BOOT_GRACE_S=20
STA_CONNECT_GRACE_S=30
EOF
sudo chmod 600 /etc/arrosage/network.env
sudo chown root:root /etc/arrosage/network.env
```

The PSK must be **8..63 characters**; shorter values make
`network.ap.ensure_profile` refuse to provision the AP (so it is never
broadcast open by accident).

For development the path can be overridden without touching `/etc`:

```bash
ARROSAGE_NETWORK_ENV=$PWD/dev.network.env python loop/main.py
```

### Redis keys used

The watchdog is the sole writer of `network:mode`,
`network:lan_last_ok_at`, `network:ap_active_since` and
`network:ap_ssid`. The HTTP API writes `network:force` and
`network:wifi_changed` as one-shot intents the watchdog consumes.

### One-time host provisioning

The backend relies on NetworkManager (default on Raspberry Pi OS
Bookworm) and creates the AP profile itself on first boot, but the host
still needs a handful of one-off steps.

1. **Enable the radio.** Fresh images often leave Wi-Fi rfkill-blocked:

   ```bash
   sudo rfkill unblock wifi
   ```

2. **Set the regulatory domain** before the AP is activated for the
   first time, otherwise NetworkManager may refuse some channels or
   power levels:

   ```bash
   sudo iw reg set FR   # or your 2-letter country code
   ```

3. **Grant permission to manage NetworkManager.** The watering loop and
   the API both call `nmcli connection add/modify/delete/up/down`. The
   simplest option, matching the current `start.sh`, is to run them as
   root via systemd. If you prefer a non-root user, install a polkit
   rule like:

   ```javascript
   // /etc/polkit-1/rules.d/50-arrosage.rules
   polkit.addRule(function(action, subject) {
       if (subject.user === "arrosage" && (
           action.id === "org.freedesktop.NetworkManager.network-control" ||
           action.id === "org.freedesktop.NetworkManager.settings.modify.system"
       )) {
           return polkit.Result.YES;
       }
   });
   ```

4. **(Optional) Pre-create the AP profile.** The watchdog runs
   `ap.ensure_profile()` on startup, but you can provision it manually
   for testing:

   ```bash
   sudo nmcli connection add \
     type wifi ifname wlan0 con-name arrosage-ap \
     autoconnect no ssid "arrosage-setup" mode ap \
     802-11-wireless.band bg 802-11-wireless.channel 6 \
     802-11-wireless-security.key-mgmt wpa-psk \
     802-11-wireless-security.proto rsn \
     802-11-wireless-security.pairwise ccmp \
     802-11-wireless-security.group ccmp \
     802-11-wireless-security.psk "your-ap-password" \
     ipv4.method shared ipv6.method ignore
   ```

### Configuring a Wi-Fi client profile at runtime

Once the Pi is reachable (over Ethernet, or over the fallback AP), the
client profile is created via the HTTP API:

```bash
curl -X PUT http://<host>:8000/network/wifi \
     -H 'Content-Type: application/json' \
     -d '{"ssid": "home-network", "security": "wpa2-psk", "psk": "correct-horse-battery-staple"}'
```

Other useful calls:

```bash
curl http://<host>:8000/network/status
curl http://<host>:8000/network/wifi
curl -X DELETE http://<host>:8000/network/wifi
curl -X POST http://<host>:8000/network/force \
     -H 'Content-Type: application/json' \
     -d '{"target": "ap"}'     # or "auto"
```

### Security caveat

`api.py` currently has no authentication. The `PUT /network/wifi`
endpoint accepts the PSK in plaintext over HTTP, and
`POST /network/force` can flip the Pi into AP mode. Before exposing the
API beyond a trusted LAN, bind the management endpoints to the AP
subnet only (e.g. via nftables on `wlan0`) or add an authentication
layer.

## Running as a service

In production, the Pi runs two `systemd` units for the app plus **Caddy**
on port 80 (instead of `start.sh`, which is kept as a dev-only convenience):

- `arrosage-loop.service` — watering loop, OLED renderer, and network
  watchdog. Runs as `root` (needs GPIO, I²C, and `nmcli` to reconfigure
  NetworkManager).
- `arrosage-api.service` — FastAPI backend on **127.0.0.1:8000** (not
  exposed on the LAN). Runs as `root` because some endpoints (e.g.
  `PUT /network/wifi`) drive `nmcli` too.
- **Caddy** (`caddy.service`) — serves the built SPA from
  `arrosage-web/dist` and reverse-proxies `/api/*` to the API (prefix
  stripped). Install with
  [`deploy/install-caddy.sh`](deploy/install-caddy.sh). The frontend
  bundle uses `VITE_API_BASE_URL=/api` so the browser talks same-origin
  to Caddy (LAN, Cloudflare, or `localhost` during dev with a matching
  proxy).

Unit files live in the repo under
[`deploy/systemd/`](deploy/systemd/) and the installer at
[`deploy/install-services.sh`](deploy/install-services.sh) copies them
to `/etc/systemd/system/`, runs `daemon-reload`, and enables them.
Re-running `install-services.sh` disables and removes any legacy
`arrosage-web.service` (old `vite preview` on :5173).

### Prerequisites (once)

1. Redis and NetworkManager enabled at boot:
   ```bash
   sudo systemctl enable --now redis-server.service NetworkManager.service
   ```
2. Python venv at `/home/jnfrm/venv` with `requirements.txt` installed.
3. Network env file provisioned:
   ```bash
   sudo ./init-network-env.sh
   ```
4. Web bundle built once:
   ```bash
   cd ../arrosage-web && npm ci && npm run build
   ```
5. Regulatory country: the loop unit runs `iw reg set FR` on start.
   Edit `deploy/systemd/arrosage-loop.service` (and reinstall) if you
   deploy outside France.

### Install

```bash
sudo ./deploy/install-services.sh
```

The script refuses to run if any prerequisite is missing (venv python,
`arrosage-web/dist/`, `/etc/arrosage/network.env`, …) and prints a clear
reason. It is idempotent — re-running it overwrites the installed units
with whatever is currently in the repo.

### Check

```bash
systemctl status arrosage-loop arrosage-api caddy
journalctl -u arrosage-loop -f
journalctl -u arrosage-api  -f
journalctl -u caddy -f
```

### Update flow

Python code changed:

```bash
git pull
sudo systemctl restart arrosage-loop arrosage-api
```

Web UI changed:

```bash
git pull
cd ../arrosage-web && npm run build
sudo systemctl restart caddy
```

Unit files changed (anything under `deploy/systemd/`):

```bash
sudo ./deploy/install-services.sh
```

### Caddy and first-time reverse proxy

After building the web app, run:

```bash
sudo ./deploy/install-caddy.sh
```

Then `sudo ./deploy/install-services.sh` as usual. To refresh Caddy
config only: `sudo ./deploy/install-caddy.sh` again (overwrites
`/etc/caddy/Caddyfile` and the systemd drop-in).

### Caddy HTTP Basic Auth

The Caddyfile protects **all** of `:80` (static UI and `/api`) with a
single user **`arrosage`**. The password is **never** stored in git;
only a **bcrypt hash** lives on the Pi in
`/etc/arrosage/caddy-basic-auth.env`.

1. On the Pi, generate a hash (interactive is best so the password is
   not left in shell history):

   ```bash
   caddy hash-password
   ```

2. Create `/etc/arrosage/caddy-basic-auth.env` with one line (use the
   full string `caddy` printed). Bcrypt values start with `$2a$` / `$2y$`;
   **systemd** reads this file without shell expansion, so those `$`
   characters are fine. (Do not `source` the file in bash with `set -u`.)

   ```bash
   ARROSAGE_BASIC_AUTH_HASH=$2a$14$...
   ```

3. Caddy runs as `jnfrm`; the file must be readable by that user, e.g.:

   ```bash
   sudo chown root:jnfrm /etc/arrosage/caddy-basic-auth.env
   sudo chmod 640 /etc/arrosage/caddy-basic-auth.env
   ```

4. Deploy / reload:

   ```bash
   sudo ./deploy/install-caddy.sh
   ```

See [`deploy/caddy/caddy-basic-auth.env.example`](deploy/caddy/caddy-basic-auth.env.example)
for a commented template. `install-caddy.sh` refuses to run if the env
file is missing, the hash is not a plausible bcrypt string, or `jnfrm`
cannot read the file.

After changing the password, regenerate the hash, update the env file,
and run `sudo systemctl restart caddy`.

