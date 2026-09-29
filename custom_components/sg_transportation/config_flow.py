from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientResponseError
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigSubentryFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import (
    CONF_ACCOUNT_KEY,
    DOMAIN,
    SUBENTRY_TYPE_BUS_SERVICE,
    SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS,
    TRAIN_ALERTS_API_URL,
)
from .subentry_flow import BusServiceSubEntryFlowHandler, TrainServiceAlertsSubEntryFlowHandler


ACCOUNT_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class SGTransportationConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        config_entry: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            SUBENTRY_TYPE_BUS_SERVICE: BusServiceSubEntryFlowHandler,
            SUBENTRY_TYPE_TRAIN_SERVICE_ALERTS: TrainServiceAlertsSubEntryFlowHandler,
        }

    async def _async_validate_account_key(self, account_key: str) -> str | None:
        session = async_get_clientsession(self.hass)
        headers = {
            "AccountKey": account_key,
            "accept": "application/json",
        }

        try:
            async with session.get(
                TRAIN_ALERTS_API_URL,
                headers=headers,
                timeout=10,
            ) as response:
                response.raise_for_status()
                await response.json()
        except ClientResponseError as err:
            if err.status in (401, 403):
                return "invalid_auth"
            return "cannot_connect"
        except (ClientError, TimeoutError):
            return "cannot_connect"
        except (TypeError, ValueError):
            return "unknown"

        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}

        if user_input is not None:
            account_key = str(user_input[CONF_ACCOUNT_KEY]).strip()
            error = await self._async_validate_account_key(account_key)

            if error is None:
                return self.async_create_entry(
                    title="SG Transportation",
                    data={CONF_ACCOUNT_KEY: account_key},
                )

            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=ACCOUNT_KEY_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        errors: dict[str, str] = {}

        if user_input is not None:
            account_key = str(user_input[CONF_ACCOUNT_KEY]).strip()
            error = await self._async_validate_account_key(account_key)

            if error is None:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_ACCOUNT_KEY: account_key},
                )

            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=ACCOUNT_KEY_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        errors: dict[str, str] = {}

        if user_input is not None:
            account_key = str(user_input[CONF_ACCOUNT_KEY]).strip()
            error = await self._async_validate_account_key(account_key)

            if error is None:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates={CONF_ACCOUNT_KEY: account_key},
                )

            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=ACCOUNT_KEY_SCHEMA,
            errors=errors,
        )
