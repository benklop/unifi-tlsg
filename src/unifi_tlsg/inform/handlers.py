"""Handle controller Inform responses (setparam / cmd / noop)."""

from __future__ import annotations

import logging
from typing import Any, Callable

from unifi_tlsg.config import DeviceState

logger = logging.getLogger(__name__)

ApplyConfigFn = Callable[[dict[str, Any]], None]


def handle_response(
    response: dict[str, Any],
    state: DeviceState,
    *,
    on_config: ApplyConfigFn | None = None,
) -> float | None:
    """Process a controller response.

    Returns a new inform interval if the response specifies one, else None.
    """
    rtype = response.get("_type", "")

    if rtype == "noop":
        return float(response.get("interval", 10))

    if rtype == "setparam":
        _handle_setparam(response, state, on_config=on_config)
        return None

    if rtype == "cmd":
        _handle_cmd(response, state)
        return None

    if rtype == "setdefault":
        logger.warning("controller requested setdefault / forget")
        state.adopted = False
        state.authkey = "ba86f2bbe107c7c57eb5f2690775c712"
        state.use_aes_gcm = False
        state.cfgversion = ""
        return None

    if rtype == "reboot":
        logger.info("controller reboot request ignored (proxy host stays up)")
        return None

    if rtype in {"httperror", "urlerror", "decodeerror"}:
        logger.warning("inform transport error: %s", response)
        return 60.0

    if rtype:
        logger.debug("unhandled inform response type %s: keys=%s", rtype, list(response))
    return None


def _handle_setparam(
    response: dict[str, Any],
    state: DeviceState,
    *,
    on_config: ApplyConfigFn | None,
) -> None:
    state.adopted = True

    if "mgmt_cfg" in response:
        _parse_mgmt_cfg(str(response["mgmt_cfg"]), state)

    if "cfgversion" in response:
        state.cfgversion = str(response["cfgversion"])

    # system_cfg / port overrides are where VLAN / port mode live.
    config_blob: dict[str, Any] = {}
    for key in ("system_cfg", "port_overrides", "vlan_config"):
        if key in response:
            config_blob[key] = response[key]

    # Some controllers embed port config as mgmt-style key=value lines.
    for key, value in response.items():
        if key.startswith("port.") or key in {"vlan", "switch"}:
            config_blob[key] = value

    if config_blob and on_config is not None:
        on_config(config_blob)

    for key, value in response.items():
        if key in {"_type", "server_time_in_utc", "blocked_sta", "mgmt_cfg"}:
            continue
        state.extra[key] = value


def _parse_mgmt_cfg(data: str, state: DeviceState) -> None:
    for row in data.splitlines():
        if "=" not in row:
            continue
        key, value = row.split("=", 1)
        if key == "cfgversion":
            state.cfgversion = value
        elif key == "authkey":
            state.authkey = value
        elif key == "use_aes_gcm":
            state.use_aes_gcm = value.lower() in {"1", "true", "yes"}
        elif key in {"mgmt_url", "inform_url"}:
            if key == "mgmt_url":
                state.mgmt_url = value
            else:
                state.inform_url = value
        else:
            state.extra[f"mgmt.{key}"] = value


def _handle_cmd(response: dict[str, Any], state: DeviceState) -> None:
    cmd = response.get("cmd", "")
    if cmd == "set-locate":
        state.locating = True
        logger.info("locate mode enabled")
    elif cmd == "unset-locate":
        state.locating = False
        logger.info("locate mode disabled")
    else:
        logger.info("ignoring cmd %s", cmd)
