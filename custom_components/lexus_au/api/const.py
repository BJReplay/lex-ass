"""Protocol constants captured from the Lexus Australia mobile app."""

AUTH_BASE_URL = "https://login.lexusdriverslogin.com.au"
OPENIDM_BASE_URL = "https://openidm.lexusdriverslogin.com.au"
API_BASE_URL = "https://tmca-oneapi.telematicsct.com.au"
ONECDN_BASE_URL = "https://onecdn.telematicsct.com.au"

AUTHENTICATE_PATH = (
    "/json/realms/tmca/authenticate?authIndexType=service&authIndexValue=oneapp"
)
AUTHORIZE_PATH = "/oauth2/realms/root/realms/tmca/authorize"
ACCESS_TOKEN_PATH = "/oauth2/realms/root/realms/tmca/access_token"
PASSWORD_CHECK_PATH = "/openidm/endpoint/passwordService?_action=checkPassword"

DEVICE_STATUS_PATH = "/v1/notification/device/status"
REMOTE_STATUS_PATH = "/v1/global/remote/status"
REMOTE_ENGINE_STATUS_PATH = "/v1/global/remote/engine-status"
REMOTE_REFRESH_PATH = "/v1/global/remote/refresh-status"
REMOTE_COMMAND_PATH = "/v1/global/remote/command"
VEHICLE_GUID_PATH = "/v2/vehicle/guid"
VEHICLE_LOCATION_PATH = "/v1/location"
TELEMETRY_V2_PATH = "/v2/telemetry"
TELEMETRY_V3_PATH = "/v3/telemetry"
ELECTRIC_STATUS_PATH = "/oneapi/v3/electric/status"
CLIMATE_SETTINGS_PATH = "/v1/remote/route/climate-settings"

CLIENT_ID = "oneapp"
REDIRECT_URI = "com.toyota.oneapp:/oauth2Callback"
TOKEN_BASIC_AUTH = "Basic b25lYXBwOm9uZWFwcA=="

# Captured from Lexus AppStore 12.1.1.35. These may need refreshing after app updates.
APP_VERSION = "12.1"
APP_VERSION_FULL = "12.1.1.35"
USER_AGENT = "LexusAppStore/12.1.1.35 CFNetwork/3826.600.41 Darwin/24.6.0"
OS_NAME = "iPadOS"
OS_VERSION = "18.6"
LOCALE = "en-AU"
DEVICE_TIMEZONE = "AEST"
DEVICE_TYPE = "iOS"
DEVICE_MODEL = "iPad"
APP_LABEL = "com.au.lexus.oneapp"
BRAND = "L"
CHANNEL = "ONEAPP"
ONECDN_APP_VERSION = "13.6.0"
ONECDN_USER_AGENT = "okhttp/5.3.2"
ONECDN_OS_NAME = "Android"
ONECDN_OS_VERSION = "15"

COMMAND_DOOR_LOCK = "door-lock"
COMMAND_DOOR_UNLOCK = "door-unlock"
COMMAND_ENGINE_START = "engine-start"
COMMAND_ENGINE_STOP = "engine-stop"
COMMAND_HAZARD_ON = "hazard-on"
COMMAND_HAZARD_OFF = "hazard-off"
COMMAND_TRUNK_LOCK = "trunk-lock"
COMMAND_TRUNK_UNLOCK = "trunk-unlock"
COMMAND_HEADLIGHT_ON = "headlight-on"
COMMAND_HEADLIGHT_OFF = "headlight-off"
COMMAND_SOUND_HORN = "sound-horn"
COMMAND_BUZZER_WARNING = "buzzer-warning"

# AU has already proven to use modern command strings with old-style numeric direction values.
COMMAND_VALUE_ON = 1
COMMAND_VALUE_OFF = 2
