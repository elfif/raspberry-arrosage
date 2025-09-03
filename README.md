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
