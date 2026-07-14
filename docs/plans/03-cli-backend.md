# Plan 03 — CLI backend hardening

SSH/CLI is the management plane. Parsers and session handling must match SG2424 V2 firmware reality.

## Issues

- [ ] [#12](https://github.com/benklop/unifi-tlsg/issues/12) CLI: disable/handle terminal paging (--More--)
- [ ] [#13](https://github.com/benklop/unifi-tlsg/issues/13) CLI: harden enable / configure mode transitions
- [ ] [#14](https://github.com/benklop/unifi-tlsg/issues/14) CLI: parse `show interface counters` into port stats
- [ ] [#15](https://github.com/benklop/unifi-tlsg/issues/15) CLI: detect combo port media-type (rj45/sfp)
- [ ] [#16](https://github.com/benklop/unifi-tlsg/issues/16) CLI: idempotent VLAN/port sync with stale membership cleanup
- [ ] [#17](https://github.com/benklop/unifi-tlsg/issues/17) CLI: reconnect and partial-failure handling
- [ ] [#18](https://github.com/benklop/unifi-tlsg/issues/18) CLI: optional telnet transport

## References

- [TL-SG2424 V2 CLI](https://static.tp-link.com/resources/document/TL-SG2424_V2_CLI.pdf)
- Interface naming: `gigabitEthernet 1/0/N`; combo ports 21–24

