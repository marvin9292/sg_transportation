from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BUS_LOAD_MAP,
    BUS_TYPE_MAP,
    DOMAIN,
    SUBENTRY_CONF_BUS_STOP_CODE,
    SUBENTRY_CONF_DESCRIPTION,
    SUBENTRY_CONF_SERVICE_NO,
    SUBENTRY_TYPE_BUS_SERVICE,
    SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS,
    TRAIN_LINE_CODES,
)
from .coordinator import SGBusArrivalsCoordinator, SGTrainServiceAlertsCoordinator


def _display_time(duration_ms: int | None) -> str:
    if duration_ms is None:
        return "No Data"
    mins = duration_ms // 60000
    if mins <= 0:
        return "Arriving"
    return f"{mins} mins"


class BusArrivalSensor(CoordinatorEntity[SGBusArrivalsCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:bus-clock"

    def __init__(
        self,
        coordinator: SGBusArrivalsCoordinator,
        subentry: ConfigSubentry,
        arrival_index: int,
    ) -> None:
        super().__init__(coordinator)

        self._subentry = subentry
        self._arrival_index = arrival_index

        self._bus_stop_code = subentry.data[SUBENTRY_CONF_BUS_STOP_CODE]
        self._description = subentry.data[SUBENTRY_CONF_DESCRIPTION]
        self._service_no = subentry.data[SUBENTRY_CONF_SERVICE_NO]

        self._trip_key = {1: "next", 2: "next2", 3: "next3"}[arrival_index]

        self._attr_unique_id = (
            f"{self._bus_stop_code}_{self._service_no}_arrival_time_{arrival_index}"
        )
        self._attr_name = f"Arrival Time {arrival_index}"

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=f"Bus {self._service_no} {self._description}",
        )

    def _service(self) -> dict | None:
        stop_data = self.coordinator.data.get(self._bus_stop_code, {})
        return stop_data.get(self._service_no)

    def _trip(self) -> dict | None:
        service = self._service()
        if not service:
            return None
        return service.get(self._trip_key)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        attrs: dict[str, Any] = {
            "stop_id": self._bus_stop_code,
            "stop_name": self._description,
            "bus_number": self._service_no,
            "arrival_index": self._arrival_index,
        }

        service = self._service()
        if not service:
            attrs["general_arrival_time"] = "No Bus Found"
            attrs["type"] = None
            attrs["load"] = None
            return attrs

        next1 = service.get("next")
        next2 = service.get("next2")
        next3 = service.get("next3")

        attrs["operator"] = service.get("operator")
        attrs["general_arrival_time"] = "/".join(
            [
                _display_time(next1.get("duration_ms")) if next1 else "No Data",
                _display_time(next2.get("duration_ms")) if next2 else "No Data",
                _display_time(next3.get("duration_ms")) if next3 else "No Data",
            ]
        )

        trip = self._trip()
        attrs["type"] = BUS_TYPE_MAP.get(trip.get("type"), trip.get("type")) if trip else None
        attrs["load"] = BUS_LOAD_MAP.get(trip.get("load"), trip.get("load")) if trip else None
        return attrs

    @property
    def native_value(self) -> str:
        trip = self._trip()
        if not trip:
            return "No Data"
        return _display_time(trip.get("duration_ms"))


class TrainServiceAlertSensor(
    CoordinatorEntity[SGTrainServiceAlertsCoordinator], SensorEntity
):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SGTrainServiceAlertsCoordinator,
        subentry: ConfigSubentry,
        line_code: str,
    ) -> None:
        super().__init__(coordinator)
        self._subentry = subentry
        self._line_code = line_code

        line_data = coordinator.data.get(line_code, {})
        line_name = line_data.get("line_name", line_code)

        self._attr_unique_id = f"{subentry.subentry_id}_{line_code.lower()}"
        self._attr_name = line_name

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{subentry.subentry_id}_train_alerts")},
            name="Train Service Alerts",
        )

    @property
    def native_value(self) -> str:
        line_data = self.coordinator.data.get(self._line_code, {})
        return line_data.get("status", "Normal")

    @property
    def icon(self) -> str:
        state = self.native_value
        if state == "Disrupted":
            return "mdi:alert"
        if state == "Advisory":
            return "mdi:information-outline"
        return "mdi:subway-variant"

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        line_data = self.coordinator.data.get(self._line_code, {})

        return {
            "line_code": line_data.get("line_code", self._line_code),
            "line_name": line_data.get("line_name", self._line_code),
            "message_count": line_data.get("message_count", 0),
            "primary_message": line_data.get("primary_message", "No active message"),
            "messages": line_data.get("messages", []),
            "segments": line_data.get("segments", []),
        }


async def async_setup_entry(
    hass,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    bus_coordinator = config_entry.runtime_data.bus_arrivals_coordinator
    train_coordinator = config_entry.runtime_data.train_service_alerts_coordinator

    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_TYPE_BUS_SERVICE:
            entities = [
                BusArrivalSensor(bus_coordinator, subentry, 1),
                BusArrivalSensor(bus_coordinator, subentry, 2),
                BusArrivalSensor(bus_coordinator, subentry, 3),
            ]

            async_add_entities(
                entities,
                update_before_add=True,
                config_subentry_id=subentry.subentry_id,
            )

        elif subentry.subentry_type == SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS:
            entities = [
                TrainServiceAlertSensor(train_coordinator, subentry, line_code)
                for line_code in TRAIN_LINE_CODES
            ]

            async_add_entities(
                entities,
                update_before_add=True,
                config_subentry_id=subentry.subentry_id,
            )
