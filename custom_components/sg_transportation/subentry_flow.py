from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigSubentryFlow

from .const import (
    SUBENTRY_CONF_BUS_STOP_CODE,
    SUBENTRY_CONF_DESCRIPTION,
    SUBENTRY_CONF_SERVICE_NO,
    SUBENTRY_TYPE_BUS_SERVICE,
    SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS,
)


class TrainServiceAlertsSubEntryFlowHandler(ConfigSubentryFlow):
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        config_entry = self._get_entry()

        for existing_subentry in config_entry.subentries.values():
            if existing_subentry.subentry_type == SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS:
                return self.async_abort(reason="already_configured")

        return self.async_create_entry(
            title="Train Service Alerts",
            data={},
            unique_id=SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS,
        )


class BusServiceSubEntryFlowHandler(ConfigSubentryFlow):
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            bus_stop_code = str(user_input[SUBENTRY_CONF_BUS_STOP_CODE]).strip()
            description = str(user_input[SUBENTRY_CONF_DESCRIPTION]).strip()
            service_no = str(user_input[SUBENTRY_CONF_SERVICE_NO]).strip().upper()

            config_entry = self._get_entry()

            for existing_subentry in config_entry.subentries.values():
                if (
                    existing_subentry.subentry_type == SUBENTRY_TYPE_BUS_SERVICE
                    and existing_subentry.data[SUBENTRY_CONF_BUS_STOP_CODE] == bus_stop_code
                    and existing_subentry.data[SUBENTRY_CONF_SERVICE_NO] == service_no
                ):
                    return self.async_abort(reason="already_configured")

            return self.async_create_entry(
                title=f"{service_no} @{description}",
                data={
                    SUBENTRY_CONF_BUS_STOP_CODE: bus_stop_code,
                    SUBENTRY_CONF_DESCRIPTION: description,
                    SUBENTRY_CONF_SERVICE_NO: service_no,
                },
                unique_id=f"{bus_stop_code}_{service_no}",
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(SUBENTRY_CONF_BUS_STOP_CODE): str,
                    vol.Required(SUBENTRY_CONF_DESCRIPTION): str,
                    vol.Required(SUBENTRY_CONF_SERVICE_NO): str,
                }
            ),
        )
