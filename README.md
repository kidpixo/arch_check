# arch_check
**Arch Linux Health & Disk Origin CLI**  
*One-command system health check and disk ancestry for Arch Linux, with zero dependencies.*
# arch_check
**Arch Linux Health & Disk Origin CLI**  
*One-command system health and disk ancestry for Arch Linux, with zero Python package dependencies (relies on system binaries).*

---

## Overview

**arch_check** is a fast, no-dependency CLI tool for Arch Linux that checks your system health, disk usage, and device ancestry in a single command. It helps you quickly spot issues with disks, kernel, services, orphaned packages, and more—making system maintenance and troubleshooting effortless. Built with pure Python standard library, it glues together essential system commands and presents results in a clear, colorized format.

**Problem Solved:**
Tired of running multiple commands to check disk usage, origins (LVM, LUKS, btrfs), kernel mismatches, or orphaned packages? arch_check gives you a single, readable summary—ideal for both daily checks and troubleshooting.

---

## Key Features

- **Disk Usage & Origin:** Shows usage, free space, filesystem, and device ancestry for all major mounts (supports ext4, btrfs, LVM, LUKS). Skips virtual and temporary filesystems for clarity.
- **Temperature Sensors:** Reports all available temperature sensors and warns if any are high.
- **SMART Disk Health:** Summarizes SMART status for all disks (if supported).
- **Kernel Version Check:** Detects mismatches between running and installed kernel.
- **Config File Alerts:** Finds unmerged `.pacnew` and `.pacsave` config files.
- **Failed Services:** Lists failed systemd services.
- **Orphaned Packages:** Detects unused dependency packages.
- **Pacman Statistics:** Summarizes package counts and cache size.
- **Colorized Output:** Auto-detects terminal and supports `--color`/`--no-color`.
- **JSON Output:** Machine-readable output for scripting.

---

## Skipped Filesystems

To keep the output focused and relevant, arch_check automatically skips virtual, temporary, and special-purpose filesystems when reporting disk usage and origins. These filesystems do not represent persistent storage or user data and are typically used by the kernel or system processes.

**Skipped filesystems include:**
- swap
- tmpfs
- devtmpfs
- proc
- sysfs
- cgroup
- mqueue
- hugetlbfs
- fusectl
- configfs
- securityfs
- pstore
- efivarfs
- debugfs
- tracefs
- ramfs
- overlay
- squashfs
- autofs
- binfmt_misc
- bpf
- nsfs

**Why skip them?**
These filesystems are either virtual (`tmpfs` and `proc`), used for system internals, or provide temporary storage. They do not contain persistent user data and are not useful for health or origin checks. By skipping them, `arch_check` keeps the output clean and focused on real disks and partitions that matter for system health and maintenance.

---

## Prerequisites & Dependencies

## Prerequisites & Dependencies

- **Python:** 3.8 or newer
- **Arch Linux:** Required for full features
- **System packages:**
  - `btrfs-progs` (for btrfs usage/subvolume info)
  - `lm_sensors` (for temperature)
  - `smartmontools` (for SMART)
  - `systemd`, `pacman` (runtime utilities)

Note: Some checks (for example `smartctl`, `btrfs subvolume show`, or reading `/var/cache/pacman/pkg`) may require root privileges to return full information; run the script with `sudo` when necessary.

---

## Installation

**Recommended (pipx):**
```sh
pipx install .
```

**Arch Linux (PKGBUILD):**
```sh
makepkg -si
```
This installs the CLI as `/usr/bin/arch_check`.

---

## Usage

### Quick Start

Available switches :

```sh
  -h, --help             show this help message and exit
  -l, --logo             Print the Arch logo and hardware summary [--no-logo to suppress]
  --sensors              Show all available temperature sensors and warn if high [--no-sensors to suppress]
  -k, --kernel           Check for kernel/running version mismatch [--no-kernel to suppress]
  -p, --pacnew           Scan for unmerged .pacnew config files [--no-pacnew to suppress]
  -s, --services         List failed systemd services [--no-services to suppress]
  -o, --orphans          List orphaned packages (unused dependencies) [--no-orphans to suppress]
  -d, --disk             Show usage, filesystem type, and LVM/LUKS origin [--no-disk to suppress]
  -t, --stats            Show pacman package statistics (Native vs AUR) [--no-stats to suppress]
  --smart                Show SMART disk health summary (if supported) [--no-smart to suppress]
  -a, --all              Perform all health checks and show logo
  -j, --json             Output all results in JSON format for further processing
  --log-level LOG_LEVEL  Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --color                Enable colored output (default if terminal)
  --no-color             Disable colored output (default if piped)
  
When using `--json`, the script runs checks with `as_dict=True` where supported and includes per-section `status` and `issues` fields for easy programmatic parsing.

```

---

## Switches & Examples

Each switch can be combined or used alone, most of them have a --no-SWITCH equivalent to switch off , useful to run -a,--all and leave a few off. 
Here are the main options, with real output examples:

### `-d`, `--disk`  
**Show disk usage, filesystem, device, and origin.**

**Example (ext4, LVM, LUKS):**
```
Mount           : Usage    : Free       : FS       : Type       : Device                 : Origin                               : Subvol
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
/               :   32.0% :    127G GB : ext4     : 1.0        : /dev/volume-root       : nvme0n1.nvme0n1p2.cryptlvm.volume-root : 
/boot           :   28.0% :    370M GB : vfat     : FAT32      : /dev/nvme0n1p1         : nvme0n1.nvme0n1p1                    : 
/home           :   41.0% :    909G GB : ext4     : 1.0        : /dev/volume-home       : nvme0n1.nvme0n1p2.cryptlvm.volume-home : 
```

