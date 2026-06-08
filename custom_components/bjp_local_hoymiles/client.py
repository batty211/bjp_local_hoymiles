"""Read-only Hoymiles DTU client adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from google.protobuf.json_format import MessageToDict
from hoymiles_wifi.dtu import DTU

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT
from .parser import HoymilesSnapshot, parse_snapshot


class CannotConnectError(Exception):
    """Raised when the DTU cannot be reached."""


class InvalidResponseError(Exception):
    """Raised when the DTU response cannot be parsed."""


class _PortAwareDTU(DTU):
    """DTU subclass that uses the configured TCP port for all requests."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(host=host, timeout=timeout)
        self._bjp_port = port

    async def async_send_request(self, *args: Any, **kwargs: Any) -> Any:
        """Send a request using the configured DTU port."""
        kwargs["dtu_port"] = self._bjp_port
        return await super().async_send_request(*args, **kwargs)


@dataclass(slots=True)
class ReadOnlyHoymilesClient:
    """Small read-only adapter around hoymiles-wifi.

    Home Assistant modules should use this adapter rather than importing DTU
    directly, so write-capable upstream methods cannot leak into the integration.
    """

    host: str
    port: int = DEFAULT_PORT
    timeout: int = DEFAULT_TIMEOUT
    _dtu: _PortAwareDTU = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._dtu = _PortAwareDTU(
            host=self.host,
            port=self.port,
            timeout=self.timeout,
        )

    async def async_get_snapshot(self) -> HoymilesSnapshot:
        """Fetch and parse the DTU real-time data snapshot."""
        response = await self._dtu.async_get_real_data_new()
        if response is None:
            raise CannotConnectError("DTU did not return real-time data")

        payload = MessageToDict(
            response,
            preserving_proto_field_name=False,
            always_print_fields_with_no_presence=True,
        )
        try:
            return parse_snapshot(payload)
        except (TypeError, ValueError, KeyError) as err:
            raise InvalidResponseError("DTU returned an invalid payload") from err

    async def async_get_network_info(self) -> dict[str, Any] | None:
        """Fetch read-only network information for diagnostics."""
        response = await self._dtu.async_network_info()
        if response is None:
            return None
        return MessageToDict(
            response,
            preserving_proto_field_name=False,
            always_print_fields_with_no_presence=True,
        )

    async def async_get_app_information(self) -> dict[str, Any] | None:
        """Fetch read-only app/device information for diagnostics."""
        response = await self._dtu.async_app_information_data()
        if response is None:
            return None
        return MessageToDict(
            response,
            preserving_proto_field_name=False,
            always_print_fields_with_no_presence=True,
        )
