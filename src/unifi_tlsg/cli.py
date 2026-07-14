"""Command-line entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from unifi_tlsg import __version__
from unifi_tlsg.config import AppConfig
from unifi_tlsg.daemon import DeviceAgent, ProxyDaemon
from unifi_tlsg.models import list_profiles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="unifi-tlsg",
        description="UniFi Inform proxy for TP-Link TL-SG smart switches",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config/unifi-tlsg.yaml",
        help="path to YAML config (default: config/unifi-tlsg.yaml)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="run inform proxy in the foreground")
    sub.add_parser("profiles", help="list built-in TL-SG model profiles")

    adopt = sub.add_parser("adopt", help="send a single adoption inform for each device")
    adopt.add_argument(
        "--url",
        help="override controller inform URL for this adoption attempt",
    )

    snap = sub.add_parser("snapshot", help="fetch a CLI snapshot from switch(es) and print summary")
    snap.add_argument("--device", help="limit to device name")

    args = parser.parse_args(argv)
    if args.command == "profiles":
        for name in list_profiles():
            print(name)
        return 0

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"config not found: {cfg_path}", file=sys.stderr)
        print("copy config/unifi-tlsg.example.yaml and edit credentials", file=sys.stderr)
        return 2

    app = AppConfig.load(cfg_path)
    logging.basicConfig(
        level=getattr(logging, app.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.command == "run":
        ProxyDaemon(app).run()
        return 0

    if args.command == "adopt":
        if args.url:
            app.controller.adopt_url = args.url
            app.controller.inform_url = args.url
        for device in app.devices:
            DeviceAgent(app, device).adopt_once()
        return 0

    if args.command == "snapshot":
        for device in app.devices:
            if args.device and device.name != args.device:
                continue
            agent = DeviceAgent(app, device)
            agent.backend.connect()
            try:
                snap_data = agent.backend.snapshot()
            finally:
                agent.backend.close()
            up = sum(1 for p in snap_data.ports if p.up)
            print(
                f"{device.name}: hostname={snap_data.hostname} "
                f"ports_up={up}/{len(snap_data.ports)} "
                f"vlans={snap_data.vlans} macs={len(snap_data.mac_table)}"
            )
            for p in snap_data.ports:
                if p.up or p.pvid != 1 or p.tagged_vlans:
                    print(
                        f"  port {p.port}: up={p.up} speed={p.speed_mbps} "
                        f"pvid={p.pvid} tagged={p.tagged_vlans}"
                    )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
