# Changelog

All notable changes to arch_check are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.4.0]

### Added
- **Two new AUR checks**:
  - `--aur-stale`: Check AUR packages for version mismatches. Queries aur.archlinux.org RPC API, flags packages maintainer has marked as out of date. Requires network access.
  - `--pacman-log`: Parse `/var/log/pacman.log` for recent changes. Shows installs, upgrades, removes. Flags silent dependency removals and systems not upgraded in 30+ days. Use `--pacman-log-days N` to adjust lookback window (default: 30).
- **JSON output support** for new checks (`aur_stale`, `pacman_log`)

### Changed
- **check_systemd_timers**: Changed to informational only - no longer increments issue_count. Output now labeled "Informational" with note that timer status does not affect system health.
- **check_systemd_boot_blame**: Maintenance units (`plocate-updatedb.service`, `man-db.service`, `updatedb.service`, `mlocate-updatedb.service`) now labeled "(maintenance timer)" and excluded from threshold flagging. Total boot time threshold raised to 45 seconds.
- **check_journal_errors**: Severity scoped to `crit..alert` priority only (removes bluetooth/firmware noise).
- **check_listening_ports**: Moved to security-only group (not included in `-q` or `-a` by default).
- **check_aur_pkgbuild**: 
  - Tightened `python_inline_exec` pattern to require `-c` followed immediately by a quote (no longer matches `python -m build`, `python -m pytest`, etc.).
  - **NEW: Added intelligent safe pattern exclusions** to reduce false positives. Four known-safe patterns are now auto-whitelisted:
    - `python -c "import site..."` — Standard idiom to locate site-packages directory
    - `python -c "import sys..."` — Used to check Python version or sys.path at build time
    - `python -c "from distutils..."` — Legacy distutils path/version lookup
    - `pip install --no-deps` — Used in -bin packages to install pre-built wheels without remote dependencies
  - Whitelisted lines are tracked separately and displayed in human output under "Excluded (known safe patterns):" section with reasons
  - Whitelisted lines included in JSON output for audit trails
  - Existing exclusions (comments, checksums, dependencies) unchanged
- **check_arch_audit**: Fixed severity display grouping - each package now printed under its own severity heading.
- **Summary section**: Fixed to show only issue count table, no longer re-prints check output.

### Removed
- **`--rkhunter`**: Completely removed. rkhunter produces too many Arch-specific false positives to be useful.
  - Function `check_rkhunter` deleted
  - Argparse flags `--rkhunter` / `--no-rkhunter` deleted
  - All references removed from checks list and JSON output

### Fixed
- **check_timedatectl**: Parser correctly extracts `Timezone=`, `NTPSynchronized=`, `NTPServiceActive=`, `LocalTime=` from `timedatectl show` output.
- **check_journal_errors**: Unit name extraction now correctly parses token before `[` in journalctl output. Kernel messages properly grouped under "kernel".
- **check_listening_ports**: ss output parsing now splits on LAST colon to correctly separate address from port (handles `0.0.0.0:22`, `[::]:80`, `*:631`).

### Run Modes (Final)
```
quick (-q and -a):
  logo, sensors, kernel, pacnew, orphans, disk, stats, smart,
  timedatectl, load_avg, inotify_limit, checkupdates,
  systemd_timers, systemd_boot_blame, arch_audit,
  aur_integrity, aur_paths, aur_suid, aur_pkgbuild,
  aur_stale, pacman_log

slow (only -a):
  journal_errors, dmesg_errors

security (--security and -a):
  listening_ports, failed_logins

removed entirely:
  rkhunter
```

---

## [0.4.0] - 2026-05-26 (Previous Draft)

### Added
- **Three run modes**: `-q/--quick` for fast snapshots, `-a/--all` for full audit, `--security` for security-focused checks
- **13 new check functions**:
  - `--timedatectl`: NTP synchronization and timezone verification
  - `--load-avg`: System load average vs CPU count comparison
  - `--inotify`: Inotify watch limit usage monitoring
  - `--checkupdates`: Pending package updates display (requires pacman-contrib)
  - `--timers`: Systemd timer status and missed run detection
  - `--boot-blame`: Boot timing analysis with slowest units ranking
  - `--arch-audit`: AUR package vulnerability scanning (requires arch-audit)
  - `--journal`: Journal errors from last 24h, grouped by unit
  - `--dmesg`: Kernel ring buffer error categorization
  - `--ports`: Listening ports analysis with systemd integration
  - `--failed-logins`: Failed login attempt analysis (requires root)
  - `--rkhunter`: Rootkit scanner integration (requires rkhunter)
