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

# Flashmail Graph API Credentials (standard for all Flashmail accounts)
FLASHMAIL_REFRESH_TOKEN = "M.C555_BAY.0.U.-CuM67nex5EBQ!GY0IMwAOsN0wHFlWi9YWNwFTS2mzmABTJw4i8BtfmVWXjVq2kH9i65E4qOMvr72P9GwhSVTa7nvrEJZqQzsCfHtANNdncOtu*MueuG6MGVTUGlRxV21ojrNHLRyLBXlnycQ!sBnjZTq1Ws4SFNennegb6ANEp3Fk9RfIGyx2O4brysLRTRG9rgzIzifUND2aJrb5xyWSOolE1wqr7nYICzgbXh4pdeiSdmA0KmFO2ogiPg4Dnh15lzDUXP597GsiBUj7Kc*3IpHXC!4aA9Ft8a2uyEAdzC2iIY39PXydNqfiEDtOeb4KvThzKx3GilBqRURL2UboxZ0POmcvKywSpm*eU!5Z9AnQD2vJQmpmAc9WlV538ZkWv8lR9R9ubkhf1T4G324wlA$"
FLASHMAIL_CLIENT_ID = "8b4ba9dd-3ea5-4e5f-86f1-ddba2230dcf2"

