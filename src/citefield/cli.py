"""Command line entry point. Commands arrive with their phases: extract (5), serve (5), eval (3)."""

from __future__ import annotations

import argparse

from citefield import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citefield", description="Document field extraction with cited sources.")
    parser.add_argument("--version", action="version", version=f"citefield {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0
