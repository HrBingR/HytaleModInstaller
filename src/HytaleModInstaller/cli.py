from __future__ import annotations

import argparse
from pathlib import Path

from .config import (
    default_config_path,
    follow_user_service_logs,
    install_user_service,
    resolve_paths,
    run_install_wizard,
    uninstall_user_service,
)
from .watcher import run_watcher


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hytalemodinstaller")

    p.add_argument(
        "--install",
        action="store_true",
        help="Interactive setup; saves config then optionally installs a user service",
    )
    p.add_argument("--staging-dir", help="Folder to watch for downloaded mods")
    p.add_argument("--mods-dir", help="Hytale Mods folder to install into")
    p.add_argument(
        "--config",
        help=f"Path to config TOML file (default: {default_config_path()})",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Process existing files in staging dir and exit (no watching)",
    )

    sub = p.add_subparsers(dest="cmd", required=False)

    sub.add_parser("run", help="Run the watcher in the foreground (default)")

    svc = sub.add_parser("service", help="Manage the systemd user service")
    svc_sub = svc.add_subparsers(dest="svc_cmd", required=True)
    svc_sub.add_parser("install", help="Install + enable + start the user service")
    svc_sub.add_parser("uninstall", help="Disable + stop + remove the user service")
    svc_sub.add_parser("logs", help="Follow service logs (journalctl)")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else default_config_path()

    if args.install:
        run_install_wizard(config_path)
        return

    if args.cmd == "service":
        if args.svc_cmd == "install":
            unit_path = install_user_service()
            print(f"Installed and started service. Unit file: {unit_path}")
            return
        if args.svc_cmd == "uninstall":
            uninstall_user_service()
            print("Service uninstalled.")
            return
        if args.svc_cmd == "logs":
            follow_user_service_logs()
            return

    # Default behavior: run
    if args.cmd is None:
        args.cmd = "run"

    if args.cmd == "run":
        staging_dir, mods_dir, archive_dir, failed_dir = resolve_paths(args, config_path=config_path)
        run_watcher(
            staging_dir=staging_dir,
            mods_dir=mods_dir,
            archive_dir=archive_dir,
            failed_dir=failed_dir,
            once=args.once,
        )
        return

    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()