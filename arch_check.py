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
                out =subprocess.check_output(["smartctl", "-H", dev], text=True, stderr=subprocess.STDOUT)
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
import re

# Color control
def get_colors(enable=True):
    if enable:
        return {
            'BLUE': '\033[34m',
            'CYAN': '\033[36m',
            'RED': '\033[31m',
            'GREEN': '\033[32m',
            'YELLOW': '\033[33m',
            'BOLD': '\033[1m',
            'RESET': '\033[0m',
        }
    else:
        return {k: '' for k in ['BLUE','CYAN','RED','GREEN','YELLOW','BOLD','RESET']}




# --- Configuration & Colors ---
# These will be set in main() based on --color/--no-color
BLUE = CYAN = RED = GREEN = YELLOW = BOLD = RESET = ''

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
f"",
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

    def resolve_via_findmnt(mount):
        """Fallback for mounts lsblk's tree doesn't surface directly
        (e.g. multiple btrfs subvolumes sharing one LUKS/device-mapper
        node). Returns a synthetic dev_entry dict, or None."""
        try:
            source = subprocess.check_output(
                ["findmnt", "-no", "SOURCE", mount], text=True
            ).strip()
            fstype_out = subprocess.check_output(
                ["findmnt", "-no", "FSTYPE", mount], text=True
            ).strip()
            name = source.replace("/dev/", "")
            # Walk up to the parent device, same technique as get_device_origin
            try:
                pkname = subprocess.check_output(
                    ["lsblk", "-no", "PKNAME", source], text=True
                ).strip().split("\n")[-1]
            except Exception:
                pkname = None
            synthetic = {"name": name, "fstype": fstype_out}
            chain = [{"name": pkname}, synthetic] if pkname else [synthetic]
            return synthetic, chain
        except Exception as e:
            logging.debug(f"findmnt fallback failed for {mount}: {e}")
            return None, None

    for mount in all_mounts:
        # Find device info first to check fstype
        dev_entry, chain = find_mount_and_chain(blkinfo, mount)
        if dev_entry is None:
            # lsblk's per-device mountpoints array can miss mounts when
            # multiple mountpoints (e.g. btrfs subvolumes) share a single
            # device-mapper node, which is common with LUKS. Fall back to
            # findmnt, which is mount-table-aware rather than block-device-
            # tree-aware.
            dev_entry, chain = resolve_via_findmnt(mount)
        fstype = dev_entry.get("fstype", "") if dev_entry else ""
        if fstype in skip_fstypes or mount in skip_mounts:
            continue

        entry = {"mount": mount}
        try:
            # Btrfs-specific reporting (optional, but will be overwritten by df below)
            if fstype == "btrfs":
                try:
                    import re
                    # Prefer the more-structured 'btrfs filesystem df -b' output (bytes)
                    btrfs_df = subprocess.check_output(["btrfs", "filesystem", "df", "-b", mount], text=True)
                    total_bytes = 0
                    used_bytes = 0
                    for line in btrfs_df.splitlines():
                        m_total = re.search(r'total=(\d+)', line)
                        m_used = re.search(r'used=(\d+)', line)
                        if m_total:
                            total_bytes += int(m_total.group(1))
                        if m_used:
                            used_bytes += int(m_used.group(1))

                    if total_bytes > 0:
                        percent = (used_bytes / total_bytes) * 100
                        entry["usage_percent"] = round(percent, 1)
                        entry["free_gb"] = round((total_bytes - used_bytes)/(2**30), 2)
                        entry["btrfs_device_size_bytes"] = int(total_bytes)
                        entry["btrfs_used_bytes"] = int(used_bytes)
                    else:
                        # Fallback to older 'btrfs filesystem usage -b' parsing if df didn't report totals
                        btrfs_out = subprocess.check_output(["btrfs", "filesystem", "usage", "-b", mount], text=True)
                        total_bytes = used_bytes = free_bytes = None
                        for line in btrfs_out.splitlines():
                            if "Device size:" in line:
                                try:
                                    total_bytes = int(line.split(":",1)[1].strip().split()[0])
                                except Exception:
                                    pass
                            elif "Used:" in line and "Device size:" not in line:
                                try:
                                    used_bytes = int(line.split(":",1)[1].strip().split()[0])
                                except Exception:
                                    pass
                            elif "Free (estimated):" in line:
                                try:
                                    free_bytes = int(line.split(":",1)[1].strip().split()[0])
                                except Exception:
                                    pass
                        if total_bytes and used_bytes is not None:
                            percent = (used_bytes / total_bytes) * 100
                            entry["usage_percent"] = round(percent, 1)
                            entry["free_gb"] = round((total_bytes - used_bytes)/(2**30), 2)
                            entry["btrfs_device_size_bytes"] = int(total_bytes)
                            entry["btrfs_used_bytes"] = int(used_bytes)
                            if free_bytes is not None:
                                entry["btrfs_free_estimated_bytes"] = int(free_bytes)
                        elif total_bytes and free_bytes is not None:
                            percent = (1 - (free_bytes / total_bytes)) * 100
                            entry["usage_percent"] = round(percent, 1)
                            entry["free_gb"] = round(free_bytes/(2**30), 2)
                            entry["btrfs_device_size_bytes"] = int(total_bytes)
                            entry["btrfs_free_estimated_bytes"] = int(free_bytes)
                        else:
                            entry["usage_percent"] = "?"
                            entry["free_gb"] = "?"
                except Exception as e:
                    entry["usage_percent"] = "?"
                    entry["free_gb"] = "?"
                    entry["btrfs_error"] = str(e)
                    entry["btrfs_device_size_bytes"] = None
                    entry["btrfs_used_bytes"] = None
                    entry["btrfs_free_estimated_bytes"] = None

                # Defer detailed subvolume parsing until after we collect fstab info
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
            # For btrfs, if lsblk didn't provide a useful type, show the btrfs-progs version
            if fstype == "btrfs" and (not entry.get("type") or entry.get("type") == "?"):
                try:
                    bv = subprocess.check_output(["btrfs", "--version"], text=True).splitlines()[0]
                    # Typical output: 'btrfs-progs v5.15.1' -> show version number
                    parts = bv.split()
                    entry["type"] = parts[1] if len(parts) > 1 else bv
                except Exception:
                    entry["type"] = "btrfs"
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
            # If this is a btrfs mount, try to gather richer subvolume metadata and prefer fstab's subvol if present
            if fstype == 'btrfs':
                entry.setdefault('subvol_id', None)
                entry.setdefault('subvol_path', None)
                entry.setdefault('subvol_uuid', None)
                entry.setdefault('subvol_name', None)
                try:
                    subvol_show = subprocess.check_output(["btrfs", "subvolume", "show", mount], text=True, stderr=subprocess.DEVNULL)
                    for line in subvol_show.splitlines():
                        l = line.strip()
                        if l.startswith('Subvolume ID:'):
                            try:
                                entry['subvol_id'] = int(l.split(':',1)[1].strip())
                            except Exception:
                                pass
                        elif l.startswith('Path:'):
                            entry['subvol_path'] = l.split(':',1)[1].strip()
                        elif l.startswith('Name:'):
                            entry['subvol_name'] = l.split(':',1)[1].strip()
                        elif l.startswith('UUID:') or l.startswith('Received UUID:'):
                            # Prefer UUID line if present
                            entry['subvol_uuid'] = l.split(':',1)[1].strip()
                except Exception:
                    # leave the subvol_* fields as None
                    pass

                # Decide what to show in the human-friendly Subvol column: prefer fstab subvol, then Name, then Path
                display_subvol = entry.get('subvol') or entry.get('subvol_name') or entry.get('subvol_path') or ''
                # Normalize display: strip leading/trailing slashes
                display_subvol = display_subvol.strip('/') if display_subvol else display_subvol
                if display_subvol and not display_subvol.startswith('@'):
                    # keep as-is; many setups name subvolumes with @ prefixes, but don't enforce
                    pass
                # Attach final normalized display value
                entry['subvol'] = display_subvol
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
            logging.debug(f"Error processing mount '{mount}': {e}")
        results.append(entry)

    if as_dict:
        return {"mounts": results, "status": "ok", "issues": sum(1 for e in results if e.get("status") == "critical")}
    # Only show the compact Btrfs used/total column when we actually have btrfs mounts
    show_btrfs = any((e.get('fstype') == 'btrfs') or (e.get('btrfs_device_size_bytes') is not None) for e in results)
    print_header("Disk Usage & Origins")
    if show_btrfs:
        print(f"{BOLD}{'Mount':<15} : {'Usage':<8} : {'Free':<10} : {'FS':<8} : {'Type':<10} : {'Device':<22} : {'Origin':<36} : {'Btrfs':<18} : {'Subvol'}{RESET}")
        print("─" * 160)
    else:
        print(f"{BOLD}{'Mount':<15} : {'Usage':<8} : {'Free':<10} : {'FS':<8} : {'Type':<10} : {'Device':<22} : {'Origin':<36}{RESET}")
        print("─" * 140)

    for entry in results:
        color = GREEN if entry["status"] == "ok" else (YELLOW if entry["status"] == "warn" else RED)
        def safe(val, default="?"):
            return str(val) if val is not None else default
        # Prepare compact btrfs used/total display when available (only if show_btrfs)
        btrfs_col = ""
        if show_btrfs:
            try:
                if entry.get("btrfs_used_bytes") and entry.get("btrfs_device_size_bytes"):
                    used_gb = float(entry.get("btrfs_used_bytes") or 0) / (2**30)
                    total_gb = float(entry.get("btrfs_device_size_bytes") or 0) / (2**30)
                    btrfs_col = f"{used_gb:.2f}/{total_gb:.2f} GiB"
            except Exception:
                btrfs_col = ""

        if show_btrfs:
            print(f"{safe(entry['mount']):<15} : {color}{safe(entry.get('usage_percent')):>6}%{RESET} : {safe(entry.get('free_gb')):>7} GB : {safe(entry.get('fstype')):<8} : {safe(entry.get('type')):<10} : {safe(entry.get('device')):<22} : {safe(entry.get('origin')):<36} : {btrfs_col:<18} : {safe(entry.get('subvol'),'')}")
        else:
            print(f"{safe(entry['mount']):<15} : {color}{safe(entry.get('usage_percent')):>6}%{RESET} : {safe(entry.get('free_gb')):>7} GB : {safe(entry.get('fstype')):<8} : {safe(entry.get('type')):<10} : {safe(entry.get('device')):<22} : {safe(entry.get('origin')):<36}")

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
    print_header("Config Files (.pacnew/.pacsave)")
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
    global issue_count
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
            orphan_count = len(out.splitlines())
            issue_count += orphan_count
            print(f"{YELLOW}Orphans: {out.replace(chr(10), ' ')}{RESET}")
            print(f'  {RED}Caution: Review the list before removing anything!{RESET}')
            print(f'  {YELLOW}Tip({RED}potentially dangerous{RESET}): Run "pacman -Rns $(pacman -Qdtq)" to remove orphans, i.e. with pactree:{RESET}')
            print(f'  for p in {out.replace(chr(10), " ")}; do pactree -r $p; echo {30*"="} ; done')
        else:
            print(f"{GREEN}No orphans.{RESET}")
    except Exception as e:
        if as_dict:
            return {"orphans": [], "count": 0, "status": "ok", "issues": 0, "error": str(e)}
        print(f"{GREEN}No orphans.{RESET}")

