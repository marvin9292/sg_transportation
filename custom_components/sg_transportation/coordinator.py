from __future__ import annotations

import collections
from asyncio import gather, timeout
from datetime import UTC, datetime, timedelta
import logging
import re

from aiohttp import ClientError, ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ACCOUNT_KEY,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
    SUBENTRY_CONF_BUS_STOP_CODE,
    SUBENTRY_TYPE_BUS_SERVICE,
    TRAIN_ALERTS_API_URL,
    TRAIN_LINE_CODES,
    TRAIN_LINE_NAME_MAP,
)


_LOGGER = logging.getLogger(__name__)


class SGBusArrivalsCoordinator(DataUpdateCoordinator[dict[str, dict[str, dict]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
            always_update=True,
        )
        self._session = async_get_clientsession(hass)
        self._account_key = str(config_entry.data[CONF_ACCOUNT_KEY])

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "AccountKey": self._account_key,
            "accept": "application/json",
        }

    def _compute_duration_ms(self, estimated_arrival: str) -> int | None:
        if not estimated_arrival:
            return None

        try:
            arrival_datetime = datetime.fromisoformat(estimated_arrival)
        except ValueError:
            return None

        now_utc = datetime.now(UTC)
        duration_ms = int((arrival_datetime - now_utc).total_seconds() * 1000)
        return max(duration_ms, 0)

    def _normalize_trip(self, trip: dict) -> dict:
        estimated_arrival = str(trip.get("EstimatedArrival", "")).strip()
        return {
            "duration_ms": self._compute_duration_ms(estimated_arrival),
            "type": trip.get("Type") or None,
            "load": trip.get("Load") or None,
        }

    async def _fetch_stop(self, bus_stop_code: str) -> list[dict]:
        url = f"{TRAIN_ALERTS_API_URL.rsplit('/', 1)[0]}/v3/BusArrival?BusStopCode={bus_stop_code}"

        async with self._session.get(
            url,
            headers=self._headers,
            timeout=10,
        ) as response:
            response.raise_for_status()
            payload = await response.json()

        services = []
        for service in payload.get("Services", []) or []:
            services.append(
                {
                    "no": str(service.get("ServiceNo", "")).upper(),
                    "operator": service.get("Operator"),
                    "next": self._normalize_trip(service.get("NextBus", {})),
                    "next2": self._normalize_trip(service.get("NextBus2", {})),
                    "next3": self._normalize_trip(service.get("NextBus3", {})),
                }
            )

        return services

    async def _async_update_data(self) -> dict[str, dict[str, dict]]:
        assert self.config_entry is not None

        bus_stop_codes: set[str] = set()
        for subentry in self.config_entry.subentries.values():
            if subentry.subentry_type == SUBENTRY_TYPE_BUS_SERVICE:
                bus_stop_codes.add(subentry.data[SUBENTRY_CONF_BUS_STOP_CODE])

        all_bus_arrivals: dict[str, dict[str, dict]] = collections.defaultdict(dict)

        try:
            async with timeout(10):
                responses = await gather(
                    *[
                        self._fetch_stop(bus_stop_code)
                        for bus_stop_code in bus_stop_codes
                    ]
                )

            for bus_stop_code, services in zip(
                bus_stop_codes,
                responses,
                strict=False,
            ):
                for service in services:
                    service_no = str(service.get("no", "")).upper()
                    all_bus_arrivals[bus_stop_code][service_no] = service

            return all_bus_arrivals

        except ClientResponseError as err:
            if err.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    "Invalid LTA DataMall AccountKey"
                ) from err
            raise UpdateFailed(
                f"Error fetching bus arrivals: {err}"
            ) from err

        except (ClientError, TimeoutError) as err:
            raise UpdateFailed(
                f"Error fetching bus arrivals: {err}"
            ) from err

        except (AttributeError, TypeError, ValueError) as err:
            raise UpdateFailed(
                f"Invalid bus arrivals response: {err}"
            ) from err


class SGTrainServiceAlertsCoordinator(
    DataUpdateCoordinator[dict[str, dict]]
):
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_train_alerts",
            config_entry=config_entry,
            update_interval=timedelta(seconds=60),
            always_update=True,
        )
        self._session = async_get_clientsession(hass)
        self._account_key = str(config_entry.data[CONF_ACCOUNT_KEY])

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "AccountKey": self._account_key,
            "accept": "application/json",
        }

    def _message_matches_line(
        self,
        content: str,
        line_code: str,
    ) -> bool:
        content_upper = content.upper()
        full_name_upper = TRAIN_LINE_NAME_MAP[line_code].upper()
        code_pattern = rf"(^|[^A-Z]){re.escape(line_code)}([^A-Z]|$)"

        return bool(
            re.search(code_pattern, content_upper)
            or full_name_upper in content_upper
        )

    async def _async_update_data(self) -> dict[str, dict]:
        try:
            async with timeout(15):
                async with self._session.get(
                    TRAIN_ALERTS_API_URL,
                    headers=self._headers,
                    timeout=15,
                ) as response:
                    response.raise_for_status()
                    payload = await response.json()

            value = payload.get("value", {})
            affected_segments = value.get("AffectedSegments", []) or []
            all_messages = value.get("Message", []) or []

            affected_by_line: dict[str, list[dict]] = {
                code: []
                for code in TRAIN_LINE_CODES
            }

            for segment in affected_segments:
                line_code = str(
                    segment.get("Line", "")
                ).upper().strip()

                if line_code in affected_by_line:
                    affected_by_line[line_code].append(segment)

            alerts: dict[str, dict] = {}

            for line_code in TRAIN_LINE_CODES:
                segments = affected_by_line[line_code]
                messages = []

                for message in all_messages:
                    content = str(
                        message.get("Content", "")
                    ).strip()

                    if content and self._message_matches_line(
                        content,
                        line_code,
                    ):
                        messages.append(content)

                if segments:
                    status = "Disrupted"
                elif messages:
                    status = "Advisory"
                else:
                    status = "Normal"

                alerts[line_code] = {
                    "line_code": line_code,
                    "line_name": TRAIN_LINE_NAME_MAP[line_code],
                    "status": status,
                    "segments": segments,
                    "message_count": len(messages),
                    "messages": messages,
                    "primary_message": (
                        messages[0]
                        if messages
                        else "No active message"
                    ),
                }

            return alerts

        except ClientResponseError as err:
            if err.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    "Invalid LTA DataMall AccountKey"
                ) from err
            raise UpdateFailed(
                f"Error fetching train service alerts: {err}"
            ) from err

        except (ClientError, TimeoutError) as err:
            raise UpdateFailed(
                f"Error fetching train service alerts: {err}"
            ) from err

        except (AttributeError, TypeError, ValueError) as err:
            raise UpdateFailed(
                f"Invalid train service alerts response: {err}"
            ) from err
