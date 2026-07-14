# Plan 06 — Testing strategy

Automated coverage for protocol/CLI/mapping, plus a documented lab checklist. Synthetic fixtures exist today; live-firmware fixtures and mocks are still missing.

## Current baseline

- Unit: Inform CBC/GCM roundtrip
- Unit: parser fixtures (synthetic status/switchport/MAC)
- Unit: port mapping + dry-run apply smoke
- Lint: ruff

## Issues

- [ ] [#26](https://github.com/benklop/unifi-tlsg/issues/26) Test: Inform response handler unit tests
- [ ] [#27](https://github.com/benklop/unifi-tlsg/issues/27) Test: discovery TLV unit tests
- [ ] [#28](https://github.com/benklop/unifi-tlsg/issues/28) Test: Inform decode error-path coverage
- [ ] [#29](https://github.com/benklop/unifi-tlsg/issues/29) Test: InformClient HTTP mock tests
- [ ] [#30](https://github.com/benklop/unifi-tlsg/issues/30) Test: fake SSH session integration tests
- [ ] [#31](https://github.com/benklop/unifi-tlsg/issues/31) Test: golden CLI sequences for port apply
- [ ] [#32](https://github.com/benklop/unifi-tlsg/issues/32) Test: setparam mapping fixtures from captured UniFi configs
- [ ] [#33](https://github.com/benklop/unifi-tlsg/issues/33) Test: GitHub Actions CI for pytest + ruff
- [ ] [#34](https://github.com/benklop/unifi-tlsg/issues/34) Test: lab marker + CLI fixture capture script
- [ ] [#35](https://github.com/benklop/unifi-tlsg/issues/35) Test: document and execute manual lab checklist

## Lab test checklist (manual)

Documented procedure for hardware validation (not CI):

1. `unifi-tlsg snapshot` both switches
2. Adopt device A, confirm Connected
3. Flap a port; confirm UniFi port state updates
4. Learn a MAC on an access port; confirm topology/clients
5. With `dry_run_apply: true`, push VLAN change; review logged CLI
6. Enable apply; verify `show interface switchport`
7. Restart daemon; confirm no re-adopt required
8. Repeat adopt for device B; concurrent run

## Exit criteria

CI green on every PR; lab checklist completed once on both SG2424s before 1.0.

