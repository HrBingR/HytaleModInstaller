# src/HytaleModInstaller/watcher.py
from __future__ import annotations

import shutil
import sys
import time
import zipfile
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

IGNORE_SUFFIXES = (".part", ".tmp", ".crdownload")
POLL_STABLE_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 60.0


def is_interesting(path: Path) -> bool:
    if not path.is_file():
        return False
    low = path.name.lower()
    if low.endswith(IGNORE_SUFFIXES):
        return False
    return low.endswith(".jar") or low.endswith(".zip")


def wait_for_stable_size(path: Path, timeout: float = POLL_TIMEOUT_SECONDS) -> bool:
    """Wait until the file size hasn't changed for POLL_STABLE_SECONDS."""
    start = time.time()
    last_size = -1
    last_change = time.time()

    while time.time() - start < timeout:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False

        if size != last_size:
            last_size = size
            last_change = time.time()
        else:
            if time.time() - last_change >= POLL_STABLE_SECONDS:
                return True

        time.sleep(0.25)

    return False


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            # zip-slip protection
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"Unsafe path in zip: {member.filename}")
        zf.extractall(dest_dir)


def ensure_dirs(staging_dir: Path, mods_dir: Path, archive_dir: Path, failed_dir: Path) -> None:
    for d in (staging_dir, mods_dir, archive_dir, failed_dir):
        d.mkdir(parents=True, exist_ok=True)


def install_file(
        path: Path,
        *,
        mods_dir: Path,
        staging_dir: Path,
        archive_dir: Path,
        failed_dir: Path,
) -> None:
    ensure_dirs(staging_dir, mods_dir, archive_dir, failed_dir)

    if not wait_for_stable_size(path):
        raise RuntimeError("Timed out waiting for download to finish")

    suffix = path.suffix.lower()
    if suffix == ".jar":
        target = mods_dir / path.name
        if target.exists():
            stamp = time.strftime("%Y%m%d-%H%M%S")
            target = mods_dir / f"{path.stem}-{stamp}{path.suffix}"
        shutil.copy2(path, target)
        return

    if suffix == ".zip":
        safe_extract_zip(path, mods_dir)
        return


def archive(
        path: Path,
        *,
        ok: bool,
        staging_dir: Path,
        mods_dir: Path,
        archive_dir: Path,
        failed_dir: Path,
        reason: str | None = None,
) -> None:
    ensure_dirs(staging_dir, mods_dir, archive_dir, failed_dir)

    dest_base = archive_dir if ok else failed_dir
    dest = dest_base / path.name
    if dest.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = dest_base / f"{path.stem}-{stamp}{path.suffix}"

    shutil.move(str(path), str(dest))

    if reason:
        log = dest.with_suffix(dest.suffix + ".log.txt")
        log.write_text(reason + "\n", encoding="utf-8")


class Handler(FileSystemEventHandler):
    def __init__(self, *, staging_dir: Path, mods_dir: Path, archive_dir: Path, failed_dir: Path):
        super().__init__()
        self.staging_dir = staging_dir
        self.mods_dir = mods_dir
        self.archive_dir = archive_dir
        self.failed_dir = failed_dir

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if not is_interesting(path):
            return

        try:
            print(f"[+] Detected: {path.name}")
            install_file(
                path,
                mods_dir=self.mods_dir,
                staging_dir=self.staging_dir,
                archive_dir=self.archive_dir,
                failed_dir=self.failed_dir,
            )
            print(f"[✓] Installed: {path.name}")
            archive(
                path,
                ok=True,
                staging_dir=self.staging_dir,
                mods_dir=self.mods_dir,
                archive_dir=self.archive_dir,
                failed_dir=self.failed_dir,
            )
        except Exception as e:
            print(f"[!] Failed: {path.name}: {e}", file=sys.stderr)
            try:
                archive(
                    path,
                    ok=False,
                    staging_dir=self.staging_dir,
                    mods_dir=self.mods_dir,
                    archive_dir=self.archive_dir,
                    failed_dir=self.failed_dir,
                    reason=str(e),
                )
            except Exception as e2:
                print(f"[!] Also failed to archive {path.name}: {e2}", file=sys.stderr)


def process_existing(*, staging_dir: Path, mods_dir: Path, archive_dir: Path, failed_dir: Path) -> None:
    """
    Process any already-present .jar/.zip files in the staging dir.
    This makes one-off usage work and also handles downloads completed while the service was down.
    """
    if not staging_dir.exists():
        return

    for path in sorted(staging_dir.iterdir()):
        if not is_interesting(path):
            continue
        try:
            print(f"[+] Found existing: {path.name}")
            install_file(
                path,
                mods_dir=mods_dir,
                staging_dir=staging_dir,
                archive_dir=archive_dir,
                failed_dir=failed_dir,
            )
            print(f"[✓] Installed: {path.name}")
            archive(
                path,
                ok=True,
                staging_dir=staging_dir,
                mods_dir=mods_dir,
                archive_dir=archive_dir,
                failed_dir=failed_dir,
            )
        except Exception as e:
            print(f"[!] Failed: {path.name}: {e}", file=sys.stderr)
            try:
                archive(
                    path,
                    ok=False,
                    staging_dir=staging_dir,
                    mods_dir=mods_dir,
                    archive_dir=archive_dir,
                    failed_dir=failed_dir,
                    reason=str(e),
                )
            except Exception as e2:
                print(f"[!] Also failed to archive {path.name}: {e2}", file=sys.stderr)


def run_watcher(*, staging_dir: Path, mods_dir: Path, archive_dir: Path, failed_dir: Path, once: bool = False) -> None:
    ensure_dirs(staging_dir, mods_dir, archive_dir, failed_dir)
    print(f"Watching: {staging_dir}")
    print(f"Installing to: {mods_dir}")

    process_existing(
        staging_dir=staging_dir,
        mods_dir=mods_dir,
        archive_dir=archive_dir,
        failed_dir=failed_dir,
    )

    if once:
        return

    observer = Observer()
    observer.schedule(
        Handler(staging_dir=staging_dir, mods_dir=mods_dir, archive_dir=archive_dir, failed_dir=failed_dir),
        str(staging_dir),
        recursive=False,
    )
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()