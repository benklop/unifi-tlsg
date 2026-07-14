"""HTTP client for UniFi /inform."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from unifi_tlsg.config import DEFAULT_AUTHKEY
from unifi_tlsg.inform.protocol import decode_inform, encode_inform

logger = logging.getLogger(__name__)


class InformClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def send(
        self,
        url: str,
        payload: dict[str, Any],
        mac: str,
        authkey: str = DEFAULT_AUTHKEY,
        *,
        use_gcm: bool = False,
    ) -> dict[str, Any]:
        body = encode_inform(payload, mac, authkey, use_gcm=use_gcm)
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-binary",
            "User-Agent": "AirControl Agent v1.0",
        }
        logger.debug("POST inform %s (%d bytes)", url, len(body))
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(url, content=body, headers=headers)
        except httpx.HTTPError as exc:
            return {"_type": "urlerror", "msg": str(exc)}

        if resp.status_code >= 400:
            return {
                "_type": "httperror",
                "code": str(resp.status_code),
                "msg": resp.reason_phrase or "",
            }
        try:
            return decode_inform(resp.content, authkey)
        except Exception as exc:
            logger.exception("failed to decode inform response")
            return {"_type": "decodeerror", "msg": str(exc)}
