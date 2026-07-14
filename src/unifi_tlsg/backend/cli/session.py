"""SSH session helper for TP-Link TL-SG CLI."""

from __future__ import annotations

import logging
import re
import time
from typing import Iterable

import paramiko

from unifi_tlsg.config import SwitchCliConfig

logger = logging.getLogger(__name__)

PROMPT_RE = re.compile(r"[\w\-().]+(?:\([\w\-]+\))?[#>] ?$")


class CliSession:
    """Interactive SSH CLI session with privileged / config modes."""

    def __init__(self, cfg: SwitchCliConfig) -> None:
        self.cfg = cfg
        self._client: paramiko.SSHClient | None = None
        self._chan: paramiko.Channel | None = None
        self._buf = ""

    def connect(self) -> None:
        if self.cfg.transport != "ssh":
            raise NotImplementedError(
                f"transport {self.cfg.transport!r} not implemented yet; use ssh"
            )
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info("SSH connect %s@%s:%s", self.cfg.username, self.cfg.host, self.cfg.port)
        client.connect(
            hostname=self.cfg.host,
            port=self.cfg.port,
            username=self.cfg.username,
            password=self.cfg.password,
            look_for_keys=False,
            allow_agent=False,
            timeout=self.cfg.timeout,
        )
        chan = client.invoke_shell(width=200, height=50)
        chan.settimeout(self.cfg.timeout)
        self._client = client
        self._chan = chan
        self._read_until_prompt()
        # Enter privileged EXEC if we landed on '>'
        if self._buf.rstrip().endswith(">"):
            self.cmd("enable", expect_password=True)

    def close(self) -> None:
        if self._chan is not None:
            self._chan.close()
        if self._client is not None:
            self._client.close()
        self._chan = None
        self._client = None

    def cmd(self, command: str, *, expect_password: bool = False) -> str:
        assert self._chan is not None
        self._chan.send(command + "\n")
        if expect_password:
            self._read_until(re.compile(r"[Pp]assword: ?$"))
            pw = self.cfg.enable_password or self.cfg.password
            self._chan.send(pw + "\n")
        return self._read_until_prompt()

    def configure(self, lines: Iterable[str]) -> str:
        """Run commands starting from privileged EXEC via `configure`."""
        out = [self.cmd("configure")]
        try:
            for line in lines:
                out.append(self.cmd(line))
        finally:
            out.append(self.cmd("end"))
        return "\n".join(out)

    def _read_until_prompt(self) -> str:
        return self._read_until(PROMPT_RE)

    def _read_until(self, pattern: re.Pattern[str]) -> str:
        assert self._chan is not None
        deadline = time.monotonic() + self.cfg.timeout
        collected = ""
        while time.monotonic() < deadline:
            if self._chan.recv_ready():
                chunk = self._chan.recv(65535).decode("utf-8", errors="replace")
                # Normalize CR and strip ANSI-ish noise.
                chunk = chunk.replace("\r", "")
                collected += chunk
                self._buf = collected
                # Match against last non-empty line.
                last = collected.strip().splitlines()[-1] if collected.strip() else ""
                if pattern.search(last):
                    return _strip_echo(collected)
            else:
                time.sleep(0.05)
        raise TimeoutError(f"CLI timeout waiting for {pattern.pattern}; got: {collected[-200:]!r}")


def _strip_echo(text: str) -> str:
    """Drop the echoed command line and trailing prompt."""
    lines = text.splitlines()
    if len(lines) >= 2:
        # First line is usually the echo; last is the prompt.
        return "\n".join(lines[1:-1]).strip()
    return text.strip()
