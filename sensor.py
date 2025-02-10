import logging
import requests
import voluptuous as vol
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_SCAN_INTERVAL, STATE_UNKNOWN
from homeassistant.helpers import config_validation as cv
from homeassistant.util.json import load_json
from homeassistant.helpers.json import save_json
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DOMAIN = "dhl_tracking"
REGISTRATIONS_FILE = "dhl_tracking.conf"
SERVICE_REGISTER = "register"
SERVICE_UNREGISTER = "unregister"
ATTR_API_KEY = "api_key"
ATTR_PACKAGE_ID = "package_id"
ICON = "mdi:package-variant-closed"
SCAN_INTERVAL = timedelta(minutes=30)
DHL_API_URL = "https://api-eu.dhl.com/track/shipments?trackingNumber={}"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(ATTR_API_KEY): cv.string})
SUBSCRIPTION_SCHEMA = vol.Schema({vol.Required(ATTR_PACKAGE_ID): cv.string})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the DHL tracking sensor."""
    api_key = config[ATTR_API_KEY]
    json_path = hass.config.path(REGISTRATIONS_FILE)
    registrations = _load_config(json_path)

    async def async_service_register(service):
        """Handle package registration."""
        package_id = service.data[ATTR_PACKAGE_ID].upper()
        if package_id in registrations:
            _LOGGER.warning("Package already tracked: %s", package_id)
            return
        registrations.append(package_id)
        await hass.async_add_executor_job(save_json, json_path, registrations)
        async_add_entities([DHLSensor(package_id, api_key)], True)

    hass.services.async_register(DOMAIN, SERVICE_REGISTER, async_service_register, schema=SUBSCRIPTION_SCHEMA)

    async def async_service_unregister(service):
        """Handle package unregistration."""
        package_id = service.data[ATTR_PACKAGE_ID]
        if package_id in registrations:
            registrations.remove(package_id)
            await hass.async_add_executor_job(save_json, json_path, registrations)
            # Match the sensor entity ID and remove it
            entity_id = f"sensor.dhl_{package_id.lower()}"
            _LOGGER.info("Unregistering package and removing sensor: %s", entity_id)
            hass.states.async_remove(entity_id)

    hass.services.async_register(DOMAIN, SERVICE_UNREGISTER, async_service_unregister, schema=SUBSCRIPTION_SCHEMA)

    # Create and add sensors for all registered packages
    sensors = [DHLSensor(package_id, api_key) for package_id in registrations]
    async_add_entities(sensors, True)

def _load_config(filename):
    """Load configuration from file."""
    try:
        return load_json(filename, [])
    except:
        return []

class DHLSensor(RestoreEntity):
    """DHL Tracking Sensor."""
    def __init__(self, package_id, api_key):
        """Initialize the sensor."""
        self._package_id = package_id
        self._api_key = api_key
        self._state = STATE_UNKNOWN
        self._attributes = {}
        self._entity_id = f"sensor.dhl_{package_id.lower()}"  # Explicitly define entity ID

    @property
    def name(self):
        return f"DHL Package {self._package_id}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def icon(self):
        return ICON

    @property
    def entity_id(self):
        return self._entity_id  # Use the defined entity_id

    def update(self):
        """Update sensor state."""
        _LOGGER.debug("Updating DHL tracking for package %s", self._package_id)
        try:
            response = requests.get(DHL_API_URL.format(self._package_id),
                                    headers={'DHL-API-Key': self._api_key},
                                    timeout=10)
            response.raise_for_status()
            data = response.json()
            if "shipments" in data and data["shipments"]:
                shipment = data["shipments"][0]
                self._state = shipment.get("status", {}).get("statusCode", STATE_UNKNOWN)
                self._attributes = shipment
            else:
                _LOGGER.warning("No shipment data found for package %s", self._package_id)
        except requests.exceptions.RequestException as err:
            _LOGGER.error("DHL API request error: %s", err)
