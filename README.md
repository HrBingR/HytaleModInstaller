# HytaleModInstaller

A small CLI tool to install Hytale mods on Linux (Flatpak) by watching a staging folder for downloads and copying/extracting them into your Hytale Mods directory.

It’s designed to be installed with `pipx` and can optionally run continuously via a **systemd user service**.

## Features

- Watches a staging directory for new mod files
- Installs:
  - `.jar` mods by copying into the Mods folder
  - `.zip` mods by extracting into the Mods folder (with zip-slip protection)
- Archives processed files into:
  - `installed/` on success
  - `failed/` on failure (with a `.log.txt` reason)
- Config stored in the standard XDG config location
- Optional systemd **user** service for “always-on” monitoring

## Requirements

- Python **3.11+**
- Linux (systemd recommended if you want the service)

## Install

### Using pipx (recommended)
