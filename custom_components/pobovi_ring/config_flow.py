"""Config and options flow for the POBOVi Ring integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ADDRESS,
    CONF_BIRTHDATE,
    CONF_COLLECT_SECONDS,
    CONF_CYCLE_DURATION,
    CONF_CYCLE_ENABLED,
    CONF_CYCLE_LENGTH,
    CONF_CYCLE_START,
    CONF_ENABLE_REALTIME,
    CONF_FIND_SECONDS,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_NAME,
    CONF_POLL_INTERVAL,
    CONF_PROFILE_ENABLED,
    CONF_SPARKY_API_KEY,
    CONF_SPARKY_ENABLED,
    CONF_SPARKY_SOURCE,
    CONF_SPARKY_URL,
    CONF_STRIDE,
    CONF_WEIGHT,
    DEFAULT_COLLECT_SECONDS,
    DEFAULT_ENABLE_REALTIME,
    DEFAULT_FIND_SECONDS,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SPARKY_ENABLED,
    DEFAULT_SPARKY_SOURCE,
    DEFAULT_SPARKY_URL,
    DOMAIN,
    MAX_COLLECT_SECONDS,
    MAX_FIND_SECONDS,
    MAX_POLL_INTERVAL,
    MIN_COLLECT_SECONDS,
    MIN_FIND_SECONDS,
    MIN_POLL_INTERVAL,
)

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def _normalize_mac(value: str) -> str:
    return value.strip().replace("-", ":").upper()


def _default_name(address: str) -> str:
    """Return a unique default name so several rings do not collide."""
    return f"POBOVi Ring {address.replace(':', '')[-4:].upper()}"


class PoboviRingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the POBOVi Ring config flow."""

    VERSION = 1

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        """Handle a ring discovered over Bluetooth."""
        address = _normalize_mac(discovery_info.address)
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        self._discovered_address = address
        self._discovered_name = _default_name(address)
        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm adding the discovered ring."""
        if user_input is not None:
            name = (user_input.get(CONF_NAME) or self._discovered_name).strip()
            return self.async_create_entry(
                title=name,
                data={CONF_ADDRESS: self._discovered_address, CONF_NAME: name},
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=self._discovered_name): str}
            ),
            description_placeholders={"address": self._discovered_address},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add a ring by address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = _normalize_mac(user_input[CONF_ADDRESS])
            if not MAC_RE.match(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                name = (user_input.get(CONF_NAME) or "").strip() or _default_name(address)
                return self.async_create_entry(
                    title=name,
                    data={CONF_ADDRESS: address, CONF_NAME: name},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(CONF_NAME): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return PoboviRingOptionsFlow()


class PoboviRingOptionsFlow(OptionsFlow):
    """Options for the POBOVi Ring integration."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage polling and SparkyFitness options."""
        errors: dict[str, str] = {}
        options = self.config_entry.options

        if user_input is not None:
            api_key = (user_input.get(CONF_SPARKY_API_KEY) or "").strip()
            if not api_key:
                api_key = options.get(CONF_SPARKY_API_KEY, "")
            url = (user_input.get(CONF_SPARKY_URL) or "").strip()
            if user_input.get(CONF_SPARKY_ENABLED) and not api_key:
                errors[CONF_SPARKY_API_KEY] = "api_key_required"
            elif user_input.get(CONF_SPARKY_ENABLED) and not url:
                errors[CONF_SPARKY_URL] = "url_required"
            else:
                new_options = {
                    CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
                    CONF_COLLECT_SECONDS: user_input[CONF_COLLECT_SECONDS],
                    CONF_ENABLE_REALTIME: user_input[CONF_ENABLE_REALTIME],
                    CONF_SPARKY_ENABLED: user_input[CONF_SPARKY_ENABLED],
                    CONF_SPARKY_URL: url or DEFAULT_SPARKY_URL,
                    CONF_SPARKY_API_KEY: api_key,
                    CONF_SPARKY_SOURCE: (user_input.get(CONF_SPARKY_SOURCE) or DEFAULT_SPARKY_SOURCE).strip(),
                    CONF_PROFILE_ENABLED: user_input[CONF_PROFILE_ENABLED],
                    CONF_GENDER: user_input[CONF_GENDER],
                    CONF_BIRTHDATE: user_input[CONF_BIRTHDATE],
                    CONF_HEIGHT: user_input[CONF_HEIGHT],
                    CONF_WEIGHT: user_input[CONF_WEIGHT],
                    CONF_STRIDE: user_input[CONF_STRIDE],
                    CONF_CYCLE_ENABLED: user_input[CONF_CYCLE_ENABLED],
                    CONF_CYCLE_START: user_input.get(CONF_CYCLE_START, ""),
                    CONF_CYCLE_DURATION: user_input[CONF_CYCLE_DURATION],
                    CONF_CYCLE_LENGTH: user_input[CONF_CYCLE_LENGTH],
                    CONF_FIND_SECONDS: user_input[CONF_FIND_SECONDS],
                }
                return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_POLL_INTERVAL,
                        max=MAX_POLL_INTERVAL,
                        step=5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
                ),
                vol.Required(
                    CONF_COLLECT_SECONDS,
                    default=options.get(CONF_COLLECT_SECONDS, DEFAULT_COLLECT_SECONDS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_COLLECT_SECONDS,
                        max=MAX_COLLECT_SECONDS,
                        step=5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(
                    CONF_ENABLE_REALTIME,
    CONF_FIND_SECONDS,
                    default=options.get(CONF_ENABLE_REALTIME, DEFAULT_ENABLE_REALTIME),
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_SPARKY_ENABLED,
                    default=options.get(CONF_SPARKY_ENABLED, DEFAULT_SPARKY_ENABLED),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_SPARKY_URL,
                    default=options.get(CONF_SPARKY_URL, DEFAULT_SPARKY_URL),
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.URL)),
                vol.Optional(
                    CONF_SPARKY_API_KEY,
                    default="",
                ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
                vol.Optional(
                    CONF_SPARKY_SOURCE,
                    default=options.get(CONF_SPARKY_SOURCE, DEFAULT_SPARKY_SOURCE),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_PROFILE_ENABLED,
                    default=options.get(CONF_PROFILE_ENABLED, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_GENDER,
                    default=options.get(CONF_GENDER, "unspecified"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["unspecified", "male"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_BIRTHDATE,
                    default=options.get(CONF_BIRTHDATE, "1990-01-01"),
                ): selector.DateSelector(),
                vol.Optional(
                    CONF_HEIGHT,
                    default=options.get(CONF_HEIGHT, 175),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=100, max=250, step=1,
                        mode=selector.NumberSelectorMode.BOX, unit_of_measurement="cm",
                    )
                ),
                vol.Optional(
                    CONF_WEIGHT,
                    default=options.get(CONF_WEIGHT, 75),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=30, max=300, step=0.1,
                        mode=selector.NumberSelectorMode.BOX, unit_of_measurement="kg",
                    )
                ),
                vol.Optional(
                    CONF_STRIDE,
                    default=options.get(CONF_STRIDE, 0),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=150, step=1,
                        mode=selector.NumberSelectorMode.BOX, unit_of_measurement="cm",
                    )
                ),
                vol.Optional(
                    CONF_FIND_SECONDS,
                    default=options.get(CONF_FIND_SECONDS, DEFAULT_FIND_SECONDS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_FIND_SECONDS, max=MAX_FIND_SECONDS, step=5,
                        mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s",
                    )
                ),
                vol.Required(
                    CONF_CYCLE_ENABLED,
                    default=options.get(CONF_CYCLE_ENABLED, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_CYCLE_START,
                    default=options.get(CONF_CYCLE_START, ""),
                ): selector.DateSelector(),
                vol.Optional(
                    CONF_CYCLE_DURATION,
                    default=options.get(CONF_CYCLE_DURATION, 5),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=15, step=1,
                        mode=selector.NumberSelectorMode.BOX, unit_of_measurement="days",
                    )
                ),
                vol.Optional(
                    CONF_CYCLE_LENGTH,
                    default=options.get(CONF_CYCLE_LENGTH, 28),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=15, max=60, step=1,
                        mode=selector.NumberSelectorMode.BOX, unit_of_measurement="days",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