**Example (btrfs, subvolumes):**
```
Mount           : Usage    : Free       : FS       : Type       : Device                 : Origin                               : Subvol
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
/               :   56.5% :   63.77 GB : btrfs    : ?          : /dev/nvme0n1p2         : nvme0n1.nvme0n1p2                    : /@
/.snapshots     :   56.5% :   63.77 GB : btrfs    : ?          : /dev/nvme0n1p2         : nvme0n1.nvme0n1p2                    : /@.snapshots
/boot           :   75.0% :    133M GB : vfat     : FAT32      : /dev/nvme0n1p1         : nvme0n1.nvme0n1p1                    :
/home           :   56.5% :   63.77 GB : btrfs    : ?          : /dev/nvme0n1p2         : nvme0n1.nvme0n1p2                    : /@home
/media/1tb      :   51.0% :    861G GB : ext4     : 1.0        : /dev/sda1              : sda.sda1                             :
/media/1tb_2    :   51.0% :    859G GB : ext4     : 1.0        : /dev/sdb1              : sdb.sdb1                             :
/var/cache/pacman/pkg :   56.5% :   63.77 GB : btrfs    : ?          : /dev/nvme0n1p2         : nvme0n1.nvme0n1p2                    : /@pkg
/var/log        :   56.5% :   63.77 GB : btrfs    : ?          : /dev/nvme0n1p2         : nvme0n1.nvme0n1p2                    : /@log
```

(Numeric btrfs Usage/Free requires `btrfs-progs` and appropriate privileges — use `sudo` if the current user cannot run `btrfs` commands.)
```

### `--sensors`  
**Show all available temperature sensors and warn if high.**

**Example:**
```
temp1:        +45.0°C
temp1:        +54.0°C
Core 0:        +43.0°C  (high = +105.0°C, crit = +105.0°C)
```

### `--smart`  
**Show SMART disk health summary (if supported).**

**Example:**
```
/dev/nvme0n1: SMART not available or permission denied.
/dev/sdb: SMART not available or permission denied.
```

### `-k`, `--kernel`  
**Check for kernel/running version mismatch.**

**Example:**
```
Component    : Installed    : Running
─────────────────────────────────────────────
Major        : 6            == 6
Minor        : 18           == 18
Patch        : 2            != 1
Arch Rel     : arch2        != arch1
Kernel check failed.
```

### `-p`, `--pacnew`  
**Scan for unmerged .pacnew config files.**

**Example:**
```
========== Config Files (.pacnew) ==========
  -> /etc/pacman.conf.pacnew
  -> /etc/makepkg.conf.pacnew
  -> /etc/makepkg.conf.d/fortran.conf.pacnew
  -> /etc/pulse/default.pa.pacnew
  -> /etc/pulse/default.pa.pacsave
```

### `-s`, `--services`  
**List failed systemd services.**

**Example:**
```
	-> docker-compose@jellifyn.service
```

### `-o`, `--orphans`  
**List orphaned packages (unused dependencies).**

**Example:**
```
Orphans: argon2, asciidoc, bridge-utils, ...
```

### `-t`, `--stats`  
**Show pacman package statistics (Native vs AUR).**

**Example:**
```
Total Packages     : 1876
	┗━ Native        : 1788
	┗━ Foreign/AUR   : 88
Explicitly Sourced : 432
As Dependencies    : 1444
Pacman Cache Size  : 50G
```

### `-a`, `--all`  
**Run all checks and show summary.**

---

## Contributing

Found a bug or want to add a feature? Please open an issue or submit a pull request on the [GitHub repository](https://github.com/kidpixo/arch_check). For major changes, open an issue first to discuss what you’d like to change.

---

## License

**0BSD** — Free for any use, no warranty.

## Troubleshooting

- No numeric btrfs usage shown for `-d`:
  - Ensure `btrfs-progs` is installed: `sudo pacman -S btrfs-progs`.
  - Try running `sudo btrfs filesystem df -b /` to inspect totals and used bytes for the filesystem.

- SMART output is empty or permission denied:
  - `smartctl` often requires root: run `sudo smartctl -H /dev/sdX` (replace `/dev/sdX` with your device).

- `sensors` shows nothing:
  - Install and configure `lm_sensors`, then run `sensors`. Run `sudo sensors-detect` if needed.

- Pacman cache size or some package stats are missing:
  - Reading `/var/cache/pacman/pkg` may require privileges; try `sudo du -sh /var/cache/pacman/pkg`.

## JSON Output (short schema example)

When using `--json`, `arch_check` returns a top-level object with keys for each enabled check and a `summary` object. Each section provides `status` and `issues` where applicable. Minimal example:

```json
{
  "disk": {
    "mounts": [
      {
        "mount": "/",
        "usage_percent": 56.5,
        "free_gb": 63.77,
        "fstype": "btrfs",
        "device": "/dev/nvme0n1p2",
        "origin": "nvme0n1.nvme0n1p2",
        "subvol": "/@"
      }
    ],
    "status": "ok",
    "issues": 0
  },
  "summary": {
    "issues": 35,
    "status": "attention"
  }
}
```

For scripting, check the per-section `status` and `issues` fields to determine if work is required.
