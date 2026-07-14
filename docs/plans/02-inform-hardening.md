# Plan 02 — Inform protocol hardening

Make Inform adoption and heartbeat behave like a real UniFi switch under modern controllers.

## Issues

- [ ] [#7](https://github.com/benklop/unifi-tlsg/issues/7) Inform: dump unknown setparam/mgmt_cfg/cmd keys
- [ ] [#8](https://github.com/benklop/unifi-tlsg/issues/8) Inform: expand US24 inform payload for modern controllers
- [ ] [#9](https://github.com/benklop/unifi-tlsg/issues/9) Inform: discovery TLV audit vs real UniFi switch
- [ ] [#10](https://github.com/benklop/unifi-tlsg/issues/10) Inform: correct cfgversion reporting after successful apply
- [ ] [#11](https://github.com/benklop/unifi-tlsg/issues/11) Inform: handle upgrade/reboot/setdefault/locate commands

## Notes

Controller versions differ in required JSON. Prefer capturing a real US-24 (or USW-24) inform exchange if available; otherwise iterate from controller logs / adopt failures.

