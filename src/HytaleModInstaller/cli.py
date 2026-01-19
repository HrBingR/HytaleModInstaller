from __future__ import annotations

import argparse
from pathlib import Path

from .config import default_config_path, resolve_paths, run_install_wizard
from .watcher import run_watcher


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hytalemodinstaller")

    p.add_argument(
        "--install",
        action="store_true",
        help="Interactive setup; saves config then exits",
    )
    p.add_argument("--staging-dir", help="Folder to watch for downloaded mods")
    p.add_argument("--mods-dir", help="Hytale Mods folder to install into")
    p.add_argument(
        "--config",
        help=f"Path to config TOML file (default: {default_config_path()})",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else default_config_path()

    if args.install:
        run_install_wizard(config_path)
        return

    staging_dir, mods_dir, archive_dir, failed_dir = resolve_paths(args, config_path=config_path)
    run_watcher(
        staging_dir=staging_dir,
        mods_dir=mods_dir,
        archive_dir=archive_dir,
        failed_dir=failed_dir,
    )


if __name__ == "__main__":
    main()