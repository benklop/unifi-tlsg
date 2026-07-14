# Plan 04 — VLAN / port config apply (milestone 0.3)

Translate UniFi provisioning into TL-SG CLI with safe, idempotent applies.

## Issues

- [ ] [#19](https://github.com/benklop/unifi-tlsg/issues/19) Config: capture real UniFi setparam provisioning blobs
- [ ] [#20](https://github.com/benklop/unifi-tlsg/issues/20) Config: resolve UniFi network object IDs to 802.1Q VLAN IDs
- [ ] [#21](https://github.com/benklop/unifi-tlsg/issues/21) Config: access/trunk/disable/name apply and verify on SG2424
- [ ] [#22](https://github.com/benklop/unifi-tlsg/issues/22) Config: debounce copy running-config startup-config
- [ ] [#23](https://github.com/benklop/unifi-tlsg/issues/23) Config: report unsupported UniFi switch features

## Exit criteria

Changing a port to access VLAN N or trunk native/tagged in UniFi results in matching `show interface switchport` on the TL-SG without manual CLI.

