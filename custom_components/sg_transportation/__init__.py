from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import CONF_ACCOUNT_KEY
from .coordinator import SGBusArrivalsCoordinator, SGTrainServiceAlertsCoordinator


@dataclass
class SGTransportationData:
    bus_arrivals_coordinator: SGBusArrivalsCoordinator
    train_service_alerts_coordinator: SGTrainServiceAlertsCoordinator


PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    account_key = str(entry.data.get(CONF_ACCOUNT_KEY, "")).strip()
    if not account_key:
        raise ConfigEntryAuthFailed(
            "LTA DataMall AccountKey is required. Reauthenticate SG Transportation."
        )

    bus_coordinator = SGBusArrivalsCoordinator(
        hass=hass,
        config_entry=entry,
    )

    train_coordinator = SGTrainServiceAlertsCoordinator(
        hass=hass,
        config_entry=entry,
    )

    entry.runtime_data = SGTransportationData(
        bus_arrivals_coordinator=bus_coordinator,
        train_service_alerts_coordinator=train_coordinator,
    )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await bus_coordinator.async_config_entry_first_refresh()
    await train_coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
