# Redis Configuration
# Modify these values according to your Redis setup

# Redis connection settings
REDIS_HOST = 'localhost'      # Redis server hostname or IP address
REDIS_PORT = 6379            # Redis server port
REDIS_DB = 0                 # Redis database number
REDIS_PASSWORD = None        # Redis password (set to string if authentication is required)

# Settings configuration
SETTINGS_DEFAULT_VALUE = 3600  # Default value for first 7 elements
SETTINGS_LAST_VALUE = 0        # Value for the last element
SETTINGS_ARRAY_SIZE = 8        # Total size of the settings array