def check_stats(as_dict=False):
    try:
        import pwd
        
        def get_count(flags: str) -> int:
            try:
                out = subprocess.check_output(["pacman"] + flags.split(), text=True, stderr=subprocess.DEVNULL)
                return len(out.strip().splitlines())
            except subprocess.CalledProcessError:
                return 0

        def _dir_size(path: str) -> int:
            """Recursively calculate directory size in bytes. Returns 0 on any error."""
            if not os.path.exists(path) or not os.path.isdir(path):
                return 0
            total = 0
            try:
                for entry in os.scandir(path):
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            total += _dir_size(entry.path)
                    except (OSError, PermissionError):
                        continue
            except (OSError, PermissionError):
                pass
            return total

        def _pkg_archive_size(path: str) -> int:
            """Recursively calculate size of .pkg.tar.zst files only. Returns 0 on any error."""
            if not os.path.exists(path) or not os.path.isdir(path):
                return 0
            total = 0
            try:
                for entry in os.scandir(path):
                    try:
                        if entry.is_file(follow_symlinks=False) and entry.name.endswith('.pkg.tar.zst'):
                            total += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            total += _pkg_archive_size(entry.path)
                    except (OSError, PermissionError):
                        continue
            except (OSError, PermissionError):
                pass
            return total

        def _fmt_size(bytes_size: int) -> str:
            """Format bytes as human-readable string. Returns '-' if 0 or invalid."""
            if bytes_size <= 0:
                return "-"
            if bytes_size >= 1_000_000_000:
                return f"{bytes_size / 1_000_000_000:.1f}G"
            elif bytes_size >= 1_000_000:
                return f"{int(bytes_size / 1_000_000)}M"
            elif bytes_size >= 1_000:
                return f"{int(bytes_size / 1_000)}K"
            else:
                return f"{bytes_size}B"

        total = get_count("-Q")
        explicit = get_count("-Qe")
        deps = get_count("-Qd")
        foreign = get_count("-Qm")
        native = total - foreign

        # Resolve home directory (handle sudo)
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            try:
                home = pwd.getpwnam(sudo_user).pw_dir
            except KeyError:
                home = os.path.expanduser('~')
        else:
            home = os.path.expanduser('~')

        # Calculate cache sizes
        pacman_cache = "/var/cache/pacman/pkg"
        yay_cache = os.path.join(home, '.cache', 'yay')
        paru_cache = os.path.join(home, '.cache', 'paru', 'clone')

        pacman_cache_bytes = _dir_size(pacman_cache) if os.path.exists(pacman_cache) else 0
        yay_cache_bytes = _dir_size(yay_cache) if os.path.exists(yay_cache) else 0
        yay_cache_pkg_bytes = _pkg_archive_size(yay_cache) if os.path.exists(yay_cache) else 0
        paru_cache_bytes = _dir_size(paru_cache) if os.path.exists(paru_cache) else 0
        paru_cache_pkg_bytes = _pkg_archive_size(paru_cache) if os.path.exists(paru_cache) else 0

        # Format sizes for display
        pacman_cache_str = _fmt_size(pacman_cache_bytes)
        yay_cache_str = _fmt_size(yay_cache_bytes)
        yay_cache_pkg_str = _fmt_size(yay_cache_pkg_bytes)
        paru_cache_str = _fmt_size(paru_cache_bytes)
        paru_cache_pkg_str = _fmt_size(paru_cache_pkg_bytes)

        if as_dict:
            return {
                "total": total,
                "native": native,
                "foreign": foreign,
                "explicit": explicit,
                "dependencies": deps,
                "pacman_cache_bytes": pacman_cache_bytes,
                "yay_cache_bytes": yay_cache_bytes,
                "yay_cache_pkg_bytes": yay_cache_pkg_bytes,
                "paru_cache_bytes": paru_cache_bytes,
                "paru_cache_pkg_bytes": paru_cache_pkg_bytes,
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

        # Display cache sizes
        if pacman_cache_str != "-":
            print(f"{'Pacman Cache':<18} : {YELLOW}{pacman_cache_str}{RESET}")
        else:
            print(f"{'Pacman Cache':<18} : {CYAN}not found{RESET}")
        
        # yay cache
        if yay_cache_str != "-":
            if yay_cache_pkg_str != "-":
                print(f"{'AUR Cache (yay)':<18} : {YELLOW}{yay_cache_str}{RESET} total, {yay_cache_pkg_str} built pkgs")
            else:
                print(f"{'AUR Cache (yay)':<18} : {YELLOW}{yay_cache_str}{RESET} total")
        else:
            print(f"{'AUR Cache (yay)':<18} : {CYAN}not found{RESET}")
        
        # paru cache
        if paru_cache_str != "-":
            if paru_cache_pkg_str != "-":
                print(f"{'AUR Cache (paru)':<18} : {YELLOW}{paru_cache_str}{RESET} total, {paru_cache_pkg_str} built pkgs")
            else:
                print(f"{'AUR Cache (paru)':<18} : {YELLOW}{paru_cache_str}{RESET} total")
        else:
            print(f"{'AUR Cache (paru)':<18} : {CYAN}not found{RESET}")

        # Show cleanup tips if built packages > 100MB
        cleanup_tips = []
        if yay_cache_pkg_bytes > 100_000_000:
            yay_recoverable = _fmt_size(yay_cache_pkg_bytes)
            cleanup_tips.append(f"  yay: run 'yay -Sc' to recover ~{yay_recoverable}\n        (yay -Sc keeps latest version per package)")
        
        if paru_cache_pkg_bytes > 100_000_000:
            paru_recoverable = _fmt_size(paru_cache_pkg_bytes)
            cleanup_tips.append(f"  paru: run 'paru -Sc' to recover ~{paru_recoverable}\n        (paru -Sc keeps latest version per package)")
        
        if cleanup_tips:
            print(f"\n{CYAN}Cleanup tips:{RESET}")
            for tip in cleanup_tips:
                print(tip)

    except Exception as e:
        if as_dict:
            return {"status": "error", "issues": 0, "error": str(e)}
        print(f"{RED}Could not retrieve stats: {e}{RESET}")

def check_aur_integrity(as_dict=False):
    """Check integrity of AUR (foreign) packages using pacman -Qk and -Qkk.
    Flag packages with missing files (>0) or MODIFIED lines. Skip noisy paths."""
    global issue_count
    import re
    import subprocess
    results = []
    summary = {"status": "ok", "issues": 0, "packages_checked": 0, "packages_with_issues": []}

    try:
        # Get foreign packages
        out = subprocess.check_output(["pacman", "-Qmq"], text=True).strip()
        if not out:
            if as_dict:
                summary["packages_checked"] = 0
                return summary
            print_header("AUR Package Integrity")
            print(f"{GREEN}No AUR (foreign) packages found.{RESET}")
            return

        foreign_pkgs = [pkg.strip() for pkg in out.splitlines() if pkg.strip()]
        summary["packages_checked"] = len(foreign_pkgs)

        # Paths to skip
        skip_patterns = [r'\.pyc$', r'\.pyo$', r'\.log$', r'\.lock$', r'/var/', r'/run/']

        for pkg in foreign_pkgs:
            pkg_result = {"name": pkg, "missing_count": 0, "modified_files": []}
            issue_found = False

            # Try pacman -Qk (newer pacman)
            try:
                qk_out = subprocess.check_output(["pacman", "-Qk", pkg], text=True, stderr=subprocess.STDOUT)
                # Parse missing count: "X missing" or "X files missing"
                for line in qk_out.splitlines():
                    match = re.search(r'(\d+)\s+missing', line, re.IGNORECASE)
                    if match:
                        count = int(match.group(1))
                        if count > 0:
                            pkg_result["missing_count"] = count
                            issue_found = True
            except subprocess.CalledProcessError:
                pass

            # Try pacman -Qkk (stricter, older pacman)
            try:
                qkk_out = subprocess.check_output(["pacman", "-Qkk", pkg], text=True, stderr=subprocess.STDOUT)
                # Look for MODIFIED lines
                for line in qkk_out.splitlines():
                    if "MODIFIED" in line.upper():
                        # Extract file path (skip noisy paths)
                        parts = line.split()
                        if parts:
                            filepath = parts[-1] if len(parts) > 1 else line.strip()
                            # Check if we should skip this path
                            skip = False
                            for pattern in skip_patterns:
                                if re.search(pattern, filepath):
                                    skip = True
                                    break
                            if not skip:
                                pkg_result["modified_files"].append(filepath)
                                issue_found = True
            except subprocess.CalledProcessError:
                pass

            if issue_found:
                summary["issues"] += 1
                summary["status"] = "attention"
                results.append(pkg_result)
                issue_count += 1

        if as_dict:
            summary["packages_with_issues"] = results
            return summary

        print_header("AUR Package Integrity")
        if not results:
            print(f"{GREEN}All {len(foreign_pkgs)} AUR packages intact.{RESET}")
        else:
            print(f"{YELLOW}{BOLD}Warning: {len(results)} package(s) with integrity issues:{RESET}")
            for pkg_result in results:
                print(f"\n{CYAN}{pkg_result['name']}{RESET}")
                if pkg_result["missing_count"] > 0:
                    print(f"  {RED}Missing files: {pkg_result['missing_count']}{RESET}")
                if pkg_result["modified_files"]:
                    print(f"  {YELLOW}Modified files: {len(pkg_result['modified_files'])}{RESET}")
                    for f in pkg_result["modified_files"][:5]:
                        print(f"    - {f}")
                    if len(pkg_result["modified_files"]) > 5:
                        print(f"    ... and {len(pkg_result['modified_files']) - 5} more")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "no_pacman"
            summary["error"] = "pacman command not found"
            return summary
        print(f"{YELLOW}pacman command not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}AUR integrity check failed: {e}{RESET}")

def check_aur_paths(as_dict=False):
    """Check for non-standard file paths in AUR (foreign) packages.
    Flag files not under /usr, /etc, /var, /opt, /lib, /lib32, /bin, /sbin, /run, /share, /usr/local."""
    global issue_count
    import subprocess
    results = []
    summary = {"status": "ok", "issues": 0, "packages_checked": 0, "unusual_paths": []}

    try:
        # Get foreign packages
        out = subprocess.check_output(["pacman", "-Qmq"], text=True).strip()
        if not out:
            if as_dict:
                summary["packages_checked"] = 0
                return summary
            print_header("AUR Package Paths")
            print(f"{GREEN}No AUR (foreign) packages found.{RESET}")
            return

        foreign_pkgs = [pkg.strip() for pkg in out.splitlines() if pkg.strip()]
        summary["packages_checked"] = len(foreign_pkgs)

        # Allowed path prefixes
        allowed_prefixes = ('/usr', '/etc', '/var', '/opt', '/lib', '/lib32', '/bin', '/sbin', '/run', '/share', '/usr/local')

        for pkg in foreign_pkgs:
            try:
                out = subprocess.check_output(["pacman", "-Ql", pkg], text=True)
                for line in out.splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        filepath = parts[1]
                        # Skip directory entries
                        if filepath.endswith('/'):
                            continue
                        # Check if path is outside allowed prefixes
                        if not filepath.startswith(allowed_prefixes):
                            results.append({"package": pkg, "path": filepath})
                            summary["issues"] += 1
                            summary["status"] = "attention"
            except subprocess.CalledProcessError:
                pass

        if as_dict:
            summary["unusual_paths"] = results
            return summary

        print_header("AUR Package Paths")
        if not results:
            print(f"{GREEN}All {len(foreign_pkgs)} AUR packages use standard paths.{RESET}")
        else:
            print(f"{YELLOW}{BOLD}Warning: {len(results)} unusual path(s) found:{RESET}")
            for item in results:
                print(f"  {CYAN}{item['package']}{RESET}: {RED}{item['path']}{RESET}")
            if summary["issues"] > 0:
                issue_count += 1
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "no_pacman"
            summary["error"] = "pacman command not found"
            return summary
        print(f"{YELLOW}pacman command not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}AUR paths check failed: {e}{RESET}")

def check_aur_suid(as_dict=False):
    """Check for setuid/setgid files in AUR (foreign) packages.
    Whitelist known safe binaries (chrome-sandbox, pmount, pumount, v4l-conf)."""
    global issue_count
    import os
    import stat
    import subprocess
    whitelisted = {'chrome-sandbox', 'pmount', 'pumount', 'v4l-conf'}
    summary = {"status": "ok", "issues": 0, "whitelisted": [], "unexpected": []}

    try:
        # Get foreign packages
        out = subprocess.check_output(["pacman", "-Qmq"], text=True).strip()
        if not out:
            if as_dict:
                summary["packages_checked"] = 0
                return summary
            print_header("AUR SetUID/SetGID Check")
            print(f"{GREEN}No AUR (foreign) packages found.{RESET}")
            return

        foreign_pkgs = [pkg.strip() for pkg in out.splitlines() if pkg.strip()]
        summary["packages_checked"] = len(foreign_pkgs)

        for pkg in foreign_pkgs:
            try:
                out = subprocess.check_output(["pacman", "-Ql", pkg], text=True)
                for line in out.splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        filepath = parts[1]
                        # Skip directory entries
                        if filepath.endswith('/'):
                            continue
                        try:
                            st = os.stat(filepath)
                            mode = st.st_mode
                            is_suid = bool(mode & stat.S_ISUID)
                            is_sgid = bool(mode & stat.S_ISGID)
                            if is_suid or is_sgid:
                                basename = os.path.basename(filepath)
                                entry = {"path": filepath, "mode": []}
                                if is_suid:
                                    entry["mode"].append("setuid")
                                if is_sgid:
                                    entry["mode"].append("setgid")

                                if basename in whitelisted:
                                    summary["whitelisted"].append(entry)
                                else:
                                    summary["unexpected"].append(entry)
                                    summary["issues"] += 1
                                    summary["status"] = "attention"
                                    issue_count += 1
                        except (OSError, FileNotFoundError):
                            pass
            except subprocess.CalledProcessError:
                pass

        if as_dict:
            return summary

        print_header("AUR SetUID/SetGID Check")

        # Show whitelisted (in green)
        if summary["whitelisted"]:
            print(f"\n{GREEN}{BOLD}Whitelisted (expected):{RESET}")
            for item in summary["whitelisted"]:
                mode_str = "|".join(item["mode"])
                print(f"  {GREEN}{item['path']}{RESET} ({mode_str})")

        # Show unexpected (in red)
        if summary["unexpected"]:
            print(f"\n{RED}{BOLD}Unexpected setuid/setgid files:{RESET}")
            for item in summary["unexpected"]:
                mode_str = "|".join(item["mode"])
                print(f"  {RED}{item['path']}{RESET} ({mode_str})")
        elif not summary["whitelisted"]:
            print(f"{GREEN}No setuid/setgid files found in AUR packages.{RESET}")
        else:
            print(f"\n{GREEN}All setuid/setgid files are whitelisted.{RESET}")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "no_pacman"
            summary["error"] = "pacman command not found"
            return summary
        print(f"{YELLOW}pacman command not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}AUR setuid check failed: {e}{RESET}")

# --- PKGBUILD exclusion filters (safe patterns) ---
# These are applied BEFORE pattern matching as a preprocessing step
PKGBUILD_EXCLUSIONS = [
    {
        "pattern": re.compile(r'python\s+-m\s+', re.IGNORECASE),
        "reason": "python module execution, common in build systems"
    },
    {
        "pattern": re.compile(r'python\s+-c\s+[\'"]import\s+site', re.IGNORECASE),
        "reason": "standard idiom to locate site-packages install path"
    },
    {
        "pattern": re.compile(r'python\s+-c\s+[\'"]import\s+sys', re.IGNORECASE),
        "reason": "used to check Python version or sys.path at build time"
    },
    {
        "pattern": re.compile(r'python\s+-c\s+[\'"]from\s+distutils', re.IGNORECASE),
        "reason": "legacy distutils path/version lookup, common in older PKGBUILDs"
    },
    {
        "pattern": re.compile(r'pip\s+install\s+--no-deps', re.IGNORECASE),
        "reason": "used in -bin packages to install pre-built wheel without remote dependencies"
    },
]

def check_aur_pkgbuild(as_dict=False):
    """Scan PKGBUILD files from local cache for suspicious patterns.
    Does NOT clone from git - reads from yay/paru cache or PKGBUILD_CACHE_DIR."""
    global issue_count
    import re
    import os
    import subprocess
    import json

    # Patterns to match (label: regex)
    patterns = {
        "curl_pipe_shell": r'curl\b.+\|\s*(ba)?sh\b',
        "wget_pipe_shell": r'wget\b.+\|\s*(ba)?sh\b',
        "eval_subshell": r'^\s*eval\s+\$\(',
        "base64_decode_pipe": r'base64\s+(--decode|-d)\s*\|',
        "python_inline_exec": r'(?<![a-z]-)python[23]?\s+-c\s+[\'"]',
        "bash_dev_tcp": r'/dev/tcp/',
        "netcat_exec": r'(nc|ncat|netcat)\s+.*-e\s',
        "rm_rf_system": r'rm\s+-rf?\s+/(?!tmp|var/tmp)',
        "skip_integrity": r'(SKIPCHECKSUMS|skipinteg)\s*=',
    }

    summary = {
        "status": "ok",
        "issues": 0,
        "scanned": 0,
        "packages_checked": 0,
        "not_cached": [],
        "flagged": []
    }

    def find_pkgbuild(pkgname):
        """Find PKGBUILD in cache directories. Returns (path, source) or (None, None)."""
        # Get user home - handle sudo by checking SUDO_USER env var
        import pwd
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            try:
                user_home = pwd.getpwnam(sudo_user).pw_dir
            except KeyError:
                user_home = os.path.expanduser("~")
        else:
            user_home = os.path.expanduser("~")

        # Priority 1: yay cache
        yay_path = os.path.join(user_home, f".cache/yay/{pkgname}/PKGBUILD")
        if os.path.isfile(yay_path):
            return yay_path, "yay"

        # Priority 2: paru cache
        paru_path = os.path.join(user_home, f".cache/paru/clone/{pkgname}/PKGBUILD")
        if os.path.isfile(paru_path):
            return paru_path, "paru"

        # Priority 3: custom cache dir from env var
        custom_base = os.environ.get('PKGBUILD_CACHE_DIR')
        if custom_base:
            custom_path = os.path.join(custom_base, pkgname, "PKGBUILD")
            if os.path.isfile(custom_path):
                return custom_path, "custom"

        return None, None

    def preprocess_content(content):
        """Remove comments, checksum lines, and depends lines before matching."""
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            # Skip comment lines
            if stripped.startswith('#'):
                continue
            # Skip checksum array lines
            if re.match(r'^(sha256sums|sha512sums|md5sums|sha1sums)\s*=', line):
                continue
            # Skip depends/makedepends lines
            if re.match(r'^(depends|makedepends|optdepends|checkdepends|source)\s*=', line):
                continue
            lines.append(line)
        return '\n'.join(lines)

    try:
        # Get foreign packages
        out = subprocess.check_output(["pacman", "-Qmq"], text=True).strip()
        if not out:
            if as_dict:
                summary["packages_checked"] = 0
                return summary
            print_header("AUR PKGBUILD Security Scan")
            print(f"{GREEN}No AUR (foreign) packages found.{RESET}")
            return

        foreign_pkgs = [pkg.strip() for pkg in out.splitlines() if pkg.strip()]
        summary["packages_checked"] = len(foreign_pkgs)

        if not as_dict:
            print_header("AUR PKGBUILD Security Scan")

        for pkg in foreign_pkgs:
            pkgbuild_path, source = find_pkgbuild(pkg)

            if not pkgbuild_path:
                summary["not_cached"].append(pkg)
                continue

            summary["scanned"] += 1

            try:
                with open(pkgbuild_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Preprocess content
                orig_lines = content.splitlines()
                
                # Apply exclusion filters first, BEFORE pattern matching
                filtered_lines = []
                excluded_indices = set()
                whitelisted_lines = []
                
                for i, orig_line in enumerate(orig_lines):
                    stripped = orig_line.strip()
                    
                    # Skip comment lines
                    if stripped.startswith('#'):
                        filtered_lines.append(None)
                        excluded_indices.add(i)
                        continue
                    
                    # Skip checksum array lines
                    if re.match(r'^(sha256sums|sha512sums|md5sums|sha1sums|b2sums)\s*=', orig_line):
                        filtered_lines.append(None)
                        excluded_indices.add(i)
                        continue
                    
                    # Skip dependency declarations
                    if re.match(r'^(depends|makedepends|optdepends|checkdepends|source)\s*=', orig_line):
                        filtered_lines.append(None)
                        excluded_indices.add(i)
                        continue
                    
                    # Check if line matches ANY exclusion filter
                    excluded = False
                    excluded_reason = None
                    for exclusion in PKGBUILD_EXCLUSIONS:
                        if exclusion["pattern"].search(orig_line):
                            excluded = True
                            excluded_reason = exclusion["reason"]
                            # Track as whitelisted for all patterns (we'll add them later)
                            for label in patterns.keys():
                                if re.search(patterns[label], orig_line, re.MULTILINE):
                                    whitelisted_lines.append({
                                        "pattern": label,
                                        "line": i + 1,
                                        "content": orig_line.strip(),
                                        "reason": excluded_reason
                                    })
                            break
                    
                    if excluded:
                        filtered_lines.append(None)
                        excluded_indices.add(i)
                    else:
                        filtered_lines.append(orig_line)
                
                # Now apply pattern matching only to non-excluded lines
                flagged_patterns = []
                matches = []
                
                for label, pattern in patterns.items():
                    flags = re.MULTILINE
                    for i, line in enumerate(filtered_lines):
                        # Skip excluded lines
                        if line is None:
                            continue
                        
                        if re.search(pattern, line, flags):
                            # Line is truly suspicious, flag it
                            flagged_patterns.append(label)
                            matches.append({
                                "pattern": label,
                                "line": i + 1,
                                "content": line.strip()
                            })

                if matches or whitelisted_lines:
                    if matches:
                        summary["issues"] += 1
                        summary["status"] = "attention"
                        issue_count += 1
                    flagged_entry = {
                        "package": pkg,
                        "source": source,
                        "source_path": pkgbuild_path,
                        "patterns_matched": flagged_patterns,
                        "matches": matches,
                        "whitelisted_lines": whitelisted_lines
                    }
                    summary["flagged"].append(flagged_entry)

            except Exception as e:
                if as_dict:
                    if "errors" not in summary:
                        summary["errors"] = []
                    summary["errors"].append({"package": pkg, "error": str(e)})

        # Human output (only if not returning dict)
        if not as_dict:
            if summary["not_cached"] or summary["flagged"]:
                if summary["not_cached"]:
                    print(f"\n{YELLOW}{BOLD}No local PKGBUILD found — manual review recommended:{RESET}")
                    for pkg in summary["not_cached"]:
                        print(f"  {YELLOW}{pkg}{RESET}")

                if summary["flagged"]:
                    print(f"\n{RED}{BOLD}Suspicious patterns detected:{RESET}")
                    for entry in summary["flagged"]:
                        print(f"\n{CYAN}{entry['package']}{RESET} (from {entry['source']} cache)")
                        if entry["patterns_matched"]:
                            print(f"  Patterns: {', '.join(entry['patterns_matched'])}")
                        for m in entry["matches"]:
                            print(f"  Line {m['line']}: {RED}{m['content']}{RESET}")
                        # Show whitelisted lines if present
                        if entry["whitelisted_lines"]:
                            print(f"  {CYAN}Excluded (known safe patterns):{RESET}")
                            for w in entry["whitelisted_lines"]:
                                print(f"    Line {w['line']}: {w['content']}")
                                print(f"      {CYAN}→ {w['reason']}{RESET}")
            else:
                print(f"{GREEN}No suspicious patterns found.{RESET}")

        if as_dict:
            # Remove source_path from flagged for cleaner output
            for entry in summary["flagged"]:
                entry.pop("source_path", None)
            return summary
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "no_pacman"
            summary["error"] = "pacman command not found"
            return summary
        print(f"{YELLOW}pacman command not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}AUR PKGBUILD scan failed: {e}{RESET}")

def check_timedatectl(as_dict=False):
    """Check systemd time/date synchronization status."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "timezone": None, "ntp_service": None, "synchronized": None, "current_time": None}

    try:
        out = subprocess.check_output(["timedatectl", "show", "--no-pager"], text=True)
        props = {}
        for line in out.splitlines():
            if '=' in line:
                key, val = line.split('=', 1)
                props[key] = val

        # Parse values from timedatectl show key=value output
        timezone = props.get('Timezone', None)
        ntp_service = props.get('NTPService', None)
        synchronized = props.get('NTPSynchronized', 'no')
        # TimeUSec is in microseconds since epoch
        time_usec = props.get('TimeUSec', '0')
        
        # Fallback to timedatectl status if machine-readable values are missing
        local_time = None
        if timezone is None or ntp_service is None or time_usec == '0':
            try:
                status_out = subprocess.check_output(["timedatectl", "status", "--no-pager"], text=True)
                for line in status_out.splitlines():
                    line = line.strip()
                    if ':' not in line:
                        continue
                    key, _, val = line.partition(':')
                    key = key.strip().lower()
                    val = val.strip()
                    if key == 'local time' and local_time is None:
                        local_time = val
                    elif key == 'ntp service' and ntp_service is None:
                        ntp_service = val
                    elif key == 'time zone' and timezone is None:
                        timezone = val.split('(')[0].strip()
            except:
                pass
        
        # Ensure defaults for missing values
        if timezone is None:
            timezone = 'unknown'
        if ntp_service is None:
            ntp_service = 'unknown'
        
        # Parse current time from TimeUSec if available, fallback to local_time from status
        current_time = 'unknown'
        try:
            from datetime import datetime
            usec = int(time_usec) if time_usec.isdigit() else 0
            if usec > 0:
                current_time = datetime.fromtimestamp(usec / 1_000_000).strftime('%Y-%m-%d %H:%M:%S')
            elif local_time is not None:
                current_time = local_time
        except (ValueError, OSError):
            if local_time is not None:
                current_time = local_time

        summary["timezone"] = timezone
        summary["ntp_service"] = ntp_service
        summary["synchronized"] = synchronized
        summary["current_time"] = current_time

        if as_dict:
            if synchronized != "yes":
                summary["status"] = "attention"
                summary["issues"] = 1
            return summary

        print_header("Time & Date (timedatectl)")
        print(f"{BOLD}Timezone:{RESET} {timezone}")
        print(f"{BOLD}NTP Service:{RESET} {ntp_service}")
        print(f"{BOLD}Synchronized:{RESET} ", end="")
        if synchronized == "yes":
            print(f"{GREEN}yes{RESET}")
        else:
            print(f"{RED}no{RESET}")
            issue_count += 1
            summary["status"] = "attention"
            summary["issues"] = 1

        print(f"{BOLD}Local Time:{RESET} {current_time}")

        if timezone in ('', 'UTC'):
            print(f"\n{YELLOW}Warning: Timezone is {timezone or 'empty'} - unusual for a personal machine.{RESET}")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "timedatectl not found"
            return summary
        print(f"{YELLOW}timedatectl not found. Is systemd available?{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}timedatectl check failed: {e}{RESET}")

def check_load_avg(as_dict=False):
    """Check system load average against CPU count."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "cpu_count": 0, "load_avg": [0.0, 0.0, 0.0], "threshold": 0}

    try:
        # Read /proc/loadavg
        with open('/proc/loadavg', 'r') as f:
            load_parts = f.read().split()
        load_avg = [float(load_parts[0]), float(load_parts[1]), float(load_parts[2])]

        # Count CPUs from /proc/cpuinfo
        with open('/proc/cpuinfo', 'r') as f:
            cpu_count = sum(1 for line in f if line.startswith('processor'))

        if cpu_count == 0:
            cpu_count = 1

        summary["cpu_count"] = cpu_count
        summary["load_avg"] = load_avg
        summary["threshold"] = cpu_count

        load_15 = load_avg[2]
        threshold_warn = cpu_count * 0.75

        if as_dict:
            if load_15 > cpu_count:
                summary["status"] = "attention"
                summary["issues"] = 1
            elif load_15 > threshold_warn:
                summary["status"] = "attention"
            return summary

        print_header("System Load Average")
        print(f"{BOLD}CPU Count:{RESET} {cpu_count}")
        print(f"{BOLD}Load Average (1/5/15 min):{RESET} {load_avg[0]:.2f} / {load_avg[1]:.2f} / {load_avg[2]:.2f}")
        print(f"{BOLD}Threshold (15-min):{RESET} {cpu_count}")

        if load_15 > cpu_count:
            print(f"\n{RED}{BOLD}Warning: 15-min load average ({load_15:.2f}) exceeds CPU count ({cpu_count})!{RESET}")
            issue_count += 1
            summary["status"] = "attention"
            summary["issues"] = 1
        elif load_15 > threshold_warn:
            print(f"\n{YELLOW}Warning: 15-min load average ({load_15:.2f}) is above 75% of CPU count.{RESET}")
            summary["status"] = "attention"
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "/proc/loadavg or /proc/cpuinfo not found"
            return summary
        print(f"{YELLOW}Could not read /proc/loadavg or /proc/cpuinfo.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}Load average check failed: {e}{RESET}")

def check_inotify_limit(as_dict=False):
    """Check inotify watch limit usage."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "limit": 0, "usage": 0, "percentage": 0}

    try:
        # Read limit
        with open('/proc/sys/fs/inotify/max_user_watches', 'r') as f:
            limit = int(f.read().strip())

        with open('/proc/sys/fs/inotify/max_user_instances', 'r') as f:
            instances_limit = int(f.read().strip())

        summary["limit"] = limit

        # Try to count usage (requires root)
        usage = 0
        try:
            # List all PIDs
            pids = [d for d in os.listdir('/proc') if d.isdigit()]
            for pid in pids:
                try:
                    fd_path = os.path.join('/proc', pid, 'fd')
                    if os.path.isdir(fd_path):
                        for fd in os.listdir(fd_path):
                            try:
                                link = os.readlink(os.path.join(fd_path, fd))
                                if link.startswith('inotify'):
                                    usage += 1
                            except (OSError, FileNotFoundError):
                                pass
                except (OSError, FileNotFoundError):
                    pass
        except Exception:
            pass

        summary["usage"] = usage
        if limit > 0:
            summary["percentage"] = round((usage / limit) * 100, 1)

        if as_dict:
            if usage > 0:
                if summary["percentage"] > 90:
                    summary["status"] = "attention"
                    summary["issues"] = 1
                elif summary["percentage"] > 75:
                    summary["status"] = "attention"
            return summary

        print_header("Inotify Watch Limit")
        print(f"{BOLD}Max User Watches:{RESET} {limit}")
        print(f"{BOLD}Max User Instances:{RESET} {instances_limit}")

        if usage > 0:
            print(f"{BOLD}Current Usage:{RESET} {usage} ({summary['percentage']}%)")
            if summary["percentage"] > 90:
                print(f"\n{RED}{BOLD}Warning: Inotify usage ({summary['percentage']}%) is above 90%!{RESET}")
                issue_count += 1
                summary["status"] = "attention"
                summary["issues"] = 1
            elif summary["percentage"] > 75:
                print(f"\n{YELLOW}Warning: Inotify usage ({summary['percentage']}%) is above 75%.{RESET}")
                summary["status"] = "attention"
        else:
            # Try root check
            is_root = os.geteuid() == 0
            if not is_root:
                print(f"{YELLOW}Usage count requires root. Run with sudo for accurate usage.{RESET}")
            else:
                print(f"{GREEN}No inotify watches in use.{RESET}")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "inotify sysfs not found"
            return summary
        print(f"{YELLOW}Inotify sysfs not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}Inotify limit check failed: {e}{RESET}")

def check_checkupdates(as_dict=False):
    """Show pending updates from checkupdates (pacman-contrib)."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "updates": [], "count": 0}

    # Check if checkupdates is installed
    if not shutil.which('checkupdates'):
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "checkupdates not installed"
            return summary
        print_header("Pending Updates")
        print(f"{YELLOW}checkupdates not installed. Install pacman-contrib to enable this check.{RESET}")
        return

    try:
        out = subprocess.check_output(["checkupdates"], text=True, stderr=subprocess.DEVNULL)
        updates = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                pkg = parts[0]
                version = parts[1] if len(parts) > 1 else "unknown"
                updates.append({"package": pkg, "version": version})

        summary["updates"] = updates
        summary["count"] = len(updates)

        if as_dict:
            return summary

        print_header("Pending Updates")
        if not updates:
            print(f"{GREEN}System up to date.{RESET}")
        else:
            print(f"{BOLD}{len(updates)} update(s) available:{RESET}")
            for u in updates:
                print(f"  {CYAN}{u['package']}{RESET} → {u['version']}")
        # Don't increment issue_count - pending updates are not issues
    except subprocess.CalledProcessError:
        if as_dict:
            summary["status"] = "ok"
            return summary
        print(f"{GREEN}System up to date.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}checkupdates failed: {e}{RESET}")

def check_pacnew(as_dict=False):
    """Scan for .pacnew/.pacsave files with age analysis."""
    global issue_count
    import time
    found = [os.path.join(r, f) for r, _, fs in os.walk('/etc') for f in fs if f.endswith(('.pacnew', '.pacsave'))]
    current_time = time.time()

    files_with_age = []
    for f in found:
        try:
            mtime = os.path.getmtime(f)
            age_days = (current_time - mtime) / 86400
            files_with_age.append({"path": f, "age_days": int(age_days)})
        except OSError:
            files_with_age.append({"path": f, "age_days": 0})

    if as_dict:
        result = {
            "files": files_with_age,
            "count": len(files_with_age),
            "status": "pending" if files_with_age else "ok",
            "issues": len(files_with_age) if files_with_age else 0
        }
        return result

    print_header("Config Files (.pacnew/.pacsave)")
    if not found:
        print(f"{GREEN}No pending merges.{RESET}")
    else:
        issue_count += len(found)
        for item in files_with_age:
            age = item["age_days"]
            path = item["path"]
            if age > 90:
                print(f"{RED}  -> {path} ({age} days old){RESET}")
            elif age >= 7:
                print(f"{YELLOW}  -> {path} ({age} days old){RESET}")
            else:
                print(f"{GREEN}  -> {path} ({age} days old){RESET}")

def check_systemd_timers(as_dict=False):
    """Check systemd timer status and missed runs. Informational only - does not increment issue_count."""
    import subprocess
    summary = {"status": "ok", "issues": 0, "timers": []}

    try:
        out = subprocess.check_output(["systemctl", "list-timers", "--all", "--no-pager", "--no-legend"], text=True)
        timers = []
        missed_never = []

        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 6:
                # Columns: NEXT, LEFT, LAST, PASSED, UNIT, ACTIVATES (may vary)
                unit = parts[-1]
                last = parts[2] if len(parts) > 2 else 'n/a'
                next_run = parts[0] if len(parts) > 0 else 'n/a'

                timer_entry = {"unit": unit, "last": last, "next": next_run}

                # Check for never run (n/a in LAST)
                if last == 'n/a' or 'n/a' in last:
                    missed_never.append(timer_entry)
                    timers.append({"unit": unit, "status": "never_run", "last": last, "next": next_run})
                else:
                    timers.append({"unit": unit, "status": "active", "last": last, "next": next_run})

        summary["timers"] = timers
        summary["missed_never"] = missed_never
        summary["count"] = len(timers)

        if as_dict:
            return summary

        print_header("Systemd Timers (Informational)")

        if missed_never:
            print(f"\n{YELLOW}{BOLD}Timers that have never run:{RESET}")
            for t in missed_never:
                print(f"  {YELLOW}{t['unit']}{RESET} - Last: {t['last']}")

        if not missed_never and not timers:
            print(f"{GREEN}No timers found.{RESET}")
        elif not missed_never:
            print(f"{GREEN}All timers appear active.{RESET}")

        print(f"\n{CYAN}Note: This is informational only. Timer status does not affect system health.{RESET}")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "systemctl not found"
            return summary
        print(f"{YELLOW}systemctl not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}systemd timers check failed: {e}{RESET}")

def check_systemd_boot_blame(as_dict=False):
    """Show systemd boot timing (slowest units)."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "boot_time": 0, "slowest_units": []}

    # Maintenance units to exclude from threshold flagging
    maintenance_units = {
        'plocate-updatedb.service', 'man-db.service', 'updatedb.service',
        'mlocate-updatedb.service'
    }

    try:
        # Get total boot time
        boot_out = subprocess.check_output(["systemd-analyze"], text=True, stderr=subprocess.DEVNULL)
        boot_time = 0
        import re
        match = re.search(r'(\d+)ms', boot_out)
        if match:
            boot_time = int(match.group(1)) / 1000  # Convert to seconds
        else:
            match = re.search(r'(\d+\.\d+)\s*s', boot_out)
            if match:
                boot_time = float(match.group(1))

        summary["boot_time"] = boot_time

        # Get slowest units
        blame_out = subprocess.check_output(["systemd-analyze", "blame", "--no-pager"], text=True, stderr=subprocess.DEVNULL)
        units = []
        for line in blame_out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    # Parse duration (e.g., "1.234s", "500ms", "1min 30s")
                    duration_str = parts[0]
                    duration_sec = 0
                    if 'min' in duration_str:
                        m_match = re.search(r'(\d+)min', duration_str)
                        if m_match:
                            duration_sec += int(m_match.group(1)) * 60
                    if 's' in duration_str:
                        s_match = re.search(r'(\d+\.?\d*)s', duration_str)
                        if s_match:
                            duration_sec += float(s_match.group(1))
                    elif 'ms' in duration_str:
                        ms_match = re.search(r'(\d+)ms', duration_str)
                        if ms_match:
                            duration_sec += int(ms_match.group(1)) / 1000

                    unit_name = parts[1].rstrip(',')
                    is_maintenance = unit_name in maintenance_units
                    units.append({"unit": unit_name, "duration_sec": duration_sec, "maintenance": is_maintenance})
                except (ValueError, IndexError):
                    pass

        # Sort by duration and get top 10
        units.sort(key=lambda x: x["duration_sec"], reverse=True)
        top_10 = units[:10]
        summary["slowest_units"] = top_10

        if as_dict:
            if boot_time > 45:
                summary["status"] = "attention"
                summary["issues"] = 1
            return summary

        print_header("Boot Timing (systemd-analyze blame)")
        print(f"{BOLD}Total Boot Time:{RESET} {boot_time:.1f}s")

        print(f"\n{BOLD}Top 10 Slowest Units:{RESET}")
        print(f"{BOLD}{'Unit':<60} : {'Duration'}{RESET}")
        print("─" * 75)
        for i, u in enumerate(top_10, 1):
            color = ""
            # Only flag non-maintenance units
            if not u["maintenance"]:
                if u["duration_sec"] > 30:
                    color = RED
                elif u["duration_sec"] > 10:
                    color = YELLOW
            suffix = " (maintenance timer)" if u["maintenance"] else ""
            print(f"{i:2}. {color}{u['unit']:<60} : {u['duration_sec']:.1f}s{suffix}{RESET}")

        # Only flag total boot time if > 45 seconds
        if boot_time > 45:
            print(f"\n{RED}{BOLD}Warning: Total boot time ({boot_time:.1f}s) exceeds 45 seconds.{RESET}")
            summary["status"] = "attention"
            summary["issues"] = 1
        elif boot_time > 30:
            print(f"\n{YELLOW}Note: Total boot time ({boot_time:.1f}s) exceeds 30 seconds.{RESET}")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "systemd-analyze not found"
            return summary
        print(f"{YELLOW}systemd-analyze not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}Boot timing check failed: {e}{RESET}")

def check_arch_audit(as_dict=False):
    """Check AUR packages for known vulnerabilities using arch-audit."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "vulnerable_packages": [], "high": 0, "medium": 0, "low": 0}

    # Check if arch-audit is installed
    if not shutil.which('arch-audit'):
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "arch-audit not installed"
            return summary
        print_header("AUR Package Audit")
        print(f"{YELLOW}arch-audit not installed. Install arch-audit to enable this check.{RESET}")
        return

    try:
        # Run arch-audit with machine-readable output
        out = subprocess.check_output(["arch-audit", "--format", "%n %s %c"], text=True, stderr=subprocess.DEVNULL)

        packages = []
        high_count = 0
        medium_count = 0
        low_count = 0

        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                pkg = parts[0]
                severity = parts[1].upper()
                cves = parts[2] if len(parts) > 2 else "N/A"

                packages.append({"package": pkg, "severity": severity, "cves": cves})

                if severity == "HIGH":
                    high_count += 1
                elif severity == "MEDIUM":
                    medium_count += 1
                elif severity == "LOW":
                    low_count += 1

        summary["vulnerable_packages"] = packages
        summary["high"] = high_count
        summary["medium"] = medium_count
        summary["low"] = low_count

        if as_dict:
            if high_count > 0:
                summary["status"] = "attention"
                summary["issues"] = high_count
            return summary

        print_header("AUR Package Audit (arch-audit)")

        if not packages:
            print(f"{GREEN}No known vulnerabilities in AUR packages.{RESET}")
        else:
            # Group packages by severity for display
            high_pkgs = [p for p in packages if p["severity"] == "HIGH"]
            medium_pkgs = [p for p in packages if p["severity"] == "MEDIUM"]
            low_pkgs = [p for p in packages if p["severity"] == "LOW"]

            if high_pkgs:
                print(f"\n{RED}{BOLD}HIGH severity ({len(high_pkgs)}):{RESET}")
                issue_count += len(high_pkgs)
                summary["status"] = "attention"
                summary["issues"] = high_count
                for p in high_pkgs:
                    print(f"  {RED}{p['package']}{RESET} - {p['cves']}")

            if medium_pkgs:
                print(f"\n{YELLOW}{BOLD}MEDIUM severity ({len(medium_pkgs)}):{RESET}")
                for p in medium_pkgs:
                    print(f"  {YELLOW}{p['package']}{RESET} - {p['cves']}")

            if low_pkgs:
                print(f"\n{CYAN}{BOLD}LOW severity ({len(low_pkgs)}):{RESET}")
                for p in low_pkgs:
                    print(f"  {CYAN}{p['package']}{RESET} - {p['cves']}")
    except subprocess.CalledProcessError:
        if as_dict:
            summary["status"] = "ok"
            return summary
        print(f"{GREEN}No known vulnerabilities in AUR packages.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}arch-audit failed: {e}{RESET}")

def check_journal_errors(as_dict=False):
    """Check journal for errors (crit..alert priority) in last 24 hours."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "total_errors": 0, "units": [], "recent_errors": []}

    try:
        # Use -p crit..alert to get only critical/alert level messages
        out = subprocess.check_output(
            ["journalctl", "-p", "crit..alert", "--since", "24 hours ago", "--no-pager", "--no-hostname"],
            text=True, stderr=subprocess.DEVNULL
        )

        lines = out.splitlines()
        total_errors = len(lines)
        summary["total_errors"] = total_errors

        # Helper to validate unit names
        def is_valid_unit_name(unit):
            """Validate that token looks like a real unit name, not a PID or partial word."""
            if not unit:
                return False
            # Reject if purely numeric (PID)
            if unit.isdigit():
                return False
            # Reject if short lowercase-only word (likely partial or noise)
            if len(unit) < 4 and unit.islower():
                return False
            # Accept if contains dot or dash (typical unit naming)
            if '.' in unit or '-' in unit:
                return True
            # Accept if contains both letters and digits (like process names)
            has_letter = any(c.isalpha() for c in unit)
            has_digit = any(c.isdigit() for c in unit)
            if has_letter and has_digit:
                return True
            # Accept known system processes (at least 4 chars or special names)
            if has_letter and len(unit) >= 4:
                return True
            # Reject anything else
            return False

        # Group by unit
        unit_errors = {}
        for line in lines:
            # Skip boot separator lines
            if line.strip().startswith('--'):
                continue

            # Skip continuation lines (start with whitespace)
            if line.startswith(' ') or line.startswith('\t'):
                continue

            # Parse unit name: format is "TIMESTAMP HOSTNAME UNIT[PID]: message"
            # The unit is the token before the first '['
            unit = "kernel"  # Default to kernel for lines without proper unit
            parts = line.split()
            for i, part in enumerate(parts):
                if '[' in part:
                    # Extract unit name (before the '[')
                    candidate = part.split('[')[0].strip()
                    # Validate the candidate
                    if is_valid_unit_name(candidate):
                        unit = candidate
                    break
                elif i > 2 and ':' in part:
                    # Fallback: look for token with colon after timestamp/hostname
                    candidate = part.split(':')[0].strip()
                    if is_valid_unit_name(candidate):
                        unit = candidate
                    break

            if unit not in unit_errors:
                unit_errors[unit] = []
            # Truncate line to 120 chars
            unit_errors[unit].append(line[:120])

        # Get top 10 noisiest units
        sorted_units = sorted(unit_errors.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        units_data = []
        for unit, err_lines in sorted_units:
            units_data.append({
                "unit": unit,
                "count": len(err_lines),
                "recent": err_lines[:3]
            })

        summary["units"] = units_data

        if as_dict:
            if total_errors > 50:
                summary["status"] = "attention"
                summary["issues"] = 1
            elif total_errors > 10:
                summary["status"] = "attention"
            return summary

        print_header("Journal Errors (last 24h)")

        if total_errors == 0:
            print(f"{GREEN}No critical/alert errors in journal.{RESET}")
        else:
            if total_errors > 50:
                print(f"\n{RED}{BOLD}Warning: {total_errors} errors found (above 50)!{RESET}")
                issue_count += 1
                summary["status"] = "attention"
                summary["issues"] = 1
            elif total_errors > 10:
                print(f"\n{YELLOW}Warning: {total_errors} errors found.{RESET}")
                summary["status"] = "attention"

            print(f"\n{BOLD}Top 10 Noisiest Units:{RESET}")
            print(f"{BOLD}{'Unit':<50} : {'Count'}{RESET}")
            print("─" * 65)
            for u in units_data:
                print(f"{u['unit']:<50} : {u['count']}")

            # Show recent errors for top unit
            if units_data:
                print(f"\n{BOLD}Recent errors from {units_data[0]['unit']}: {RESET}")
                for line in units_data[0]["recent"]:
                    print(f"  {line[:120]}")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "journalctl not found"
            return summary
        print(f"{YELLOW}journalctl not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}Journal check failed: {e}{RESET}")

def check_dmesg_errors(as_dict=False):
    """Check kernel ring buffer for hardware/system errors."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "categories": {}, "total_errors": 0}

    # Keywords to flag as RED
    critical_keywords = ['mce', 'hardware error', 'i/o error', 'filesystem error', 'oom', 'out of memory']

    try:
        # Try multiple dmesg flag variations for error-level messages
        out = ""
        for level_args in [
            ["--level=err,crit,alert,emerg"],  # Long form
            ["-l", "err,crit,alert,emerg"],     # Short form
        ]:
            for time_arg in ["--since", "24h", ""]:  # Try with time filter, then without
                try:
                    cmd = ["dmesg"] + level_args + ([time_arg, "24h"] if time_arg else []) + ["--notime", "--nopager"]
                    out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                    break
                except subprocess.CalledProcessError:
                    continue
            if out:
                break

        # If all level-based approaches failed, fall back to manual filtering
        if not out:
            try:
                out = subprocess.check_output(["dmesg", "--notime", "--nopager"], text=True, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                out = subprocess.check_output(["dmesg"], text=True, stderr=subprocess.DEVNULL)
            # Manually filter for error-level messages
            out = "\n".join([
                line for line in out.splitlines()
                if any(kw in line.lower() for kw in ['error', 'fail', 'critical', 'emergency', 'alert', 'mce'])
            ])

        lines = out.splitlines()
        
        # Deduplicate lines by exact string match
        lines = list(dict.fromkeys(lines))
        
        summary["total_errors"] = len(lines)

        # Categorize
        categories = {}
        for line in lines:
            line_lower = line.lower()[:120]
            category = "other"

            for kw in critical_keywords:
                if kw in line_lower:
                    category = kw
                    break

            if category not in categories:
                categories[category] = []
            categories[category].append(line_lower)

        summary["categories"] = {k: len(v) for k, v in categories.items()}

        if as_dict:
            critical_count = sum(len(v) for k, v in categories.items() if k in critical_keywords)
            if critical_count > 0:
                summary["status"] = "attention"
                summary["issues"] = critical_count
            return summary

        print_header("Kernel Errors (dmesg)")

        if not lines:
            print(f"{GREEN}No kernel errors found in last 24h.{RESET}")
        else:
            critical_count = sum(len(v) for k, v in categories.items() if k in critical_keywords)

            # Show summary first
            print(f"\n{BOLD}Total errors: {len(lines)}{RESET}")
            if critical_count > 0:
                print(f"{RED}{BOLD}Critical errors: {critical_count}{RESET}")
                issue_count += 1
                summary["status"] = "attention"
                summary["issues"] = 1

            # Show counts by category (condensed)
            print(f"\n{BOLD}By category:{RESET}")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                if cat in critical_keywords:
                    print(f"  {RED}{cat}: {count}{RESET}")
                else:
                    print(f"  {cat}: {count}")

            # Show 3 examples per category (max 3 categories)
            if len(lines) > 3:
                print(f"\n{BOLD}Examples (3 per category, max 3 categories):{RESET}")
                shown_cats = 0
                for cat in list(categories.keys())[:3]:
                    if shown_cats >= 3:
                        break
                    print(f"\n{CYAN}{cat} ({len(categories[cat])} total):{RESET}")
                    for line in categories[cat][:3]:
                        print(f"  {line[:100]}")
                    shown_cats += 1
                if len(categories) > 3:
                    print(f"\n  ... and {len(categories) - 3} more categories")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "dmesg not found"
            return summary
        print(f"{YELLOW}dmesg not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}dmesg check failed: {e}{RESET}")

def check_listening_ports(as_dict=False):
    """Check listening ports for unexpected services."""
    global issue_count
    import subprocess
    import re
    summary = {"status": "ok", "issues": 0, "listeners": [], "unexpected": [], "external": []}

    try:
        out = subprocess.check_output(["ss", "-tlnpu", "--numeric"], text=True, stderr=subprocess.DEVNULL)
        lines = out.splitlines()[1:]  # Skip header

        listeners = []
        unexpected = []
        external = []

        for line in lines:
            parts = line.split()
            if len(parts) < 4:
                continue

            proto = parts[0]

            # ss -tlnpu output format: Netid Recv-Q Send-Q Local Address:Port Peer Address:Port Process
            # Local Address:Port is typically parts[3], but verify it looks like an address
            local_addr = None
            process_info = "unknown"

            # Find the local address column (should contain ':' or '*')
            for part in parts[1:]:
                if ':' in part or part in ('*', '[::]'):
                    # Check if next part looks like a port (numeric) or process info
                    local_addr = part
                    break

            if not local_addr:
                continue

            # Get process info (last column, usually contains users:((...)))
            for part in parts:
                if 'users:' in part or part.startswith('("'):
                    process_info = part
                    break

            # Parse address:port - split on LAST colon
            if ':' in local_addr:
                addr_parts = local_addr.rsplit(':', 1)
                # Validate port is numeric
                if addr_parts[1].isdigit():
                    address = addr_parts[0]
                    port = addr_parts[1]
                else:
                    # IPv6 case like [::]:22 - already handled by rsplit
                    address = local_addr
                    port = "?"
            else:
                address = local_addr
                port = "?"

            # Parse process name from format like "users:((\"nginx\",pid=123,fd=4))"
            proc_match = re.search(r'\(\("([^"]+)"', process_info)
            proc_name = proc_match.group(1) if proc_match else "unknown"

            listener = {
                "proto": proto,
                "address": address,
                "port": port,
                "process": proc_name,
                "pid": "unknown",
                "managed": False
            }

            # Check if process is managed by systemd
            is_managed = False
            try:
                pid_match = re.search(r'pid=(\d+)', process_info)
                if pid_match:
                    pid = pid_match.group(1)
                    unit_out = subprocess.check_output(["systemctl", "status", pid], text=True, stderr=subprocess.DEVNULL)
                    if "Loaded:" in unit_out and "not-found" not in unit_out:
                        is_managed = True
                        listener["managed"] = True
                        listener["pid"] = pid
            except subprocess.CalledProcessError:
                pass
            except Exception:
                pass

            # Check if externally reachable
            if address in ('0.0.0.0', '::', '*', '[::]'):
                listener["external"] = True
                external.append(listener)
            elif not is_managed:
                listener["external"] = False
                unexpected.append(listener)

            listeners.append(listener)

        summary["listeners"] = listeners
        summary["unexpected"] = unexpected
        summary["external"] = external

        if as_dict:
            if unexpected:
                summary["status"] = "attention"
                summary["issues"] = len(unexpected)
            return summary

        print_header("Listening Ports")

        if not listeners:
            print(f"{GREEN}No listening ports found.{RESET}")
        else:
            # Calculate dynamic column widths based on actual data
            proto_width = max(len(l['proto']) for l in listeners) if listeners else 4
            address_width = max(len(l['address']) for l in listeners) if listeners else 10
            port_width = max(len(l['port']) for l in listeners) if listeners else 4
            process_width = max(len(l['process']) for l in listeners) if listeners else 7
            managed_width = 3  # "yes" or "no"
            
            # Add minimum widths and buffer for readability
            proto_width = max(proto_width, 5)
            address_width = max(address_width, 7)
            port_width = max(port_width, 4)
            process_width = max(process_width, 7)
            
            # Calculate separator line length
            # Format: proto : address : port : process : managed
            sep_length = proto_width + 3 + address_width + 3 + port_width + 3 + process_width + 3 + managed_width
            
            # Show table with dynamically aligned columns
            print(f"{BOLD}{'PROTO':<{proto_width}} : {'ADDRESS':<{address_width}} : {'PORT':<{port_width}} : {'PROCESS':<{process_width}} : {'MANAGED':<{managed_width}}{RESET}")
            print("─" * sep_length)
            for l in listeners:
                managed_str = f"{GREEN}yes{RESET}" if l["managed"] else f"{YELLOW}no{RESET}"
                print(f"{l['proto']:<{proto_width}} : {l['address']:<{address_width}} : {l['port']:<{port_width}} : {l['process']:<{process_width}} : {managed_str:<{managed_width}}")

            if unexpected:
                print(f"\n{RED}{BOLD}Unexpected listeners (not managed by systemd):{RESET}")
                for l in unexpected:
                    print(f"  {RED}{l['proto']} {l['address']}:{l['port']} ({l['process']}){RESET}")
                issue_count += len(unexpected)
                summary["status"] = "attention"
                summary["issues"] = len(unexpected)

            if external:
                print(f"\n{YELLOW}{BOLD}Externally reachable (0.0.0.0 or ::):{RESET}")
                for l in external:
                    print(f"  {YELLOW}{l['proto']} {l['address']}:{l['port']}{RESET}")
    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "ss not found"
            return summary
        print(f"{YELLOW}ss command not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}Listening ports check failed: {e}{RESET}")

def check_failed_logins(as_dict=False):
    """Check for failed login attempts using lastb."""
    global issue_count
    import subprocess
    summary = {"status": "ok", "issues": 0, "total_failed": 0, "recent_attempts": []}

    # Check if lastb is available
    if not shutil.which('lastb'):
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "lastb not found"
            return summary
        print_header("Failed Login Attempts")
        print(f"{YELLOW}lastb not found.{RESET}")
        return

    try:
        # Check if btmp is readable (requires root)
        try:
            with open('/var/log/btmp', 'r') as f:
                pass
        except PermissionError:
            if as_dict:
                summary["status"] = "skipped"
                summary["error"] = "Permission denied - requires root"
                return summary
            print_header("Failed Login Attempts")
            print(f"{YELLOW}Permission denied reading /var/log/btmp. Run with sudo.{RESET}")
            return

        # Get total count using wc -l
        count_out = subprocess.check_output("lastb 2>/dev/null | wc -l", shell=True, text=True)
        total = int(count_out.strip())
        summary["total_failed"] = total

        # Get recent attempts
        recent_out = subprocess.check_output(["lastb", "-n", "20", "--time-format", "iso"], text=True, stderr=subprocess.DEVNULL)
        recent_lines = recent_out.splitlines()

        # Skip header line if present
        if recent_lines and "user" in recent_lines[0].lower():
            recent_lines = recent_lines[1:]

        attempts = []
        for line in recent_lines[:20]:
            parts = line.split()
            if len(parts) >= 3:
                attempts.append({
                    "user": parts[0],
                    "source": parts[2] if len(parts) > 2 else "unknown",
                    "line": line[:120]
                })

        summary["recent_attempts"] = attempts

        if as_dict:
            if total > 100:
                summary["status"] = "attention"
                summary["issues"] = 1
            elif total > 10:
                summary["status"] = "attention"
            return summary

        print_header("Failed Login Attempts")

        if total == 0:
            print(f"{GREEN}No failed login attempts.{RESET}")
        else:
            if total > 100:
                print(f"\n{RED}{BOLD}Warning: {total} failed login attempts (possible brute force)!{RESET}")
                issue_count += 1
                summary["status"] = "attention"
                summary["issues"] = 1
            elif total > 10:
                print(f"\n{YELLOW}Warning: {total} failed login attempts.{RESET}")
                summary["status"] = "attention"

            print(f"\n{BOLD}Last 20 failed attempts:{RESET}")
            for a in attempts:
                print(f"  {a['line'][:120]}")
    except subprocess.CalledProcessError:
        if as_dict:
            summary["status"] = "ok"
            return summary
        print(f"{GREEN}No failed login attempts.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}Failed logins check failed: {e}{RESET}")

def check_aur_stale(as_dict=False):
    """Check AUR packages for version mismatches and maintainer-flagged out-of-date packages."""
    global issue_count
    import subprocess
    import json
    import urllib.request
    import urllib.parse

    summary = {
        "status": "ok",
        "issues": 0,
        "up_to_date": 0,
        "updates_available": [],
        "maintainer_flagged": [],
        "not_found_on_aur": []
    }

    try:
        import time
        import json
        
        # Get foreign packages
        out = subprocess.check_output(["pacman", "-Qmq"], text=True).strip()
        if not out:
            if as_dict:
                summary["packages_checked"] = 0
                return summary
            print_header("AUR Stale Packages")
            print(f"{GREEN}No AUR (foreign) packages found.{RESET}")
            return

        foreign_pkgs = [pkg.strip() for pkg in out.splitlines() if pkg.strip()]
        summary["packages_checked"] = len(foreign_pkgs)

        if not foreign_pkgs:
            if as_dict:
                return summary
            print_header("AUR Stale Packages")
            print(f"{GREEN}No AUR (foreign) packages found.{RESET}")
            return

        # Build batched requests to AUR RPC, chunking by 20 packages per request
        def _chunked(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i+n]

        aur_info = {}
        cache_path = "/tmp/arch_check_aur_cache.json"
        cache_ttl = 3600  # 1 hour
        use_cache = False
        cache_age_min = 0
        
        # Check if cache is valid
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                    cache_timestamp = cache_data.get('timestamp', 0)
                    current_time = time.time()
                    cache_age = current_time - cache_timestamp
                    if cache_age < cache_ttl:
                        # Cache is still valid
                        aur_info = cache_data.get('results', {})
                        use_cache = True
                        cache_age_min = int(cache_age / 60)
        except:
            pass  # Silently fall through to live fetch on any cache error
        
        # Fetch from AUR API if cache not available
        if not use_cache:
            try:
                for chunk in _chunked(foreign_pkgs, 20):
                    query_params = urllib.parse.urlencode([('arg[]', p) for p in chunk])
                    url = f"https://aur.archlinux.org/rpc?v=5&type=info&{query_params}"
                    headers = {'User-Agent': 'arch-check/1.0 (system audit tool)'}
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        for item in data.get('results', []):
                            aur_info[item.get('Name')] = item
                
                # Write to cache
                try:
                    cache_data = {
                        'timestamp': time.time(),
                        'results': aur_info
                    }
                    with open(cache_path, 'w') as f:
                        json.dump(cache_data, f)
                except:
                    pass  # Silently ignore cache write failures
            except Exception as e:
                if as_dict:
                    summary["status"] = "skipped"
                    summary["error"] = f"Network error: {e}"
                    return summary
                print_header("AUR Stale Packages")
                print(f"{YELLOW}Network error accessing aur.archlinux.org: {e}{RESET}")
                return

        # Build installed versions dict from pacman -Qm (all foreign packages at once)
        installed = {}
        try:
            qm = subprocess.check_output(['pacman', '-Qm'], text=True)
            for line in qm.strip().splitlines():
                parts = line.split()
                if len(parts) == 2:
                    installed[parts[0]] = parts[1]
        except subprocess.CalledProcessError:
            pass

        # Compare versions using vercmp
        up_to_date = 0
        updates_available = []
        locally_ahead = []
        maintainer_flagged = []
        not_found = []

        for pkg in foreign_pkgs:
            installed_ver = installed.get(pkg, "unknown")

            if pkg not in aur_info:
                not_found.append(pkg)
                continue

            aur_pkg = aur_info[pkg]
            aur_ver = aur_pkg.get('Version', 'unknown')
            out_of_date = aur_pkg.get('OutOfDate')  # unix timestamp or null

            # Use vercmp to compare versions
            cmp_result = 0  # Default to equal if vercmp fails
            if installed_ver != "unknown" and aur_ver != "unknown":
                try:
                    result = subprocess.run(
                        ['vercmp', installed_ver, aur_ver],
                        capture_output=True, text=True
                    )
                    cmp_result = int(result.stdout.strip())
                except:
                    # Fallback to string comparison
                    if installed_ver == aur_ver:
                        cmp_result = 0
                    elif installed_ver < aur_ver:
                        cmp_result = -1
                    else:
                        cmp_result = 1
            elif installed_ver == aur_ver:
                cmp_result = 0
            elif aur_ver == "unknown":
                cmp_result = 1  # installed version exists, aur doesn't

            # Check for maintainer-flagged packages first (separate from version comparison)
            if out_of_date is not None:
                from datetime import datetime as dt
                flagged_date = dt.fromtimestamp(out_of_date).strftime('%Y-%m-%d')
                status_entry = {
                    "name": pkg,
                    "installed": installed_ver,
                    "aur_version": aur_ver,
                    "flagged_since": flagged_date
                }
                maintainer_flagged.append(status_entry)
                summary["issues"] += 1
            else:
                # Only categorize by version if NOT flagged
                if cmp_result == 0:
                    up_to_date += 1
                elif cmp_result < 0:
                    # installed is older: update available
                    status_entry = {
                        "name": pkg,
                        "installed": installed_ver,
                        "aur_version": aur_ver
                    }
                    updates_available.append(status_entry)
                elif cmp_result > 0:
                    # installed is newer: locally ahead
                    status_entry = {
                        "name": pkg,
                        "installed": installed_ver,
                        "aur_version": aur_ver
                    }
                    locally_ahead.append(status_entry)

        summary["up_to_date"] = up_to_date
        summary["updates_available"] = updates_available
        summary["locally_ahead"] = locally_ahead
        summary["maintainer_flagged"] = maintainer_flagged
        summary["not_found_on_aur"] = not_found

        if as_dict:
            if summary["issues"] > 0:
                summary["status"] = "attention"
            return summary

        print_header("AUR Stale Packages")
        
        # Show cache status if used
        if use_cache:
            print(f"{CYAN}AUR data from cache ({cache_age_min} min old){RESET}")

        if not maintainer_flagged and not updates_available and not locally_ahead and not not_found:
            print(f"{GREEN}All AUR packages up to date.{RESET}")
        else:
            # Calculate dynamic column widths across all three tables
            all_entries = updates_available + locally_ahead + maintainer_flagged
            
            if all_entries:
                pkg_width = max(len(e['name']) for e in all_entries) if all_entries else 7
                inst_width = max(len(e['installed']) for e in all_entries) if all_entries else 9
                aur_width = max(len(e['aur_version']) for e in all_entries) if all_entries else 11
                since_width = max(len(e.get('flagged_since', '')) for e in maintainer_flagged) if maintainer_flagged else 5
                
                # Apply minimum widths
                pkg_width = max(pkg_width, 7)
                inst_width = max(inst_width, 9)
                aur_width = max(aur_width, 11)
                since_width = max(since_width, 5)
            else:
                pkg_width, inst_width, aur_width, since_width = 7, 9, 11, 5

            if updates_available:
                print(f"\n{YELLOW}{BOLD}Updates available:{RESET}")
                sep_length_3 = pkg_width + 3 + inst_width + 3 + aur_width
                print(f"{BOLD}{'PACKAGE':<{pkg_width}} : {'INSTALLED':<{inst_width}} : {'AUR VERSION'}{RESET}")
                print("─" * sep_length_3)
                for entry in updates_available:
                    print(f"{entry['name']:<{pkg_width}} : {entry['installed']:<{inst_width}} : {YELLOW}{entry['aur_version']}{RESET}")

            if locally_ahead:
                print(f"\n{CYAN}{BOLD}Locally ahead of AUR (custom build or held version):{RESET}")
                sep_length_3 = pkg_width + 3 + inst_width + 3 + aur_width
                print(f"{BOLD}{'PACKAGE':<{pkg_width}} : {'INSTALLED':<{inst_width}} : {'AUR VERSION'}{RESET}")
                print("─" * sep_length_3)
                for entry in locally_ahead:
                    print(f"{CYAN}{entry['name']:<{pkg_width}} : {entry['installed']:<{inst_width}} : {entry['aur_version']}{RESET}")

            if maintainer_flagged:
                print(f"\n{RED}{BOLD}Flagged out of date by maintainer:{RESET}")
                sep_length_4 = pkg_width + 3 + inst_width + 3 + aur_width + 3 + since_width
                print(f"{BOLD}{'PACKAGE':<{pkg_width}} : {'INSTALLED':<{inst_width}} : {'AUR VERSION':<{aur_width}} : {'SINCE'}{RESET}")
                print("─" * sep_length_4)
                for entry in maintainer_flagged:
                    print(f"{RED}{entry['name']:<{pkg_width}} : {entry['installed']:<{inst_width}} : {entry['aur_version']:<{aur_width}} : {entry['flagged_since']}{RESET}")

            if not_found:
                print(f"\n{YELLOW}{BOLD}Not found on AUR (may be split packages or local builds):{RESET}")
                for pkg in not_found:
                    print(f"  {YELLOW}{pkg}{RESET}")

        if summary["issues"] > 0:
            issue_count += summary["issues"]

    except FileNotFoundError:
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "pacman not found"
            return summary
        print(f"{YELLOW}pacman not found.{RESET}")
    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}AUR stale check failed: {e}{RESET}")


def check_pacman_log(as_dict=False, days=30):
    """Parse /var/log/pacman.log to surface recent package changes."""
    global issue_count
    import subprocess
    from datetime import datetime, timedelta, timezone
    import re

    summary = {
        "status": "ok",
        "issues": 0,
        "days_since_upgrade": 0,
        "last_upgrade_date": None,
        "installs": [],
        "upgrades": [],
        "removes": [],
        "silent_removes": []
    }

    log_path = "/var/log/pacman.log"

    if not os.path.exists(log_path):
        if as_dict:
            summary["status"] = "skipped"
            summary["error"] = "pacman log not found"
            return summary
        print_header("Pacman Log Analysis")
        print(f"{YELLOW}pacman log not found at {log_path}.{RESET}")
        return

    try:
        import time
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Use proper regex to parse pacman.log format
        LOG_RE = re.compile(
            r'^\[(?P<ts>[^\]]+)\]'      # [timestamp]
            r'\s+\[ALPM\]\s+'           # [ALPM] with literal brackets
            r'(?P<action>installed|upgraded|removed|downgraded)'
            r'\s+(?P<pkg>[^\s]+)'       # package name
            r'\s+\((?P<ver>[^)]+)\)'    # (version)
        )

        # Regex to parse [PACMAN] command lines
        PACMAN_RE = re.compile(
            r'^\[(?P<ts>[^\]]+)\]'      # [timestamp]
            r'\s+\[PACMAN\]\s+'         # [PACMAN] literal brackets
            r"Running\s+'pacman\s+(?P<cmd>[^']+)'"  # pacman command
        )

        installs = []
        upgrades = []
        removes = []
        session_events = []
        all_events = []  # Track all events with timestamps for transaction grouping

        with open(log_path, 'r') as f:
            lines = f.readlines()

        # Build a map of explicitly removed packages from [PACMAN] lines
        explicitly_removed = set()
        pacman_remove_timestamps = {}  # Map timestamp-second to list of explicitly removed packages
        for line in lines:
            pacman_match = PACMAN_RE.match(line)
            if pacman_match:
                ts_str = pacman_match.group('ts')
                cmd = pacman_match.group('cmd')
                # Only care about remove commands (-R, -Rs, -Rn, -Rns, etc.)
                if '-R' in cmd:
                    try:
                        ts_str_norm = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', ts_str)
                        ts = datetime.fromisoformat(ts_str_norm)
                        ts_min = ts.strftime('%Y-%m-%dT%H:%M')  # Timestamp-minute granularity
                        
                        # Extract package names: tokens after flags (not starting with -)
                        tokens = cmd.split()
                        for i, token in enumerate(tokens):
                            if token.startswith('-'):
                                continue  # Skip flags
                            if i > 0 and tokens[i-1].startswith('-'):
                                continue  # Skip if previous token is flag (flag arg)
                            explicitly_removed.add(token)
                            if ts_min not in pacman_remove_timestamps:
                                pacman_remove_timestamps[ts_min] = []
                            pacman_remove_timestamps[ts_min].append(token)
                    except:
                        pass

        # Diagnostic output collected but not printed (debug phase complete)

        # Parse each line with the regex
        for line in lines:
            line = line.rstrip('\n')
            if not line.strip():
                continue

            match = LOG_RE.match(line)
            if not match:
                continue

            ts_str = match.group('ts')
            try:
                # Insert colon into timezone offset for Python < 3.11 compatibility
                # e.g., +0200 becomes +02:00
                ts_str = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', ts_str)
                ts = datetime.fromisoformat(ts_str)
            except:
                continue

            # Check if past cutoff
            if ts < cutoff_date:
                continue

            action = match.group('action')
            pkg = match.group('pkg')
            ver = match.group('ver')
            ts_min = ts.strftime('%Y-%m-%dT%H:%M')  # Timestamp-minute granularity

            # Parse version string
            if action == 'upgraded':
                # version looks like "1.0 -> 2.0"
                parts = ver.split(' -> ')
                if len(parts) == 2:
                    old_ver, new_ver = parts
                    event = {"name": pkg, "old_version": old_ver, "new_version": new_ver, "date": ts.strftime('%Y-%m-%dT%H:%M:%S')}
                    upgrades.append(event)
                    all_events.append(("upgrade", pkg, ts))
                    session_events.append(("upgrade", pkg, event))
            elif action == 'installed':
                event = {"name": pkg, "version": ver, "date": ts.strftime('%Y-%m-%dT%H:%M:%S')}
                installs.append(event)
                all_events.append(("install", pkg, ts))
                session_events.append(("install", pkg, event))
            elif action == 'removed':
                event = {"name": pkg, "version": ver, "date": ts.strftime('%Y-%m-%dT%H:%M:%S')}
                removes.append(event)
                all_events.append(("remove", pkg, ts))
                session_events.append(("remove", pkg, event))
            elif action == 'downgraded':
                # version looks like "2.0 -> 1.0"
                parts = ver.split(' -> ')
                if len(parts) == 2:
                    old_ver, new_ver = parts
                    event = {"name": pkg, "old_version": old_ver, "new_version": new_ver, "date": ts.strftime('%Y-%m-%dT%H:%M:%S')}
                    upgrades.append(event)  # Treat downgrade like upgrade for tracking
                    all_events.append(("downgrade", pkg, ts))
                    session_events.append(("downgrade", pkg, event))
        
        # Detect genuine silent removes: removes not explicitly requested and not in same transaction
        genuine_silent_removes = []
        for event_type, pkg, event in session_events:
            if event_type == "remove":
                ts_min = event['date'][:16]  # Truncate to minute (YYYY-MM-DDTHH:MM)
                # Check if explicitly removed
                if pkg in explicitly_removed:
                    continue  # User explicitly removed it
                # Check if in same minute-block as explicit remove command
                if ts_min in pacman_remove_timestamps and pkg in pacman_remove_timestamps[ts_min]:
                    continue  # Part of same transaction
                # It's a genuine silent removal - flag it
                genuine_silent_removes.append(event)
        
        summary["silent_removes"] = genuine_silent_removes

        # Get last full system upgrade
        last_upgrade_date = None
        days_since = 0
        for line in reversed(lines):
            if '[ALPM] upgraded' in line and 'system' in line:
                ts_match = re.match(r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})\]', line)
                if ts_match:
                    ts_str = ts_match.group(1)
                    try:
                        # Apply timezone colon-insertion fix
                        ts_str = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', ts_str)
                        last_ts = datetime.fromisoformat(ts_str)
                        last_upgrade_date = last_ts.strftime('%Y-%m-%d')
                        days_since = (datetime.now(timezone.utc) - last_ts).days
                    except:
                        pass
                    break

        summary["days_since_upgrade"] = days_since
        summary["last_upgrade_date"] = last_upgrade_date
        summary["installs"] = installs[-10:]  # Last 10
        summary["upgrades"] = upgrades[-10:]  # Last 10
        summary["removes"] = removes[-10:]    # Last 10

        # Group upgrades into transactions (same [PACMAN] command or within 5 seconds)
        upgrade_transactions = 0
        if upgrades:
            # Sort by timestamp for grouping
            upgrades_sorted = sorted(upgrades, key=lambda e: e['date'])
            current_txn_start = None
            for e in upgrades_sorted:
                ts = datetime.fromisoformat(e['date'])
                if current_txn_start is None:
                    current_txn_start = ts
                    upgrade_transactions += 1
                else:
                    # If more than 5 seconds apart, it's a new transaction
                    if (ts - current_txn_start).total_seconds() > 5:
                        current_txn_start = ts
                        upgrade_transactions += 1

        # Check for installed-then-removed packages
        installed_names = {e["name"] for e in installs}
        removed_names = {e["name"] for e in removes}
        installed_then_removed = installed_names & removed_names

        # Calculate issues
        if days_since > 30:
            summary["issues"] += 1
        summary["issues"] += len(summary["silent_removes"])
        
        # Store raw counts for JSON
        summary["raw_install_count"] = len(installs)
        summary["raw_upgrade_count"] = len(upgrades)
        summary["raw_remove_count"] = len(removes)
        summary["upgrade_transactions"] = upgrade_transactions

        if as_dict:
            if summary["issues"] > 0:
                summary["status"] = "attention"
            return summary

        print_header("Pacman Log Analysis")

        # Debug safeguard: warn if no events found but log has content
        if len(installs) + len(upgrades) + len(removes) == 0 and len(lines) > 100:
            print(f"{CYAN}Note: no ALPM events found in log — log format may differ from expected.{RESET}")

        # Days since last upgrade
        if last_upgrade_date:
            print(f"{BOLD}Days since last full system upgrade:{RESET} {days_since}")
            if days_since > 30:
                print(f"{RED}{BOLD}Warning: System not upgraded in {days_since} days!{RESET}")
                issue_count += 1
                summary["status"] = "attention"
            elif days_since > 14:
                print(f"{YELLOW}Note: System not upgraded in {days_since} days.{RESET}")
        else:
            print(f"{YELLOW}Could not determine last upgrade date.{RESET}")

        # Show recent installs
        if installs:
            print(f"\n{BOLD}Recent installs (last 5):{RESET}")
            for e in installs[-5:]:
                print(f"  {e['date'][:10]}: {e['name']} ({e['version']})")

        # Show recent upgrades
        if upgrades:
            print(f"\n{BOLD}Recent upgrades (last 5):{RESET}")
            for e in upgrades[-5:]:
                print(f"  {e['date'][:10]}: {e['name']} ({e['old_version']} -> {e['new_version']})")

        # Show recent removes
        if removes:
            print(f"\n{BOLD}Recent removes (last 5):{RESET}")
            for e in removes[-5:]:
                print(f"  {e['date'][:10]}: {e['name']} ({e['version']})")

        # Show silent removes
        if summary["silent_removes"]:
            print(f"\n{RED}{BOLD}Potential silent dependency removals:{RESET}")
            for e in summary["silent_removes"]:
                print(f"  {RED}{e['name']}{RESET} ({e['date'][:10]})")
            issue_count += len(summary["silent_removes"])

        # Summary counts - show transactions for upgrades, raw counts for others
        if upgrade_transactions > 0:
            print(f"\n{BOLD}Summary:{RESET} {len(installs)} installs, {upgrade_transactions} upgrade transactions ({len(upgrades)} individual packages), {len(removes)} removes in last {days} days")
        else:
            print(f"\n{BOLD}Summary:{RESET} {len(installs)} installs, {len(upgrades)} upgrades, {len(removes)} removes in last {days} days")

    except Exception as e:
        if as_dict:
            summary["status"] = "error"
            summary["error"] = str(e)
            return summary
        print(f"{RED}Pacman log analysis failed: {e}{RESET}")

