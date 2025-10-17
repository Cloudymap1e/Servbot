"""Application-wide constants and configuration values.

Centralizes magic numbers and hardcoded values for better maintainability.
"""

# IMAP Configuration
DEFAULT_IMAP_PORT = 993
DEFAULT_IMAP_SSL = True
DEFAULT_IMAP_FOLDER = "INBOX"
DEFAULT_IMAP_TIMEOUT = 30

# Graph API Configuration
GRAPH_API_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_API_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_API_MAX_MESSAGES = 50

# Flashmail API Configuration
FLASHMAIL_BASE_URL = "https://zizhu.shanyouxiang.com"
FLASHMAIL_MIN_QUANTITY = 1
FLASHMAIL_MAX_QUANTITY = 2000
FLASHMAIL_DEFAULT_TIMEOUT = 60

# Message Fetching Defaults
DEFAULT_MESSAGE_LIMIT = 200
DEFAULT_MESSAGE_PREVIEW_LENGTH = 280

# Verification Polling
DEFAULT_POLL_TIMEOUT_SECONDS = 60
DEFAULT_POLL_INTERVAL_SECONDS = 5
MIN_POLL_INTERVAL_SECONDS = 1

# HTTP Configuration
DEFAULT_HTTP_TIMEOUT = 20
DEFAULT_USER_AGENT = "Servbot/1.0"

# Database
DEFAULT_VERIFICATION_HOURS = 24

