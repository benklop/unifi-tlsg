"""Main inform loop: poll TL-SG via CLI, speak UniFi Inform."""

from __future__ import annotations

import logging
import signal
import time
from pathlib import Path
from typing import Any

from unifi_tlsg.backend.cli import TlSgCliBackend
from unifi_tlsg.config import AppConfig, DeviceConfig, DeviceState
from unifi_tlsg.inform.client import InformClient
from unifi_tlsg.inform.discovery import build_discovery_packet, send_discovery
from unifi_tlsg.inform.handlers import handle_response
from unifi_tlsg.inform.payloads import build_adoption_inform, build_switch_inform
from unifi_tlsg.mapping.ports import parse_unifi_port_config, snapshot_to_inform
from unifi_tlsg.models import get_profile

logger = logging.getLogger(__name__)


class DeviceAgent:
    def __init__(self, app: AppConfig, device: DeviceConfig) -> None:
        self.app = app
        self.device = device
        self.profile = get_profile(device.model_profile)
        self.state_dir = Path(device.state_dir)
        self.state = DeviceState.load(self.state_dir, device.mac)
        self.client = InformClient()
        self.backend = TlSgCliBackend(
            device.cli, self.profile, dry_run=app.dry_run_apply
        )
        self.interval = app.inform_interval
        self._running = True

    @property
    def inform_url(self) -> str:
        return (
            self.state.inform_url
            or self.app.controller.adopt_url
            or self.app.controller.inform_url
        )

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        self.backend.connect()
        try:
            while self._running and not self.state.adopted:
                self._adoption_step()
                self._sleep(self.interval)

            logger.info("%s adopted; entering inform loop", self.device.name)
            while self._running:
                try:
                    self._inform_once()
                except Exception:
                    logger.exception("inform loop error")
                    self.interval = min(self.interval * 2, 60)
                self._sleep(self.interval)
        finally:
            self.backend.close()
            self.state.save(self.state_dir, self.device.mac)

    def adopt_once(self) -> None:
        self.backend.connect()
        try:
            self._adoption_step()
            self.state.save(self.state_dir, self.device.mac)
        finally:
            self.backend.close()

    def _adoption_step(self) -> None:
        # L2 discovery helps LAN controllers find us.
        try:
            pkt = build_discovery_packet(
                self.device.mac,
                self.device.ip,
                self.device.unifi_model,
                self.device.firmware,
            )
            send_discovery(pkt)
        except Exception:
            logger.debug("discovery broadcast failed", exc_info=True)

        payload = build_adoption_inform(self.device, self.state, self.inform_url)
        resp = self.client.send(
            self.inform_url,
            payload,
            self.device.mac,
            self.state.authkey,
            use_gcm=self.state.use_aes_gcm,
        )
        logger.info("adoption inform response: %s", resp.get("_type"))
        handle_response(resp, self.state, on_config=self._apply_config)
        self.state.save(self.state_dir, self.device.mac)

    def _inform_once(self) -> None:
        snap = self.backend.snapshot()
        ports, macs = snapshot_to_inform(snap, uplink_port=self.device.uplink_port)
        payload = build_switch_inform(
            self.device,
            self.state,
            self.profile,
            inform_url=self.inform_url,
            ports=ports,
            mac_table=macs,
            uptime=snap.uptime,
            hostname=snap.hostname or self.device.name,
        )
        resp = self.client.send(
            self.inform_url,
            payload,
            self.device.mac,
            self.state.authkey,
            use_gcm=self.state.use_aes_gcm,
        )
        new_interval = handle_response(resp, self.state, on_config=self._apply_config)
        if new_interval is not None:
            self.interval = new_interval
        self.state.save(self.state_dir, self.device.mac)

    def _apply_config(self, blob: dict[str, Any]) -> None:
        desired = parse_unifi_port_config(blob)
        if not desired:
            logger.debug("setparam contained no portable port config")
            return
        self.backend.apply_port_config(desired)
        try:
            self.backend.save_config()
        except Exception:
            logger.warning("failed to save startup-config", exc_info=True)

    def _sleep(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while self._running and time.monotonic() < end:
            time.sleep(min(0.25, end - time.monotonic()))


class ProxyDaemon:
    def __init__(self, app: AppConfig) -> None:
        self.app = app
        self.agents = [DeviceAgent(app, d) for d in app.devices]
        self._running = True

    def run(self) -> None:
        if not self.agents:
            raise SystemExit("no devices configured")
        signal.signal(signal.SIGTERM, self._signal)
        signal.signal(signal.SIGINT, self._signal)

        # Simple sequential multi-device loop for v0.1; one thread per device later.
        if len(self.agents) == 1:
            self.agents[0].run()
            return

        import threading

        threads = []
        for agent in self.agents:
            t = threading.Thread(target=agent.run, name=agent.device.name, daemon=True)
            t.start()
            threads.append(t)
        while self._running and any(t.is_alive() for t in threads):
            time.sleep(0.5)
        for agent in self.agents:
            agent.stop()

    def _signal(self, signum: int, frame: Any) -> None:
        logger.info("signal %s; shutting down", signum)
        self._running = False
        for agent in self.agents:
            agent.stop()
