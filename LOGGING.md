# API Logging Documentation

## Overview

The Arrosage API now has comprehensive logging for all operations, errors, and requests.

## Log Format

```
YYYY-MM-DD HH:MM:SS - arrosage_api - LEVEL - MESSAGE
```

Example:
```
2025-10-19 13:35:56 - arrosage_api - INFO - ➡️  GET /mode - Client: 192.168.1.46
```

## Log Levels

- **INFO**: Normal operations (requests, successful operations)
- **WARNING**: Validation errors, missing data
- **ERROR**: Exceptions, system errors, failures
- **DEBUG**: Detailed information (enable by changing `level=logging.DEBUG`)

## What Gets Logged

### 1. Startup
```
2025-10-19 13:35:56 - arrosage_api - INFO - 📦 Importing commands...
2025-10-19 13:35:56 - arrosage_api - INFO - ✅ semi_auto imported
2025-10-19 13:35:56 - arrosage_api - INFO - 🚀 Starting Arrosage API...
```

### 2. Every HTTP Request
```
2025-10-19 14:23:45 - arrosage_api - INFO - ➡️  GET /mode - Client: 192.168.1.46
2025-10-19 14:23:45 - arrosage_api - INFO - ⬅️  GET /mode - Status: 200 - Duration: 0.023s
```

### 3. Successful Operations
```
2025-10-19 14:25:10 - arrosage_api - INFO - Settings endpoint called
2025-10-19 14:25:10 - arrosage_api - INFO - Returning settings successfully
```

### 4. Validation Errors
```
2025-10-19 14:30:22 - arrosage_api - WARNING - Invalid start_at format: 25:99
2025-10-19 14:30:22 - arrosage_api - WARNING - Invalid sequence length: 5
```

### 5. System Errors
```
2025-10-19 14:35:00 - arrosage_api - ERROR - ❌ GET /settings - Error: Connection refused - Duration: 0.105s
2025-10-19 14:35:00 - arrosage_api - ERROR - Traceback:
Traceback (most recent call last):
  File "/home/jnfrm/projects/arrosage/arrosage-python/api.py", line 78, in log_requests
    response = await call_next(request)
  ...
```

### 6. CORS Errors
CORS errors will show up in the logs as blocked requests before reaching your endpoints. You'll see:
```
2025-10-19 14:40:00 - arrosage_api - INFO - ➡️  OPTIONS /mode - Client: 192.168.1.46
2025-10-19 14:40:00 - arrosage_api - INFO - ⬅️  OPTIONS /mode - Status: 200 - Duration: 0.001s
```

## Enabling Debug Logging

To see more detailed logs (like Redis operations), change line 24 in `api.py`:

```python
# From:
level=logging.INFO,

# To:
level=logging.DEBUG,
```

Then you'll see additional debug messages:
```
2025-10-19 15:00:00 - arrosage_api - DEBUG - Getting settings from Redis...
2025-10-19 15:00:00 - arrosage_api - DEBUG - Settings retrieved: {'start_at': '20:00', ...}
```

## Log Output Location

By default, logs are printed to **stdout** (console). To save logs to a file, you can:

### Option 1: Redirect when running
```bash
python3 api.py 2>&1 | tee api.log
```

### Option 2: Configure file handler in code
Add this to the logging configuration in `api.py`:

```python
# Add file handler
file_handler = logging.FileHandler('arrosage_api.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(file_handler)
```

## Troubleshooting CORS Errors

If you see CORS errors in the browser console but nothing in the API logs, it means:
1. The request never reached the Python server (network issue)
2. The preflight OPTIONS request was blocked before logging

With the current setup, you should see:
- **OPTIONS** requests (CORS preflight checks)
- **GET/POST** requests (actual API calls)
- Full error tracebacks if something goes wrong
- Request duration to identify slow endpoints

