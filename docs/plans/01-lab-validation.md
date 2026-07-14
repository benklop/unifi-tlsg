# Plan 01 — Lab validation (milestone 0.2)

Prove the v0.1 scaffold against two TL-SG2424 V2 switches and a real UniFi Network controller.

## Goals

- End-to-end adopt + stay-online
- Real CLI output fixtures replace synthetic ones
- Dual-device config path exercised
- Capture raw Inform `setparam` traffic for phase-3 mapping

## Issues

- [ ] [#1](https://github.com/benklop/unifi-tlsg/issues/1) Lab: live SSH snapshot against TL-SG2424 V2
- [ ] [#2](https://github.com/benklop/unifi-tlsg/issues/2) Lab: capture real SG2424 V2 `show` fixtures
- [ ] [#3](https://github.com/benklop/unifi-tlsg/issues/3) Lab: end-to-end UniFi discovery + adopt
- [ ] [#4](https://github.com/benklop/unifi-tlsg/issues/4) Lab: adopt state survives daemon restart
- [ ] [#5](https://github.com/benklop/unifi-tlsg/issues/5) Lab: validate AES-GCM Inform upgrade path
- [ ] [#6](https://github.com/benklop/unifi-tlsg/issues/6) Lab: run two SG2424 device agents concurrently

## Exit criteria

Device appears in UniFi, stays Connected for ≥1h, port up/down and MAC entries look plausible, restart does not require re-adopt.