# --- Main ---

def main():
    # 1. Setup Parser
    # Use RawDescriptionHelpFormatter to preserve newlines in descriptions
    parser = argparse.ArgumentParser(
        description=f"{CYAN}{BOLD}Arch Linux System Health Utility{RESET}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{BOLD}Run Modes:{RESET}
  arch-check -q               Quick health snapshot (seconds)
  arch-check -a               Full audit (slower, some need root)
  arch-check --security       Security-focused checks only
  arch-check -q --security    Quick + security checks
  arch-check -a --no-journal  Full audit, skip journal scan
  arch-check -j -q            Quick audit as JSON
  arch-check --pacman-log-days 7  Show only last 7 days of log

{BOLD}Extended Descriptions:{RESET}
  {BOLD}--kernel{RESET}   Compares 'uname -r' with the version in the pacman DB.
             If they differ, your system cannot load new modules until reboot.

  {BOLD}--pacnew{RESET}   Scans /etc for .pacnew and .pacsave files. These are created
             when an update has a new default config but you've modified yours.
             Files older than 90 days are flagged as high risk.

  {BOLD}--services{RESET} Queries systemd for any units in a 'failed' state. Useful for
             catching silent background daemon crashes.

  {BOLD}--orphans{RESET}  Lists packages installed as dependencies but no longer required
             by any other package. Helps keep the system lean.

  {BOLD}--disk{RESET}     Analyzes usage for /, /boot, and /home. Specifically tracks
             LVM/LUKS lineage to show you the physical origin of each mount.

  {BOLD}--stats{RESET}     Show pacman package statistics (Native vs AUR)

  {BOLD}--timedatectl{RESET} Check systemd time/date synchronization. Warns if NTP
             is not synchronized or timezone is UTC/empty.

  {BOLD}--load-avg{RESET}  Read /proc/loadavg and compare 15-min average against CPU count.
             Warns if load exceeds 75% or 100% of CPU count.

  {BOLD}--inotify{RESET}   Check inotify watch limit usage. Reads max_user_watches
             and counts current usage (requires root for accurate count).

  {BOLD}--checkupdates{RESET} Run checkupdates (pacman-contrib) to show pending updates.
             Does not flag as issue - just informational.

  {BOLD}--timers{RESET}    List systemd timers and flag those that have never run (n/a).

  {BOLD}--boot-blame{RESET} Run systemd-analyze blame to show slowest boot units.
             Warns if any unit takes >10s or total boot >30s.

  {BOLD}--arch-audit{RESET} Check AUR packages for known CVEs using arch-audit.
             Requires arch-audit package. Flags HIGH severity as issues.

  {BOLD}--journal{RESET}   Check journalctl for errors in last 24h. Groups by unit
             and shows top 10 noisiest units. Slow check.

  {BOLD}--dmesg{RESET}     Check kernel ring buffer for hardware/I/O errors.
             Categorizes by keyword (mce, I/O error, OOM, etc.). Slow check.

  {BOLD}--ports{RESET}     List listening TCP/UDP ports. Flags unexpected listeners
             (not managed by systemd) and externally reachable services.

  {BOLD}--failed-logins{RESET} Check /var/log/btmp for failed login attempts.
             Warns if >10, flags as brute-force if >100. Requires root.

  {BOLD}--aur-stale{RESET}   Check AUR packages for version mismatches. Queries
             aur.archlinux.org RPC API. Flags packages maintainer has marked
             as out of date. Requires network access.

  {BOLD}--pacman-log{RESET}  Parse /var/log/pacman.log for recent changes. Shows
             installs, upgrades, removes. Flags silent dependency removals
             and systems not upgraded in 30+ days. Use --pacman-log-days N
             to adjust lookback window (default: 30).

  {BOLD}--aur-integrity{RESET} Verify AUR package file integrity with pacman -Qk.
             Flags packages with missing or modified files.

  {BOLD}--aur-paths{RESET} Check for AUR packages installing files outside
             standard paths (/usr, /etc, /var, etc.).

  {BOLD}--aur-suid{RESET}  Find setuid/setgid files in AUR packages.
             Whitelists known safe binaries (chrome-sandbox, pmount).

  {BOLD}--aur-pkgbuild{RESET} Scan PKGBUILDs from local cache for suspicious patterns
             (curl|sh, eval, base64 decode, etc.). Fast, no network.
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
    group_aur_int = parser.add_mutually_exclusive_group()
    _ = group_aur_int.add_argument("--aur-integrity", dest="aur_integrity", action="store_true", default=None, help="Check AUR package integrity with pacman -Qk [--no-aur-integrity to suppress]")
    _ = group_aur_int.add_argument("--no-aur-integrity", dest="aur_integrity", action="store_false", default=None, help=argparse.SUPPRESS)
    group_aur_paths = parser.add_mutually_exclusive_group()
    _ = group_aur_paths.add_argument("--aur-paths", dest="aur_paths", action="store_true", default=None, help="Check for non-standard file paths in AUR packages [--no-aur-paths to suppress]")
    _ = group_aur_paths.add_argument("--no-aur-paths", dest="aur_paths", action="store_false", default=None, help=argparse.SUPPRESS)
    group_aur_suid = parser.add_mutually_exclusive_group()
    _ = group_aur_suid.add_argument("--aur-suid", dest="aur_suid", action="store_true", default=None, help="Check for setuid/setgid files in AUR packages [--no-aur-suid to suppress]")
    _ = group_aur_suid.add_argument("--no-aur-suid", dest="aur_suid", action="store_false", default=None, help=argparse.SUPPRESS)
    group_aur_pkgbuild = parser.add_mutually_exclusive_group()
    _ = group_aur_pkgbuild.add_argument("--aur-pkgbuild", dest="aur_pkgbuild", action="store_true", default=None, help="Scan PKGBUILDs for suspicious patterns [--no-aur-pkgbuild to suppress]")
    _ = group_aur_pkgbuild.add_argument("--no-aur-pkgbuild", dest="aur_pkgbuild", action="store_false", default=None, help=argparse.SUPPRESS)

    # Quick group - new checks
    group_timedatectl = parser.add_mutually_exclusive_group()
    _ = group_timedatectl.add_argument("--timedatectl", dest="timedatectl", action="store_true", default=None, help="Check systemd time/date synchronization status [--no-timedatectl to suppress]")
    _ = group_timedatectl.add_argument("--no-timedatectl", dest="timedatectl", action="store_false", default=None, help=argparse.SUPPRESS)
    group_load_avg = parser.add_mutually_exclusive_group()
    _ = group_load_avg.add_argument("--load-avg", dest="load_avg", action="store_true", default=None, help="Check system load average against CPU count [--no-load-avg to suppress]")
    _ = group_load_avg.add_argument("--no-load-avg", dest="load_avg", action="store_false", default=None, help=argparse.SUPPRESS)
    group_inotify = parser.add_mutually_exclusive_group()
    _ = group_inotify.add_argument("--inotify", dest="inotify", action="store_true", default=None, help="Check inotify watch limit usage [--no-inotify to suppress]")
    _ = group_inotify.add_argument("--no-inotify", dest="inotify", action="store_false", default=None, help=argparse.SUPPRESS)
    group_checkupdates = parser.add_mutually_exclusive_group()
    _ = group_checkupdates.add_argument("--checkupdates", dest="checkupdates", action="store_true", default=None, help="Show pending updates from checkupdates [--no-checkupdates to suppress]")
    _ = group_checkupdates.add_argument("--no-checkupdates", dest="checkupdates", action="store_false", default=None, help=argparse.SUPPRESS)
    group_timers = parser.add_mutually_exclusive_group()
    _ = group_timers.add_argument("--timers", dest="timers", action="store_true", default=None, help="Check systemd timer status and missed runs [--no-timers to suppress]")
    _ = group_timers.add_argument("--no-timers", dest="timers", action="store_false", default=None, help=argparse.SUPPRESS)
    group_boot_blame = parser.add_mutually_exclusive_group()
    _ = group_boot_blame.add_argument("--boot-blame", dest="boot_blame", action="store_true", default=None, help="Show systemd boot timing (slowest units) [--no-boot-blame to suppress]")
    _ = group_boot_blame.add_argument("--no-boot-blame", dest="boot_blame", action="store_false", default=None, help=argparse.SUPPRESS)
    group_arch_audit = parser.add_mutually_exclusive_group()
    _ = group_arch_audit.add_argument("--arch-audit", dest="arch_audit", action="store_true", default=None, help="Check AUR packages for known vulnerabilities [--no-arch-audit to suppress]")
    _ = group_arch_audit.add_argument("--no-arch-audit", dest="arch_audit", action="store_false", default=None, help=argparse.SUPPRESS)

    # Slow group
    group_journal = parser.add_mutually_exclusive_group()
    _ = group_journal.add_argument("--journal", dest="journal", action="store_true", default=None, help="Check journal for errors in last 24h [--no-journal to suppress]")
    _ = group_journal.add_argument("--no-journal", dest="journal", action="store_false", default=None, help=argparse.SUPPRESS)
    group_dmesg = parser.add_mutually_exclusive_group()
    _ = group_dmesg.add_argument("--dmesg", dest="dmesg", action="store_true", default=None, help="Check kernel ring buffer for errors [--no-dmesg to suppress]")
    _ = group_dmesg.add_argument("--no-dmesg", dest="dmesg", action="store_false", default=None, help=argparse.SUPPRESS)

    # Security group
    group_ports = parser.add_mutually_exclusive_group()
    _ = group_ports.add_argument("--ports", dest="ports", action="store_true", default=None, help="Check listening ports for unexpected services [--no-ports to suppress]")
    _ = group_ports.add_argument("--no-ports", dest="ports", action="store_false", default=None, help=argparse.SUPPRESS)
    group_failed_logins = parser.add_mutually_exclusive_group()
    _ = group_failed_logins.add_argument("--failed-logins", dest="failed_logins", action="store_true", default=None, help="Check for failed login attempts [--no-failed-logins to suppress]")
    _ = group_failed_logins.add_argument("--no-failed-logins", dest="failed_logins", action="store_false", default=None, help=argparse.SUPPRESS)

    # New checks
    group_aur_stale = parser.add_mutually_exclusive_group()
    _ = group_aur_stale.add_argument("--aur-stale", dest="aur_stale", action="store_true", default=None, help="Check AUR packages for stale versions [--no-aur-stale to suppress]")
    _ = group_aur_stale.add_argument("--no-aur-stale", dest="aur_stale", action="store_false", default=None, help=argparse.SUPPRESS)

    group_pacman_log = parser.add_mutually_exclusive_group()
    _ = group_pacman_log.add_argument("--pacman-log", dest="pacman_log", action="store_true", default=None, help="Analyze pacman.log for recent changes [--no-pacman-log to suppress]")
    _ = group_pacman_log.add_argument("--no-pacman-log", dest="pacman_log", action="store_false", default=None, help=argparse.SUPPRESS)
    _ = parser.add_argument("--pacman-log-days", dest="pacman_log_days", type=int, default=30, help="Days to look back in pacman.log (default: 30)")

    _ = parser.add_argument("-q", "--quick", action="store_true", help="Run quick health checks only (seconds, no root needed)")
    _ = parser.add_argument("-a", "--all", action="store_true", help="Run all health checks (quick + slow + security, some need root)")
    _ = parser.add_argument("--security", action="store_true", help="Run security-focused checks only (can combine with -q or -a)")
    _ = parser.add_argument("-j","--json", action="store_true", help="Output all results in JSON format for further processing")
    _ = parser.add_argument("--log-level", default="WARNING", help="Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    import sys
    color_group = parser.add_mutually_exclusive_group()
    # Default: color if stdout is a terminal, no color if piped
    default_color = sys.stdout.isatty()
    color_group.add_argument('--color', dest='color', action='store_true', default=None, help='Enable colored output (default if terminal)')
    color_group.add_argument('--no-color', dest='color', action='store_false', default=None, help='Disable colored output (default if piped)')

    # Custom help output for compact style
    parser.usage = None
    parser.formatter_class = lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=32)
    
    args = parser.parse_args()
    # Set up logging
    log_level = getattr(logging, str(args.log_level).upper(), logging.WARNING)
    logging.basicConfig(level=log_level, format='[%(levelname)s] %(message)s')
    logger = logging.getLogger(__name__)

    # Determine color: explicit flag wins, else auto-detect
    if args.color is not None:
        use_color = args.color
    else:
        use_color = default_color
    colors = get_colors(use_color)
    globals()['BLUE'] = colors['BLUE']
    globals()['CYAN'] = colors['CYAN']
    globals()['RED'] = colors['RED']
    globals()['GREEN'] = colors['GREEN']
    globals()['YELLOW'] = colors['YELLOW']
    globals()['BOLD'] = colors['BOLD']
    globals()['RESET'] = colors['RESET']
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

    # Determine run mode
    run_mode = "custom"
    if args.all:
        run_mode = "all"
    elif args.quick:
        run_mode = "quick"
    elif args.security:
        run_mode = "security"

    # Helper to determine if a check should run based on group membership
    def should_run(flag, group):
        """Determine if a check runs based on its flag and group membership.
        Individual --no-X always suppresses. --X always enables.
        Group modes enable their members unless suppressed."""
        # --no-X always suppresses
        if flag is False:
            return False
        # --X always enables
        if flag is True:
            return True
        # Default depends on mode and group
        if run_mode == "all":
            return True
        elif run_mode == "quick" and group == "quick":
            return True
        elif run_mode == "security" and group == "security":
            return True
        return False

    # Merge --feature/--no-feature into a single flag for each feature
    # Group membership: quick, slow, security, or none (logo)
    logo_flag = should_run(args.logo, "none")
    sensors_flag = should_run(args.sensors, "quick")
    smart_flag = should_run(args.smart, "quick")
    kernel_flag = should_run(args.kernel, "quick")
    pacnew_flag = should_run(args.pacnew, "quick")
    services_flag = should_run(args.services, "quick")
    orphans_flag = should_run(args.orphans, "quick")
    disk_flag = should_run(args.disk, "quick")
    stats_flag = should_run(args.stats, "quick")
    aur_integrity_flag = should_run(args.aur_integrity, "quick")
    aur_paths_flag = should_run(args.aur_paths, "quick")
    aur_suid_flag = should_run(args.aur_suid, "quick")
    aur_pkgbuild_flag = should_run(args.aur_pkgbuild, "quick")
    journal_flag = should_run(args.journal, "slow")
    dmesg_flag = should_run(args.dmesg, "slow")
    ports_flag = should_run(args.ports, "security")
    failed_logins_flag = should_run(args.failed_logins, "security")
    # Additional quick checks
    timedatectl_flag = should_run(args.timedatectl, "quick")
    load_avg_flag = should_run(args.load_avg, "quick")
    inotify_flag = should_run(args.inotify, "quick")
    checkupdates_flag = should_run(args.checkupdates, "quick")
    timers_flag = should_run(args.timers, "quick")
    boot_blame_flag = should_run(args.boot_blame, "quick")
    arch_audit_flag = should_run(args.arch_audit, "quick")
    aur_stale_flag = should_run(args.aur_stale, "quick")
    pacman_log_flag = should_run(args.pacman_log, "quick")

    import json
    checks = [
        # quick group
        (logo_flag, print_logo_info, 'logo'),
        (sensors_flag, check_sensors, 'sensors'),
        (smart_flag, check_smart, 'smart'),
        (kernel_flag, check_kernel(), 'kernel'),
        (pacnew_flag, check_pacnew, 'pacnew'),
        (services_flag, check_failed_services, 'services'),
        (orphans_flag, check_orphans, 'orphans'),
        (disk_flag, check_disk, 'disk'),
        (stats_flag, check_stats, 'stats'),
        (aur_integrity_flag, check_aur_integrity, 'aur_integrity'),
        (aur_paths_flag, check_aur_paths, 'aur_paths'),
        (aur_suid_flag, check_aur_suid, 'aur_suid'),
        (aur_pkgbuild_flag, check_aur_pkgbuild, 'aur_pkgbuild'),
        (timedatectl_flag, check_timedatectl, 'timedatectl'),
        (load_avg_flag, check_load_avg, 'load_avg'),
        (inotify_flag, check_inotify_limit, 'inotify_limit'),
        (checkupdates_flag, check_checkupdates, 'checkupdates'),
        (timers_flag, check_systemd_timers, 'systemd_timers'),
        (boot_blame_flag, check_systemd_boot_blame, 'systemd_boot_blame'),
        (arch_audit_flag, check_arch_audit, 'arch_audit'),
        (aur_stale_flag, check_aur_stale, 'aur_stale'),
        (pacman_log_flag, check_pacman_log, 'pacman_log'),
        # slow group
        (journal_flag, check_journal_errors, 'journal_errors'),
        (dmesg_flag, check_dmesg_errors, 'dmesg_errors'),
        # security group
        (ports_flag, check_listening_ports, 'listening_ports'),
        (failed_logins_flag, check_failed_logins, 'failed_logins'),
    ]

    enabled = [name for flag, _, name in checks if flag]
    logger.debug(f"[DEBUG] Enabled checks: {enabled}")

    if args.json:
        results = {}
        for selected, func, name in checks:
            if selected:
                # All checks that support as_dict should use it
                if name in ('kernel', 'smart', 'pacnew', 'services', 'orphans', 'stats', 'sensors', 'disk', 'aur_integrity', 'aur_paths', 'aur_suid', 'aur_pkgbuild', 'timedatectl', 'load_avg', 'inotify_limit', 'checkupdates', 'systemd_timers', 'systemd_boot_blame', 'arch_audit', 'aur_stale', 'pacman_log', 'journal_errors', 'dmesg_errors', 'listening_ports', 'failed_logins'):
                    # check_sensors needs temp_warn default
                    if name == 'sensors':
                        results[name] = func(as_dict=True)
                    elif name == 'pacman_log':
                        results[name] = func(as_dict=True, days=args.pacman_log_days)
                    else:
                        results[name] = func(as_dict=True)
                else:
                    results[name] = None
        # Add summary with per-section issues
        issues_by_section = {k: (v.get('issues', 0) if isinstance(v, dict) else 0) for k, v in results.items() if k != 'summary'}
        results['summary'] = {
            'issues': sum(issues_by_section.values()),
            'issues_by_section': issues_by_section,
            'status': 'ok' if all((v.get('status', 'ok') == 'ok' if isinstance(v, dict) else True) for v in results.values() if v) else 'attention',
        }
        print(json.dumps(results, indent=2))
    else:
        # Track skipped checks
        skipped_checks = []
        ran_checks = []

        for selected, func, name in checks:
            if selected:
                result = func()
                # Check if this check was skipped
                if isinstance(result, dict) and result.get('status') == 'skipped':
                    skipped_checks.append(name)
                else:
                    ran_checks.append(name)

        print_header("Summary")
        print(f"{BOLD}Run mode:{RESET} {run_mode}")

        # Collect per-section issues for enabled checks
        issues_by_section = {}
        skipped_section = []
        error_section = []
        for selected, func, name in checks:
            if selected and name in ('kernel', 'smart', 'pacnew', 'services', 'orphans', 'stats', 'sensors', 'disk', 'aur_integrity', 'aur_paths', 'aur_suid', 'aur_pkgbuild', 'timedatectl', 'load_avg', 'inotify_limit', 'checkupdates', 'systemd_timers', 'systemd_boot_blame', 'arch_audit', 'aur_stale', 'pacman_log', 'journal_errors', 'dmesg_errors', 'listening_ports', 'failed_logins'):
                try:
                    if name == 'sensors':
                        result = func(as_dict=True)
                    elif name == 'pacman_log':
                        result = func(as_dict=True, days=args.pacman_log_days)
                    else:
                        result = func(as_dict=True)
                    status = result.get('status', 'ok') if isinstance(result, dict) else 'ok'
                    if status == 'skipped':
                        skipped_section.append(name)
                    elif status == 'error':
                        error_section.append(name)
                    else:
                        issues_by_section[name] = result.get('issues', 0) if isinstance(result, dict) else 0
                except Exception:
                    error_section.append(name)

        print(f"\n{BOLD}Issues by section:{RESET}")
        for section, count in issues_by_section.items():
            color = GREEN if count == 0 else RED
            print(f"  {color}{section}: {count}{RESET}")

        if error_section:
            print(f"\n{BOLD}Errors (check failed):{RESET}")
            for section in error_section:
                print(f"  {RED}{section}{RESET}")

        if skipped_section:
            print(f"\n{BOLD}Skipped (binary not installed):{RESET}")
            for section in skipped_section:
                print(f"  {CYAN}{section}{RESET}")

        print("")
        if issue_count == 0 and not skipped_section:
            print(f"{GREEN}{BOLD}✔ System Healthy: No issues detected.{RESET}")
        elif issue_count == 0:
            print(f"{GREEN}{BOLD}✔ System Healthy: No issues detected ({len(skipped_section)} check(s) skipped).{RESET}")
        else:
            print(f"{RED}{BOLD}✘ Attention Required: {issue_count} potential issue(s) found.{RESET}")
        print("")


if __name__ == "__main__":
    main()
