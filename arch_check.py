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

def check_disk():
    global issue_count
    print_header("Disk Usage & Origins")
    critical_mounts = ['/', '/boot', '/home', '/var']
    print(f"{BOLD}{'Mount':<15} : {'Usage':<8} : {'Free':<10} : {'FS':<8} : {'Type':<10} : {'Device':<22} : {'Origin':<20} : {'Subvol'}{RESET}")
    print("─" * 140)

    # Get mount -> fs type
    with open('/proc/mounts', 'r') as f:
        mount_data = {l.split()[1]: l.split()[2] for l in f if l.split()[1] in critical_mounts}

    # Get lsblk info as JSON
    import json
    lsblk_out = subprocess.check_output(["lsblk", "-J", "-o", "NAME,TYPE,MOUNTPOINT,FSTYPE"] , text=True)
    blkinfo = json.loads(lsblk_out)["blockdevices"]

    def find_chain_and_dev_by_mount(mount):
        # Recursively walk lsblk tree to find the chain and device info for a mountpoint
        def walk(dev, chain):
            if dev.get("mountpoint") == mount:
                return (chain + [dev["name"]], dev)
            for child in dev.get("children", []):
                result = walk(child, chain + [dev["name"]])
                if result:
                    return result
            return None
        for dev in blkinfo:
            result = walk(dev, [])
            if result:
                return result
        # Fallback: use findmnt to get device, then lsblk to get ancestry
        try:
            dev_path = subprocess.check_output(["findmnt", "-nno", "SOURCE", mount], text=True).strip()
            # Remove /dev/ if present
            dev_name = os.path.basename(dev_path)
            # Recursively search for dev_name in blkinfo
            def search_dev(devs, chain):
                for dev in devs:
                    if dev.get("name") == dev_name:
                        return (chain + [dev["name"]], dev)
                    if "children" in dev:
                        result = search_dev(dev["children"], chain + [dev["name"]])
                        if result:
                            return result
                return None
            result = search_dev(blkinfo, [])
            if result:
                return result
            # If still not found, just return the device name
            return ([dev_name], {"name": dev_name, "fstype": "unknown", "type": "unknown"})
        except Exception as e:
            return ([], None)

    for mount in critical_mounts:
        if mount not in mount_data:
            # Only show as 'Not mounted' if it is a separate mount point in fstab or /proc/mounts
            # Otherwise, skip it entirely
            if mount == '/var':
                try:
                    with open('/etc/fstab', 'r') as fstab:
                        found = any(line.strip() and not line.strip().startswith('#') and any(part == '/var' for part in line.split()) for line in fstab)
                    if not found:
                        continue
                except Exception:
                    continue
            print(f"{mount:<15} : {YELLOW}Not mounted{RESET}")
            continue
        try:
            total, used, free = shutil.disk_usage(mount)
            percent = (used / total) * 100
            color = GREEN
            if percent > 90:
                color = RED
                issue_count += 1
            elif percent > 75:
                color = YELLOW

            # Find device info and origin chain
            chain, dev_entry = find_chain_and_dev_by_mount(mount)
            subvol = ""
            # Try to get subvolume info for btrfs
            try:
                # Try findmnt with SUBVOL support, capture stderr too
                findmnt_out = subprocess.check_output(["findmnt", "-nno", "SOURCE,SUBVOL", mount], text=True, stderr=subprocess.STDOUT).strip()
                if 'unknown column' in findmnt_out or 'findmnt:' in findmnt_out:
                    raise Exception('findmnt SUBVOL not supported')
                parts = findmnt_out.split()
                dev_path = parts[0] if parts else ""
                subvol = parts[1] if len(parts) > 1 else ""
            except Exception:
                # Fallback: get device only
                try:
                    dev_path_raw = subprocess.check_output(["findmnt", "-nno", "SOURCE", mount], text=True).strip()
                    # If output is /dev/xxx[subvol], parse device and subvol
                    import re
                    m = re.match(r"(/dev/\S+)(\[(.+)\])?", dev_path_raw)
                    if m:
                        dev_path = m.group(1)
                        subvol = m.group(3) if m.group(3) else ""
                    else:
                        dev_path = dev_path_raw
                        subvol = ""
                except Exception:
                    dev_path = f"/dev/{dev_entry['name']}" if dev_entry and 'name' in dev_entry else ""
                    subvol = ""
                # Try to get subvol from /etc/fstab if not found
                if not subvol:
                    try:
                        with open('/etc/fstab', 'r') as fstab:
                            for line in fstab:
                                if line.strip() and not line.strip().startswith('#') and mount in line:
                                    opts = line.split()
                                    if len(opts) > 3:
                                        for opt in opts[3].split(','):
                                            if opt.startswith('subvol='):
                                                subvol = opt.split('=',1)[1]
                    except Exception:
                        pass
            # If btrfs, always use the real block device for device/origin
            if dev_entry and (dev_entry.get('fstype', '') == 'btrfs' or (dev_path and dev_path and dev_path.startswith('/dev/') and 'btrfs' in (dev_entry.get('fstype', '') or ''))):
                # Clean trailing ']' from device and origin if present
                device = dev_path.rstrip(']') if dev_path.endswith(']') else dev_path
                dev_name = os.path.basename(device)
                def search_dev(devs, chain):
                    for dev in devs:
                        if dev.get("name") == dev_name:
                            return chain + [dev["name"]]
                        if "children" in dev:
                            result = search_dev(dev["children"], chain + [dev["name"]])
                            if result:
                                return result
                    return None
                origin_chain = search_dev(blkinfo, [])
                origin = '.'.join(origin_chain) if origin_chain else dev_name
                # Remove trailing ']' from origin if present
                origin = origin.rstrip(']') if origin.endswith(']') else origin
                fstype = 'btrfs'
                dtype = dev_entry.get('type', 'unknown') if dev_entry else 'unknown'
            else:
                device = f"/dev/{dev_entry['name']}" if dev_entry and 'name' in dev_entry else ""
                fstype = dev_entry.get('fstype', 'unknown') if dev_entry else 'unknown'
                dtype = dev_entry.get('type', 'unknown') if dev_entry else 'unknown'
                origin = '.'.join(chain) if chain else (dev_entry.get('name', 'unknown') if dev_entry else 'unknown')

            print(f"{mount:<15} : {color}{percent:>6.1f}%{RESET} : {free/(2**30):>7.2f} GB : {fstype:<8} : {dtype:<10} : {device:<22} : {origin:<20} : {subvol}")
        except Exception as e:
            print(f"{mount:<15} : {RED}Error: {e}{RESET}")

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
                cache_out = subprocess.check_output(["du", "-sh", cache_path], text=True).split()[0]
                cache_size_str = cache_out
            except Exception:
                pass

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

    # Custom help output for compact style
    parser.usage = None
    parser.formatter_class = lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=32)
    
    args = parser.parse_args()
    
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

    # enabled = [name for flag, _, name in checks if flag]
    # print(f"[DEBUG] Enabled checks: {enabled}")

    if args.json:
        results = {}
        for selected, func, name in checks:
            if selected:
                # Only check_kernel supports as_dict for now
                if name in ('kernel', 'smart', 'pacnew', 'services', 'orphans', 'stats', 'sensors'):
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
