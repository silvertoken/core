"""Support for ISY994 switches."""
from typing import Callable

from pyisy.constants import ISY_VALUE_UNKNOWN, PROTO_GROUP

from homeassistant.components.switch import DOMAIN as SWITCH, SwitchEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.typing import ConfigType

from . import ISY994_NODES, ISY994_PROGRAMS
from .const import _LOGGER
from .entity import ISYNodeEntity, ISYProgramEntity


def setup_platform(
    hass, config: ConfigType, add_entities: Callable[[list], None], discovery_info=None
):
    """Set up the ISY994 switch platform."""
    devices = []
    for node in hass.data[ISY994_NODES][SWITCH]:
        devices.append(ISYSwitchEntity(node))

    for name, status, actions in hass.data[ISY994_PROGRAMS][SWITCH]:
        devices.append(ISYSwitchProgramEntity(name, status, actions))

    add_entities(devices)


class ISYSwitchEntity(ISYNodeEntity, SwitchEntity):
    """Representation of an ISY994 switch device."""

    @property
    def is_on(self) -> bool:
        """Get whether the ISY994 device is in the on state."""
        if self.value == ISY_VALUE_UNKNOWN:
            return STATE_UNKNOWN
        return bool(self.value)

    def turn_off(self, **kwargs) -> None:
        """Send the turn off command to the ISY994 switch."""
        if not self._node.turn_off():
            _LOGGER.debug("Unable to turn off switch.")

    def turn_on(self, **kwargs) -> None:
        """Send the turn on command to the ISY994 switch."""
        if not self._node.turn_on():
            _LOGGER.debug("Unable to turn on switch.")

    @property
    def icon(self) -> str:
        """Get the icon for groups."""
        if hasattr(self._node, "protocol") and self._node.protocol == PROTO_GROUP:
            return "mdi:google-circles-communities"  # Matches isy scene icon
        return super().icon


class ISYSwitchProgramEntity(ISYProgramEntity, SwitchEntity):
    """A representation of an ISY994 program switch."""

    @property
    def is_on(self) -> bool:
        """Get whether the ISY994 switch program is on."""
        return bool(self.value)

    def turn_on(self, **kwargs) -> None:
        """Send the turn on command to the ISY994 switch program."""
        if not self._actions.run_then():
            _LOGGER.error("Unable to turn on switch")

    def turn_off(self, **kwargs) -> None:
        """Send the turn off command to the ISY994 switch program."""
        if not self._actions.run_else():
            _LOGGER.error("Unable to turn off switch")

    @property
    def icon(self) -> str:
        """Get the icon for programs."""
        return "mdi:script-text-outline"  # Matches isy program icon