- **AUR security scanning suite**:
  - `--aur-integrity`: Verify AUR package file integrity with `pacman -Qk`
  - `--aur-paths`: Detect files installed outside standard paths
  - `--aur-suid`: Find setuid/setgid files with whitelist
  - `--aur-pkgbuild`: Scan PKGBUILDs for suspicious patterns (curl|sh, eval, base64, etc.)
- **Extended `--pacnew`**: Age analysis with 7-day and 90-day thresholds
- **Summary section updates**: Shows run mode, skipped checks, per-section issues

### Changed
- Refactored flag resolution to support group-based check selection
- Updated help text with comprehensive descriptions for all 24+ flags
- Summary now distinguishes between "ok", "attention", and "skipped" statuses

### Security
- Added PKGBUILD pattern scanning for common malicious techniques:
  - curl/wget piped to shell
  - eval subshell execution
  - base64 decode pipes
  - python inline exec
  - /dev/tcp connections
  - netcat reverse shells
  - dangerous rm -rf patterns

---

## [0.3.1] - 2026-03-27

### Changed
- Improved orphan package output with helpful tips and warnings
- Added caution message about reviewing orphans before removal

### Fixed
- Better orphan detection messaging for user safety

---

## [0.3.0] - 2026-01-09

### Changed
- **Major refactor**: Split AUR-specific content into separate repository `arch-check-aur`
- Cleaner separation of concerns between base tool and AUR extensions

### Removed
- AUR-specific checks moved to dedicated repository

---

## [0.2.0] - 2026-01-05

### Added
- Proper Arch Linux packaging support (PKGBUILD)
- Installation via `makepkg` for Arch users

### Changed
- Updated installation documentation
- Bumped version for Arch packaging milestone

---

## [0.1.0] - 2026-01-05

### Added
- **Initial release** with core system health checks:
  - `--disk`: Disk usage, filesystem, device origin tracking (ext4, btrfs, LVM, LUKS)
  - `--sensors`: Temperature sensor monitoring with warning thresholds
  - `--smart`: SMART disk health status
  - `--kernel`: Kernel version mismatch detection
  - `--pacnew`: Unmerged config file detection (.pacnew/.pacsave)
  - `--services`: Failed systemd service listing
  - `--orphans`: Orphaned package detection
  - `--stats`: Pacman package statistics (native vs AUR counts)
  - `--logo`: Arch Linux logo with hardware summary
- **Colorized output**: Auto-detection of terminal support
- **JSON output** (`-j`): Machine-readable output for scripting
- **Flexible CLI**: Exclusive `--no-XXX` switches for each option
- **Skipped filesystems**: Filters out virtual/temporary filesystems (tmpfs, proc, cgroup, etc.)

### Fixed
- Logo display issues
- btrfs disk info parsing

### Documentation
- Added README with usage examples
- Added screenshots
- Arch Linux installation guide

---

## Version History Summary

| Version | Date | Key Changes |
|---------|------|-------------|
| 0.4.0 | UNRELEASED | Added aur-stale, pacman-log; removed rkhunter; behavioral tuning |
| 0.4.0 | 2026-05-26 | Run modes, 13 new checks, AUR security suite (draft) |
| 0.3.1 | 2026-03-27 | Improved orphan warnings |
| 0.3.0 | 2026-01-09 | AUR split to separate repo |
| 0.2.0 | 2026-01-05 | Arch packaging support |
| 0.1.0 | 2026-01-05 | Initial release |

---

## Notes

- **0.4.0 (UNRELEASED)**: Major cleanup - removed rkhunter due to false positives, added AUR stale checking and pacman log analysis, behavioral tuning for systemd_timers and boot_blame
- **0.3.0**: Structural change to separate AUR functionality
- Pre-0.1.0 commits exist in git history but were not tagged releases
