def check_smart():
    """Check SMART health for all disks using smartctl. Warn if any disk is failing."""
    global issue_count
    print_header("SMART Disk Health Summary")
    try:
        # List all /dev/sd[a-z] and /dev/nvme*n1 devices
        import glob
        devs = glob.glob('/dev/sd?') + glob.glob('/dev/nvme*n1')
        if not devs:
            print(f"{YELLOW}No disks found for SMART check.{RESET}")
            return
        for dev in devs:
            try:
                out = subprocess.check_output(["smartctl", "-H", dev], text=True, stderr=subprocess.STDOUT)
                if "PASSED" in out:
                    print(f"{GREEN}{dev}: PASSED{RESET}")
                else:
                    print(f"{RED}{dev}: {out.strip()}{RESET}")
                    issue_count += 1
                # Optionally print some attributes
                attr = subprocess.check_output(["smartctl", "-A", dev], text=True, stderr=subprocess.STDOUT)
                for line in attr.splitlines():
                    if any(x in line for x in ["Reallocated_Sector_Ct", "Power_On_Hours", "Temperature_Celsius", "Media_Wearout_Indicator"]):
                        print(f"  {line.strip()}")
            except subprocess.CalledProcessError as e:
                print(f"{YELLOW}{dev}: SMART not available or permission denied.{RESET}")
            except Exception as e:
                print(f"{RED}{dev}: SMART check failed: {e}{RESET}")
    except FileNotFoundError:
        print(f"{YELLOW}smartctl command not found. Please install smartmontools.{RESET}")
    except Exception as e:
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

