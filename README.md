# arch_chek

Arch Linux system health and disk origin checker CLI.
Written only with python stdlib, no dependencies. 
It is a glorified cli command glue and frontend.

## Features
- Shows disk usage and device ancestry for all major mounts
- Reports temperature sensors
- Checks SMART disk health
- Kernel, pacnew, failed services, orphaned packages, and more

## Usage

```sh
arch_chek -d           # Show disk usage and device origins
arch_chek --sensors    # Show temperature sensors
arch_chek --smart      # Show SMART disk health
arch_chek -a           # Run all checks
arch_chek --help       # Show all options
```

## Install (Recommended: pipx)

```sh
pipx install .
```

## Install via PKGBUILD (Arch Linux)

```sh
makepkg -si
```

This will install the CLI as `/usr/bin/arch_chek`.

## Requirements
- Python 3.8+
- Arch Linux (for full features)
- lm_sensors, smartmontools, systemd, pacman

## License
MIT
