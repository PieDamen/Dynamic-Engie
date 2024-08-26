import logging
import requests
from datetime import date, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, UNIT_PERCENTAGE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=1)  # Update every hour

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Engie sensor based on the configuration entry."""
    coordinator = EngieDataCoordinator(hass)
    await coordinator.async_refresh()
    async_add_entities([EngieSensor(coordinator)], update_before_add=True)

class EngieDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Engie data."""

    def __init__(self, hass):
        """Initialize global data updater."""
        self.hass = hass
        self.url = 'https://api.engie.be/engie/ms/pricing/v1/public/prices/epex'
        super().__init__(hass, _LOGGER, name="Engie Data", update_interval=SCAN_INTERVAL)

    async def _async_update_data(self):
        """Fetch data from the API."""
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            data = response.json()

            today = date.today()
            tomorrow = today + timedelta(days=1)
            formatted_today = today.strftime('%Y-%m-%d')
            formatted_tomorrow = tomorrow.strftime('%Y-%m-%d')

            today_data = [entry['value'] for entry in data['timeSeries'] if entry['period'].startswith(formatted_today)]
            tomorrow_data = [entry['value'] for entry in data['timeSeries'] if entry['period'].startswith(formatted_tomorrow)]

            # Calculations for the sensor attributes
            attributes = {
                "state_class": "total",
                "average": sum(today_data) / len(today_data) if today_data else 0,
                "off_peak_1": min(today_data) if today_data else 0,
                "off_peak_2": max(today_data) if today_data else 0,
                "peak": max(today_data) if today_data else 0,
                "min": min(today_data) if today_data else 0,
                "max": max(today_data) if today_data else 0,
                "mean": sum(today_data) / len(today_data) if today_data else 0,
                "unit": "kWh",
                "currency": "EUR",
                "country": "Belgium",
                "region": "BE",
                "low_price": False,  # You might need additional logic to determine this
                "price_percent_to_average": (sum(today_data) / len(today_data) if today_data else 0) / (sum(today_data) / len(today_data) if today_data else 1),
                "today": today_data,
                "tomorrow": tomorrow_data,
                "tomorrow_valid": bool(tomorrow_data),
                "raw_today": [ {"start": entry["period"], "end": entry["end"], "value": entry["value"]} for entry in data["timeSeries"] if entry['period'].startswith(formatted_today)],
                "raw_tomorrow": [ {"start": entry["period"], "end": entry["end"], "value": entry["value"]} for entry in data["timeSeries"] if entry['period'].startswith(formatted_tomorrow)],
                "current_price": max(today_data) if today_data else 0,
                "additional_costs_current_hour": 0,
                "price_in_cents": True,
                "unit_of_measurement": "c/kWh",
                "device_class": "monetary",
                "icon": "mdi:flash",
                "friendly_name": "Engie Price Sensor"
            }

            return attributes

        except Exception as e:
            raise UpdateFailed(f"Error fetching data from Engie: {e}")

class EngieSensor(SensorEntity):
    """Representation of an Engie sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Engie Price Sensor"
        self._attr_unique_id = "engie_price_sensor"
        self._attr_device_class = "monetary"
        self._attr_unit_of_measurement = "kWh"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("current_price")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self.coordinator.data