# The high-detail ASCII logo provided
ARCH_LOGO = [
f"{CYAN}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣷⣤⣙⢻⣿⣿⣿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡄⠀⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⡿⠛⠛⠿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠙⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⠀⣰⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⠿⣆⠀⠀⠀⠀{RESET}",
f"{CYAN}⠀⠀⠀⣴⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣷⣦⡀⠀⠀⠀{RESET}",
f"{CYAN}⠀⢀⣾⣿⣿⠿⠟⠛⠋⠉⠉⠀⠀⠀⠀⠀⠀⠉⠉⠙⠛⠻⠿⣿⣿⣷⡀⠀{RESET}",
f"{CYAN}⣠⠟⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⣄{RESET}",
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

def check_sensors(temp_warn: int = 80):
    """Check and print all available sensor temperatures. Warn if any exceed temp_warn (Celsius)."""
    global issue_count
    print_header("Temperature & Sensors")
    try:
        out = subprocess.check_output(["sensors"], text=True)
        lines = out.splitlines()
        high_found = False
        for line in lines:
            if "temp" in line.lower() or "core" in line.lower() or "Package id" in line:
                # Try to extract temperature value
                import re
                match = re.search(r'([+-]?[0-9]+\.[0-9])°C', line)
                if match:
                    temp = float(match.group(1))
                    color = RED if temp >= temp_warn else (YELLOW if temp >= temp_warn-10 else GREEN)
                    print(f"{color}{line.strip()}{RESET}")
                    if temp >= temp_warn:
                        high_found = True
        if high_found:
            print(f"{RED}{BOLD}Warning: High temperature detected!{RESET}")
            issue_count += 1
        if not lines:
            print(f"{YELLOW}No sensor data found. Is lm_sensors installed and configured?{RESET}")
    except FileNotFoundError:
        print(f"{YELLOW}sensors command not found. Please install lm_sensors.{RESET}")
    except Exception as e:
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
    print(f"{BOLD}{'Mount':<10} : {'Usage':<8} : {'Free':<10} : {'FS':<8} : {'Type':<10} : {'Device':<22} : {'Origin'}{RESET}")
    print("─" * 120)

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
        return ([], None)

    for mount in critical_mounts:
        if mount not in mount_data:
            print(f"{mount:<10} : {YELLOW}Not mounted{RESET}")
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
            if not chain or not dev_entry or "name" not in dev_entry:
                print(f"{mount:<10} : {RED}No device info found for mountpoint{RESET}")
                continue
            device = f"/dev/{dev_entry['name']}"
            fstype = dev_entry.get('fstype', 'unknown')
            dtype = dev_entry.get('type', 'unknown')
            origin = '.'.join(chain) if chain else dev_entry.get('name', 'unknown')

            print(f"{mount:<10} : {color}{percent:>6.1f}%{RESET} : {free/(2**30):>7.2f} GB : {fstype:<8} : {dtype:<10} : {device:<22} : {origin}")
        except Exception as e:
            print(f"{mount:<10} : {RED}Error: {e}{RESET}")

def check_kernel():
    global issue_count
    print_header("Kernel Version Check")
    try:
        pac_out = subprocess.check_output(["pacman", "-Qi", "linux"], text=True)
        installed = next(l.split(":")[1].strip() for l in pac_out.splitlines() if l.startswith("Version"))
        running = subprocess.check_output(["uname", "-r"], text=True).strip()
        p_v, r_v = installed.replace('-', '.').split('.'), running.replace('-', '.').split('.')
        mismatch = False
        print(f"{'Component':<12} : {'Installed':<12} : {'Running'}")
        print("─" * 45)
        for lbl, p, r in zip(['Major', 'Minor', 'Patch', 'Arch Rel'], p_v, r_v):
            if p != r: mismatch = True
            print(f"{GREEN if p==r else RED}{lbl:<12} : {p:<12} {'==' if p==r else '!='} {r}{RESET}")
        if mismatch:
            issue_count += 1
            print(f"\n{RED}{BOLD}![REBOOT REQUIRED]: Running kernel mismatch.{RESET}")
    except: print(f"{RED}Kernel check failed.{RESET}")

def check_pacnew():
    global issue_count
    print_header("Config Files (.pacnew)")
    found = [os.path.join(r, f) for r, _, fs in os.walk('/etc') for f in fs if f.endswith(('.pacnew', '.pacsave'))]
    if found:
        issue_count += len(found)
        for f in found: print(f"{YELLOW}  -> {f}{RESET}")
    else: print(f"{GREEN}No pending merges.{RESET}")

def check_failed_services():
    global issue_count
    print_header("Failed Services")
    try:
        out = subprocess.check_output(["systemctl", "list-units", "--state=failed", "--plain", "--no-legend"], text=True).strip()
        if out:
            lines = out.splitlines()
            issue_count += len(lines)
            for line in lines: print(f"{RED}  -> {line.split()[0]}{RESET}")
        else: print(f"{GREEN}All units OK.{RESET}")
    except: pass

def check_orphans():
    print_header("Orphaned Packages")
    try:
        out = subprocess.check_output(["pacman", "-Qdtq"], text=True).strip()
        if out: print(f"{YELLOW}Orphans: {out.replace(chr(10), ', ')}{RESET}")
        else: print(f"{GREEN}No orphans.{RESET}")
    except: print(f"{GREEN}No orphans.{RESET}")

def check_stats():
    print_header("Pacman Statistics")
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
            # Using du -sh is the easiest way to get human-readable directory size
            try:
                cache_out = subprocess.check_output(["du", "-sh", cache_path], text=True).split()[0]
                cache_size_str = cache_out
            except: pass

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

    _ = parser.add_argument("-l", "--logo", action="store_true", help="Print the Arch logo and hardware summary")
    _ = parser.add_argument("--sensors", action="store_true", help="Show all available temperature sensors and warn if high")
    _ = parser.add_argument("-k", "--kernel", action="store_true", help="Check for kernel/running version mismatch")
    _ = parser.add_argument("-p", "--pacnew", action="store_true", help="Scan for unmerged .pacnew config files")
    _ = parser.add_argument("-s", "--services", action="store_true", help="List failed systemd services")
    _ = parser.add_argument("-o", "--orphans", action="store_true", help="List orphaned packages (unused dependencies)")
    _ = parser.add_argument("-d", "--disk", action="store_true", help="Show usage, filesystem type, and LVM/LUKS origin")
    _ = parser.add_argument("-a", "--all", action="store_true", help="Perform all health checks and show logo")
    _ = parser.add_argument("-t", "--stats", action="store_true", help="Show pacman package statistics (Native vs AUR)")
    _ = parser.add_argument("--smart", action="store_true", help="Show SMART disk health summary (if supported)")

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


    checks = [
        (getattr(args, 'logo', False), print_logo_info),
        (getattr(args, 'sensors', False), check_sensors),
        (getattr(args, 'smart', False), check_smart),
        (getattr(args, 'kernel', False), check_kernel),
        (getattr(args, 'pacnew', False), check_pacnew),
        (getattr(args, 'services', False), check_failed_services),
        (getattr(args, 'orphans', False), check_orphans),
        (getattr(args, 'disk', False), check_disk),
        (getattr(args, 'stats', False), check_stats),
    ]


    for selected, func in checks:
        if getattr(args, 'all', False) or selected:
            func()

    print_header("Summary")
    if issue_count == 0:
        print(f"{GREEN}{BOLD}✔ System Healthy: No issues detected.{RESET}")
    else:
        print(f"{RED}{BOLD}✘ Attention Required: {issue_count} potential issue(s) found.{RESET}")
    print("")


if __name__ == "__main__":
    main()
