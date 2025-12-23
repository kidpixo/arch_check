#!/usr/bin/env python3
def check_smart(as_dict=False):
    """Check SMART health for all disks using smartctl. Warn if any disk is failing. Return dict if as_dict."""
    global issue_count
    import glob
    import subprocess
    results = []
    summary = {"status": "ok", "issues": 0, "error": None}
    try:
        devs = glob.glob('/dev/sd?') + glob.glob('/dev/nvme*n1')
        if not devs:
            if as_dict:
                summary["status"] = "no_disks"
                summary["error"] = "No disks found for SMART check."
                return {"devices": [], **summary}
            print_header("SMART Disk Health Summary")
            print(f"{YELLOW}No disks found for SMART check.{RESET}")
            return
        for dev in devs:
            dev_result = {"device": dev, "status": None, "attributes": [], "error": None}
            try:
                out = subprocess.check_output(["smartctl", "-H", dev], text=True, stderr=subprocess.STDOUT)
                if "PASSED" in out:
                    dev_result["status"] = "PASSED"
                    if not as_dict:
                        print(f"{GREEN}{dev}: PASSED{RESET}")
                else:
                    dev_result["status"] = out.strip()
                    summary["issues"] += 1
                    summary["status"] = "attention"
                    if not as_dict:
                        print(f"{RED}{dev}: {out.strip()}{RESET}")
                    issue_count += 1
                # Optionally collect some attributes
                attr = subprocess.check_output(["smartctl", "-A", dev], text=True, stderr=subprocess.STDOUT)
                for line in attr.splitlines():
                    if any(x in line for x in ["Reallocated_Sector_Ct", "Power_On_Hours", "Temperature_Celsius", "Media_Wearout_Indicator"]):
                        dev_result["attributes"].append(line.strip())
                        if not as_dict:
                            print(f"  {line.strip()}")
            except subprocess.CalledProcessError as e:
                dev_result["status"] = "unavailable"
                dev_result["error"] = "SMART not available or permission denied."
                if not as_dict:
                    print(f"{YELLOW}{dev}: SMART not available or permission denied.{RESET}")
            except Exception as e:
                dev_result["status"] = "error"
                dev_result["error"] = str(e)
                if not as_dict:
                    print(f"{RED}{dev}: SMART check failed: {e}{RESET}")
            results.append(dev_result)
        if as_dict:
            return {"devices": results, **summary}
        print_header("SMART Disk Health Summary")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "no_smartctl"
            summary["error"] = "smartctl command not found. Please install smartmontools."
            return {"devices": [], **summary}
        print(f"{YELLOW}smartctl command not found. Please install smartmontools.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return {"devices": [], **summary}
        print(f"{RED}SMART summary failed: {e}{RESET}")
#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse
import shutil
import platform
import logging

# --- Configuration & Colors ---
BLUE = '\033[34m'
CYAN = '\033[36m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BOLD = '\033[1m'
RESET = '\033[0m'

# The high-detail ASCII logo provided from https://github.com/deater/linux_logo
ARCH_LOGO = [
f"{CYAN}                   -`      {RESET}",
f"{CYAN}                  .o+`     {RESET}",
f"{CYAN}                 `ooo/     {RESET}",
f"{CYAN}                `+oooo:    {RESET}",
f"{CYAN}               `+oooooo:   {RESET}",
f"{CYAN}               -+oooooo+:  {RESET}",
f"{CYAN}             `/:-:++oooo+: {RESET}",
f"{CYAN}            `/++++/+++++++:{RESET}",
f"{CYAN}           `/++++++++++++++:{RESET}",
f"{CYAN}          `/+++++oooooooooo/`{RESET}",
f"{CYAN}         ./ooosssso++osssssso+`{RESET}",
f"{CYAN}        .oossssso-````/ossssss+`{RESET}",
f"{CYAN}       -osssssso.      :ssssssso.{RESET}",
f"{CYAN}      :osssssss/        osssso+++.{RESET}",
f"{CYAN}     /ossssssss/        +ssssooo/-{RESET}",
f"{CYAN}   `/ossssso+/:-        -:/+osssso+-{RESET}",
f"{CYAN}  `+sso+:-`                 `.-/+oso:{RESET}",
f"{CYAN} `++:.                           `-/+/ {RESET}",
f"{CYAN}    [ logo from deater/linux_logo ]{RESET}",
]

# Shared counter for the final summary
issue_count = 0

def print_header(title: str):
    print(f"\n{BOLD}{'='*10} {title} {'='*10}{RESET}")

# --- Helper: Device Origin ---

def get_device_origin(mount_point: str):
    try:
        # findmnt gets the source (e.g., /dev/mapper/volume-home)
        result = subprocess.check_output(["findmnt", "-nno", "SOURCE", mount_point], text=True).strip()
        dev_name = os.path.basename(result)
        # lsblk gets the parent (e.g., cryptlvm or nvme0n1)
        lineage = subprocess.check_output(["lsblk", "-no", "PKNAME", result], text=True).strip().split('\n')[-1]
        return dev_name, lineage if lineage else dev_name
    except:
        return "unknown", "unknown"

# --- Main Check Functions ---

def check_sensors(temp_warn: int = 80, as_dict=False):
    """Check and print all available sensor temperatures. Warn if any exceed temp_warn (Celsius)."""
    global issue_count
    import re
    try:
        out = subprocess.check_output(["sensors"], text=True)
        lines = out.splitlines()
        sensors = []
        high_found = False
        for line in lines:
            if "temp" in line.lower() or "core" in line.lower() or "Package id" in line:
                match = re.search(r'([+-]?[0-9]+\.[0-9])°C', line)
                if match:
                    temp = float(match.group(1))
                    entry = {
                        "label": line.strip(),
                        "temp": temp,
                        "warn": temp >= temp_warn,
                        "color": "red" if temp >= temp_warn else ("yellow" if temp >= temp_warn-10 else "green")
                    }
                    sensors.append(entry)
                    if not as_dict:
                        color = RED if temp >= temp_warn else (YELLOW if temp >= temp_warn-10 else GREEN)
                        print(f"{color}{line.strip()}{RESET}")
                    if temp >= temp_warn:
                        high_found = True
        if as_dict:
            return {
                "sensors": sensors,
                "count": len(sensors),
                "high_temp": high_found,
                "status": "warn" if high_found else "ok",
                "issues": 1 if high_found else 0
            }
        print_header("Temperature & Sensors")
        if high_found:
            print(f"{RED}{BOLD}Warning: High temperature detected!{RESET}")
            issue_count += 1
        if not lines:
            print(f"{YELLOW}No sensor data found. Is lm_sensors installed and configured?{RESET}")
    except FileNotFoundError:
        if as_dict:
            return {"sensors": [], "count": 0, "high_temp": False, "status": "no_sensors", "issues": 0, "error": "sensors command not found"}
        print(f"{YELLOW}sensors command not found. Please install lm_sensors.{RESET}")
    except Exception as e:
        if as_dict:
            return {"sensors": [], "count": 0, "high_temp": False, "status": "error", "issues": 0, "error": str(e)}
        print(f"{RED}Sensor check failed: {e}{RESET}")

def print_logo_info():
    # Gather System Info
    info = {
        'User': os.getlogin(),
        'Host': platform.node(),
        'OS': "Arch Linux",
        'Kernel': platform.release(),
        'Shell': os.environ.get('SHELL', 'N/A').split('/')[-1],
    }
    
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpu = [line.split(':')[1].strip() for line in f if "model name" in line][0]
            info['CPU'] = cpu.split('@')[0].strip()
    except: info['CPU'] = "Unknown"

    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            total = int(lines[0].split()[1]) // 1024
            avail = int(lines[2].split()[1]) // 1024
            info['Memory'] = f"{total - avail}MiB / {total}MiB"
    except: info['Memory'] = "Unknown"

    data_lines = [
        f"{CYAN}{BOLD}{info['User']}@{info['Host']}{RESET}",
        f"{'─' * (len(info['User']) + len(info['Host']) + 1)}",
        f"{BOLD}OS:{RESET} {info['OS']}",
        f"{BOLD}Kernel:{RESET} {info['Kernel']}",
        f"{BOLD}Shell:{RESET} {info['Shell']}",
        f"{BOLD}CPU:{RESET} {info['CPU']}",
        f"{BOLD}Memory:{RESET} {info['Memory']}"
    ]
    
    print("")
    for i in range(max(len(ARCH_LOGO), len(data_lines))):
        logo = ARCH_LOGO[i] if i < len(ARCH_LOGO) else " " * 20
        text = data_lines[i] if i < len(data_lines) else ""
        print(f" {logo}   {text}")

def check_disk(as_dict=False):
    """Show disk usage, filesystem, device, and origin info for key mounts. Uses lsblk -f -J and /etc/fstab."""
    import json
    import shutil
    import subprocess
    import os
    global issue_count

    import logging
    try:
        lsblk_out = subprocess.check_output(["lsblk", "-f", "-J"], text=True)
        logging.debug(f"lsblk -f -J output: {lsblk_out}")
        blkinfo = json.loads(lsblk_out)["blockdevices"]
        logging.debug(f"Parsed blkinfo: {blkinfo}")
    except Exception as e:
        if as_dict:
            return {"error": f"lsblk failed: {e}", "status": "error", "issues": 1}
        print(f"{RED}lsblk failed: {e}{RESET}")
        return

    # Parse /etc/fstab for subvolumes and mount options
    fstab_info = {}
    try:
        with open('/etc/fstab', 'r') as fstab:
            for line in fstab:
                if line.strip() and not line.strip().startswith('#'):
                    parts = line.split()
                    if len(parts) > 3:
                        fstab_info[parts[1]] = parts[3]
        logging.debug(f"fstab_info: {fstab_info}")
    except Exception as e:
        logging.debug(f"Failed to parse /etc/fstab: {e}")

    # Gather all mountpoints from lsblk and fstab
    def collect_mountpoints_from_lsblk(devs):
        mounts = set()
        for dev in devs:
            mps = dev.get('mountpoints', [])
            if mps:
                for mp in mps:
                    if mp:
                        mounts.add(mp)
            if 'children' in dev and dev['children']:
                mounts.update(collect_mountpoints_from_lsblk(dev['children']))
        return mounts

    lsblk_mounts = collect_mountpoints_from_lsblk(blkinfo)

    # Also gather mountpoints from fstab (may include unmounted targets)
    fstab_mounts = set(fstab_info.keys())

    # Union of all mountpoints, sorted for display
    all_mounts = sorted(lsblk_mounts | fstab_mounts)

    results = []
    def find_mount_and_chain(devs, mount, chain=None):
        if chain is None:
            chain = []
        for dev in devs:
            mps = dev.get('mountpoints', [])
            mps = [mp for mp in mps if mp]
            if mount in mps:
                return dev, chain + [dev]
            if "children" in dev and dev["children"]:
                found, found_chain = find_mount_and_chain(dev["children"], mount, chain + [dev]) or (None, None)
                if found:
                    return found, found_chain
        return None, None

    # Filesystem types and mount names to skip
    skip_fstypes = {
        'swap', 'tmpfs', 'devtmpfs', 'proc', 'sysfs', 'cgroup', 'mqueue', 'hugetlbfs', 'fusectl', 'configfs', 'securityfs', 'pstore',
        'efivarfs', 'debugfs', 'tracefs', 'ramfs', 'overlay', 'squashfs', 'autofs', 'binfmt_misc', 'bpf', 'nsfs',
    }
    skip_mounts = {'[SWAP]', 'none', ''}

    # Parse df -h output for all mounts
    df_info = {}
    try:
        df_out = subprocess.check_output(["df", "-hP"], text=True)
        for line in df_out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                mp = parts[5]
                df_info[mp] = {
                    "use_percent": parts[4],
                    "avail": parts[3]
                }
    except Exception as e:
        logging.debug(f"Failed to parse df -h: {e}")

    for mount in all_mounts:
        # Find device info first to check fstype
        dev_entry, chain = find_mount_and_chain(blkinfo, mount)
        fstype = dev_entry.get("fstype", "") if dev_entry else ""
        if fstype in skip_fstypes or mount in skip_mounts:
            continue

        entry = {"mount": mount}
        try:
            # Btrfs-specific reporting (optional, but will be overwritten by df below)
            if fstype == "btrfs":
                try:
                    btrfs_out = subprocess.check_output(["btrfs", "filesystem", "usage", "-b", mount], text=True)
                    total_bytes = used_bytes = free_bytes = None
                    for line in btrfs_out.splitlines():
                        if "Device size:" in line:
                            total_bytes = int(line.split(":",1)[1].strip().split()[0])
                        elif "Used:" in line and "Device size:" not in line:
                            used_bytes = int(line.split(":",1)[1].strip().split()[0])
                        elif "Free (estimated):" in line:
                            free_bytes = int(line.split(":",1)[1].strip().split()[0])
                    if total_bytes and used_bytes is not None:
                        percent = (used_bytes / total_bytes) * 100
                        entry["usage_percent"] = round(percent, 1)
                        entry["free_gb"] = round((total_bytes - used_bytes)/(2**30), 2)
                    elif total_bytes and free_bytes is not None:
                        percent = (1 - (free_bytes / total_bytes)) * 100
                        entry["usage_percent"] = round(percent, 1)
                        entry["free_gb"] = round(free_bytes/(2**30), 2)
                    else:
                        entry["usage_percent"] = "?"
                        entry["free_gb"] = "?"
                except Exception as e:
                    entry["usage_percent"] = "?"
                    entry["free_gb"] = "?"
                    entry["btrfs_error"] = str(e)
                entry["status"] = "ok"
            else:
                entry["usage_percent"] = "?"
                entry["free_gb"] = "?"
                entry["status"] = "ok"


            # Overwrite usage and free with df info only for non-Btrfs filesystems
            if fstype != "btrfs" and mount in df_info:
                try:
                    entry["usage_percent"] = float(df_info[mount]["use_percent"].strip('%'))
                except Exception:
                    entry["usage_percent"] = df_info[mount]["use_percent"]
                entry["free_gb"] = df_info[mount]["avail"]

            if entry["usage_percent"] != "?" and isinstance(entry["usage_percent"], float):
                if entry["usage_percent"] > 90:
                    entry["status"] = "critical"
                    issue_count += 1
                elif entry["usage_percent"] > 75:
                    entry["status"] = "warn"

            logging.debug(f"Searching for mount '{mount}' in blkinfo")
            # dev_entry, chain already found above
            logging.debug(f"Result for mount '{mount}': dev_entry={dev_entry}, chain={chain}")
            # Device path
            device = f"/dev/{dev_entry['name']}" if dev_entry and 'name' in dev_entry else "?"
            entry["device"] = device
            # Filesystem
            entry["fstype"] = fstype if fstype else "?"
            # Type: use 'fsver' if present, else 'type' (lsblk -f -J may not have 'type')
            entry["type"] = dev_entry.get("fsver") or dev_entry.get("type", "?") if dev_entry else "?"
            # Label
            entry["label"] = dev_entry.get("label", "") if dev_entry else ""
            # Origin chain (skip the mount leaf, join parent names)
            if chain:
                origin = '.'.join([d['name'] for d in chain])
            else:
                origin = dev_entry['name'] if dev_entry and 'name' in dev_entry else "?"
            entry["origin"] = origin
            # Subvolume from fstab only
            subvol = ""
            opts = fstab_info.get(mount, "")
            for opt in opts.split(','):
                if opt.startswith('subvol='):
                    subvol = opt.split('=',1)[1]
            entry["subvol"] = subvol
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
            logging.debug(f"Error processing mount '{mount}': {e}")
        results.append(entry)

    if as_dict:
        return {"mounts": results, "status": "ok", "issues": sum(1 for e in results if e.get("status") == "critical")}
    print_header("Disk Usage & Origins")
    print(f"{BOLD}{'Mount':<15} : {'Usage':<8} : {'Free':<10} : {'FS':<8} : {'Type':<10} : {'Device':<22} : {'Origin':<36} : {'Subvol'}{RESET}")
    print("─" * 140)
    for entry in results:
        color = GREEN if entry["status"] == "ok" else (YELLOW if entry["status"] == "warn" else RED)
        def safe(val, default="?"):
            return str(val) if val is not None else default
        print(f"{safe(entry['mount']):<15} : {color}{safe(entry.get('usage_percent')):>6}%{RESET} : {safe(entry.get('free_gb')):>7} GB : {safe(entry.get('fstype')):<8} : {safe(entry.get('type')):<10} : {safe(entry.get('device')):<22} : {safe(entry.get('origin')):<36} : {safe(entry.get('subvol'),'')}")

def check_kernel():
    global issue_count
    def _kernel_dict(installed, running, mismatch, details=None, error=None):
        return {
            "installed": installed,
            "running": running,
            "mismatch": mismatch,
            "details": details or [],
            "error": error,
            "status": "mismatch" if mismatch else "ok",
            "issues": 1 if mismatch else 0
        }

    import traceback
    def _parse_versions(installed, running):
        p_v = installed.replace('-', '.').split('.')
        r_v = running.replace('-', '.').split('.')
        return p_v, r_v

    def _labels():
        return ['Major', 'Minor', 'Patch', 'Arch Rel']

    def check_kernel_inner(as_dict=False):
        try:
            pac_out = subprocess.check_output(["pacman", "-Qi", "linux"], text=True)
            installed = next(l.split(":")[1].strip() for l in pac_out.splitlines() if l.startswith("Version"))
            running = subprocess.check_output(["uname", "-r"], text=True).strip()
            p_v, r_v = _parse_versions(installed, running)
            mismatch = False
            details = []
            for lbl, p, r in zip(_labels(), p_v, r_v):
                if p != r:
                    mismatch = True
                details.append({"component": lbl, "installed": p, "running": r, "match": p == r})
            if as_dict:
                return _kernel_dict(installed, running, mismatch, details=details)
            print_header("Kernel Version Check")
            print(f"{'Component':<12} : {'Installed':<12} : {'Running'}")
            print("─" * 45)
            for d in details:
                color = GREEN if d["match"] else RED
                eq = '==' if d["match"] else '!='
                print(f"{color}{d['component']:<12} : {d['installed']:<12} {eq} {d['running']}{RESET}")
            if mismatch:
                issue_count += 1
                print(f"\n{RED}{BOLD}![REBOOT REQUIRED]: Running kernel mismatch.{RESET}")
        except Exception as e:
            if as_dict:
                return _kernel_dict(None, None, True, error=str(e))
            print(f"{RED}Kernel check failed.{RESET}")
    return check_kernel_inner


def check_pacnew(as_dict=False):
    global issue_count
    found = [os.path.join(r, f) for r, _, fs in os.walk('/etc') for f in fs if f.endswith(('.pacnew', '.pacsave'))]
    if as_dict:
        result = {
            "files": found,
            "count": len(found),
            "status": "pending" if found else "ok",
            "issues": len(found) if found else 0
        }
        return result
    print_header("Config Files (.pacnew)")
    if found:
        issue_count += len(found)
        for f in found:
            print(f"{YELLOW}  -> {f}{RESET}")
    else:
        print(f"{GREEN}No pending merges.{RESET}")

def check_failed_services(as_dict=False):
    global issue_count
    try:
        out = subprocess.check_output(["systemctl", "list-units", "--state=failed", "--plain", "--no-legend"], text=True).strip()
        if out:
            lines = out.splitlines()
            if as_dict:
                return {
                    "failed_services": [line.split()[0] for line in lines],
                    "count": len(lines),
                    "status": "failed",
                    "issues": len(lines)
                }
            issue_count += len(lines)
            print_header("Failed Services")
            for line in lines:
                print(f"{RED}  -> {line.split()[0]}{RESET}")
        else:
            if as_dict:
                return {"failed_services": [], "count": 0, "status": "ok", "issues": 0}
            print_header("Failed Services")
            print(f"{GREEN}All units OK.{RESET}")
    except Exception as e:
        if as_dict:
            return {"failed_services": [], "count": 0, "status": "error", "issues": 0, "error": str(e)}
        pass

def check_orphans(as_dict=False):
    try:
        out = subprocess.check_output(["pacman", "-Qdtq"], text=True).strip()
        if as_dict:
            orphans = out.splitlines() if out else []
            return {
                "orphans": orphans,
                "count": len(orphans),
                "status": "found" if orphans else "ok",
                "issues": len(orphans)
            }
        print_header("Orphaned Packages")
        if out:
            print(f"{YELLOW}Orphans: {out.replace(chr(10), ', ')}{RESET}")
        else:
            print(f"{GREEN}No orphans.{RESET}")
    except Exception as e:
        if as_dict:
            return {"orphans": [], "count": 0, "status": "ok", "issues": 0, "error": str(e)}
        print(f"{GREEN}No orphans.{RESET}")

def check_stats(as_dict=False):
    try:
        def get_count(flags: str) -> int:
            try:
                out = subprocess.check_output(["pacman"] + flags.split(), text=True, stderr=subprocess.DEVNULL)
                return len(out.strip().splitlines())
            except subprocess.CalledProcessError:
                return 0

        total = get_count("-Q")
        explicit = get_count("-Qe")
        deps = get_count("-Qd")
        foreign = get_count("-Qm")
        native = total - foreign

        # Calculate Pacman Cache Size
        cache_path = "/var/cache/pacman/pkg"
        cache_size_str = "Unknown"
        if os.path.exists(cache_path):
            try:
                import sys
                du_proc = subprocess.run(["du", "-sh", cache_path], text=True, capture_output=True)
                if du_proc.returncode == 0:
                    cache_size_str = du_proc.stdout.split()[0]
                else:
                    print(du_proc.stderr, file=sys.stderr, end="")
                    cache_size_str = "Unknown (run with sudo to read /var/cache/pacman/pkg/ with du)"
            except Exception:
                cache_size_str = "Unknown (run with sudo to read /var/cache/pacman/pkg/ with du)"

        if as_dict:
            return {
                "total": total,
                "native": native,
                "foreign": foreign,
                "explicit": explicit,
                "dependencies": deps,
                "cache_size": cache_size_str,
                "status": "ok",
                "issues": 0
            }
        print_header("Pacman Statistics")
        print(f"{BOLD}{'Category':<18} : {'Count/Size'}{RESET}")
        print("─" * 35)
        print(f"{'Total Packages':<18} : {total}")
        print(f"{'  ┗━ Native':<18} : {native}")
        print(f"{'  ┗━ Foreign/AUR':<18} : {CYAN}{foreign}{RESET}")
        print("-" * 35)
        print(f"{'Explicitly Sourced':<18} : {explicit}")
        print(f"{'As Dependencies':<18} : {deps}")
        print("-" * 35)
        print(f"{'Pacman Cache Size':<18} : {YELLOW}{cache_size_str}{RESET}")
    except Exception as e:
        if as_dict:
            return {"status": "error", "issues": 0, "error": str(e)}
        print(f"{RED}Could not retrieve stats: {e}{RESET}")

# --- Main ---

def main():
    # 1. Setup Parser
    # Use RawDescriptionHelpFormatter to preserve newlines in descriptions
    parser = argparse.ArgumentParser(
        description=f"{CYAN}{BOLD}Arch Linux System Health Utility{RESET}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{BOLD}Usage Examples:{RESET}
  arch-health -a              Run every check available.
  arch-health -k -d           Check only kernel and disk status.
  arch-health -p              Scan for configuration merges.

{BOLD}Extended Descriptions:{RESET}
  {BOLD}--kernel{RESET}   Compares 'uname -r' with the version in the pacman DB. 
             If they differ, your system cannot load new modules until reboot.
             
  {BOLD}--pacnew{RESET}   Scans /etc for .pacnew and .pacsave files. These are created 
             when an update has a new default config but you've modified yours.
             
  {BOLD}--services{RESET} Queries systemd for any units in a 'failed' state. Useful for 
             catching silent background daemon crashes.
             
  {BOLD}--orphans{RESET}  Lists packages installed as dependencies but no longer required 
             by any other package. Helps keep the system lean.
             
  {BOLD}--disk{RESET}     Analyzes usage for /, /boot, and /home. Specifically tracks 
             LVM/LUKS lineage to show you the physical origin of each mount.

  {BOLD}--stats{RESET}     Show pacman package statistics (Native vs AUR)
        """
    )

    group_logo = parser.add_mutually_exclusive_group()
    _ = group_logo.add_argument("-l", "--logo", dest="logo", action="store_true", default=None, help="Print the Arch logo and hardware summary [--no-logo to suppress]")
    _ = group_logo.add_argument("--no-logo", dest="logo", action="store_false", default=None, help=argparse.SUPPRESS)
    group_sensors = parser.add_mutually_exclusive_group()
    _ = group_sensors.add_argument("--sensors", dest="sensors", action="store_true", default=None, help="Show all available temperature sensors and warn if high [--no-sensors to suppress]")
    _ = group_sensors.add_argument("--no-sensors", dest="sensors", action="store_false", default=None, help=argparse.SUPPRESS)
    group_kernel = parser.add_mutually_exclusive_group()
    _ = group_kernel.add_argument("-k", "--kernel", dest="kernel", action="store_true", default=None, help="Check for kernel/running version mismatch [--no-kernel to suppress]")
    _ = group_kernel.add_argument("--no-kernel", dest="kernel", action="store_false", default=None, help=argparse.SUPPRESS)
    group_pacnew = parser.add_mutually_exclusive_group()
    _ = group_pacnew.add_argument("-p", "--pacnew", dest="pacnew", action="store_true", default=None, help="Scan for unmerged .pacnew config files [--no-pacnew to suppress]")
    _ = group_pacnew.add_argument("--no-pacnew", dest="pacnew", action="store_false", default=None, help=argparse.SUPPRESS)
    group_services = parser.add_mutually_exclusive_group()
    _ = group_services.add_argument("-s", "--services", dest="services", action="store_true", default=None, help="List failed systemd services [--no-services to suppress]")
    _ = group_services.add_argument("--no-services", dest="services", action="store_false", default=None, help=argparse.SUPPRESS)
    group_orphans = parser.add_mutually_exclusive_group()
    _ = group_orphans.add_argument("-o", "--orphans", dest="orphans", action="store_true", default=None, help="List orphaned packages (unused dependencies) [--no-orphans to suppress]")
    _ = group_orphans.add_argument("--no-orphans", dest="orphans", action="store_false", default=None, help=argparse.SUPPRESS)
    group_disk = parser.add_mutually_exclusive_group()
    _ = group_disk.add_argument("-d", "--disk", dest="disk", action="store_true", default=None, help="Show usage, filesystem type, and LVM/LUKS origin [--no-disk to suppress]")
    _ = group_disk.add_argument("--no-disk", dest="disk", action="store_false", default=None, help=argparse.SUPPRESS)
    group_stats = parser.add_mutually_exclusive_group()
    _ = group_stats.add_argument("-t", "--stats", dest="stats", action="store_true", default=None, help="Show pacman package statistics (Native vs AUR) [--no-stats to suppress]")
    _ = group_stats.add_argument("--no-stats", dest="stats", action="store_false", default=None, help=argparse.SUPPRESS)
    group_smart = parser.add_mutually_exclusive_group()
    _ = group_smart.add_argument("--smart", dest="smart", action="store_true", default=None, help="Show SMART disk health summary (if supported) [--no-smart to suppress]")
    _ = group_smart.add_argument("--no-smart", dest="smart", action="store_false", default=None, help=argparse.SUPPRESS)
    _ = parser.add_argument("-a", "--all", action="store_true", help="Perform all health checks and show logo")
    _ = parser.add_argument("-j","--json", action="store_true", help="Output all results in JSON format for further processing")
    _ = parser.add_argument("--log-level", default="WARNING", help="Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    # Custom help output for compact style
    parser.usage = None
    parser.formatter_class = lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=32)
    
    args = parser.parse_args()
    # Set up logging
    log_level = getattr(logging, str(args.log_level).upper(), logging.WARNING)
    logging.basicConfig(level=log_level, format='[%(levelname)s] %(message)s')
    logger = logging.getLogger(__name__)
    # 2. Help/Early Exit Check
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # 3. THE ARCH CHECK (The Gatekeeper)
    if not os.path.exists("/etc/arch-release"):
        print(f"{RED}{BOLD}Error:{RESET} This script requires Arch Linux.")
        print("Required file '/etc/arch-release' not found.")
        sys.exit(1)
    
# 4. Proceed with checks...


    global issue_count
    issue_count = 0
    # Merge --feature/--no-feature into a single flag for each feature
    if args.all:
        logo_flag = True if args.logo is not False else False
        sensors_flag = True if args.sensors is not False else False
        smart_flag = True if args.smart is not False else False
        kernel_flag = True if args.kernel is not False else False
        pacnew_flag = True if args.pacnew is not False else False
        services_flag = True if args.services is not False else False
        orphans_flag = True if args.orphans is not False else False
        disk_flag = True if args.disk is not False else False
        stats_flag = True if args.stats is not False else False
    else:
        logo_flag = True if args.logo is True else False
        sensors_flag = True if args.sensors is True else False
        smart_flag = True if args.smart is True else False
        kernel_flag = True if args.kernel is True else False
        pacnew_flag = True if args.pacnew is True else False
        services_flag = True if args.services is True else False
        orphans_flag = True if args.orphans is True else False
        disk_flag = True if args.disk is True else False
        stats_flag = True if args.stats is True else False

    import json
    checks = [
        (logo_flag, print_logo_info, 'logo'),
        (sensors_flag, check_sensors, 'sensors'),
        (smart_flag, check_smart, 'smart'),
        (kernel_flag, check_kernel(), 'kernel'),
        (pacnew_flag, check_pacnew, 'pacnew'),
        (services_flag, check_failed_services, 'services'),
        (orphans_flag, check_orphans, 'orphans'),
        (disk_flag, check_disk, 'disk'),
        (stats_flag, check_stats, 'stats'),
    ]

    enabled = [name for flag, _, name in checks if flag]
    logger.debug(f"[DEBUG] Enabled checks: {enabled}")

    if args.json:
        results = {}
        for selected, func, name in checks:
            if selected:
                # All checks that support as_dict should use it
                if name in ('kernel', 'smart', 'pacnew', 'services', 'orphans', 'stats', 'sensors', 'disk'):
                    # check_sensors needs temp_warn default
                    if name == 'sensors':
                        results[name] = func(as_dict=True)
                    else:
                        results[name] = func(as_dict=True)
                else:
                    results[name] = None
        # Add summary
        results['summary'] = {
            'issues': sum((v.get('issues', 0) if isinstance(v, dict) else 0) for v in results.values() if v),
            'status': 'ok' if all((v.get('status', 'ok') == 'ok' if isinstance(v, dict) else True) for v in results.values() if v) else 'attention',
        }
        print(json.dumps(results, indent=2))
    else:
        for selected, func, name in checks:
            if selected:
                func()
        print_header("Summary")
        if issue_count == 0:
            print(f"{GREEN}{BOLD}✔ System Healthy: No issues detected.{RESET}")
        else:
            print(f"{RED}{BOLD}✘ Attention Required: {issue_count} potential issue(s) found.{RESET}")
        print("")


if __name__ == "__main__":
    main()
