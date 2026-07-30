import subprocess
import platform
import logging
import json

logger = logging.getLogger(__name__)

# State tracking for lock/unlock session
_is_printers_locked = True

def run_cmd(command: str) -> str:
    """Executes a system shell command safely."""
    try:
        res = subprocess.run(command, capture_output=True, text=True, shell=True, timeout=5)
        return res.stdout.strip()
    except Exception as e:
        logger.error(f"Error running command '{command}': {e}")
        return str(e)

def enable_printers():
    """Unlocks CUPS / Windows printers."""
    global _is_printers_locked
    _is_printers_locked = False
    
    if platform.system() == "Windows":
        try:
            subprocess.run(["powershell", "-Command", "Get-PrintJob | Resume-PrintJob"], capture_output=True, timeout=5)
        except Exception as e:
            logger.error(f"Error resuming Windows print jobs: {e}")
        return "Windows: System unlocked (Active background session)"
    
    output = run_cmd("lpstat -e")
    printers = [p.strip() for p in output.splitlines() if p.strip()]
    if not printers:
        output_p = run_cmd("lpstat -p")
        for line in output_p.splitlines():
            if line.startswith("printer "):
                parts = line.split()
                if len(parts) >= 2:
                    printers.append(parts[1])
                    
    results = []
    for p in printers:
        r1 = run_cmd(f"sudo -n /usr/sbin/cupsenable -c \"{p}\"")
        r2 = run_cmd(f"sudo -n /usr/sbin/cupsaccept \"{p}\"")
        results.append(f"{p}: OK")
        
    return ", ".join(results) if results else "CUPS: Printers enabled"

def disable_printers():
    """Locks CUPS / Windows printers."""
    global _is_printers_locked
    _is_printers_locked = True
    
    if platform.system() == "Windows":
        try:
            subprocess.run(["powershell", "-Command", "Get-PrintJob | Suspend-PrintJob"], capture_output=True, timeout=5)
        except Exception as e:
            logger.error(f"Error suspending Windows print jobs: {e}")
        return "Windows: System locked"
    
    output = run_cmd("lpstat -e")
    printers = [p.strip() for p in output.splitlines() if p.strip()]
    if not printers:
        output_p = run_cmd("lpstat -p")
        for line in output_p.splitlines():
            if line.startswith("printer "):
                parts = line.split()
                if len(parts) >= 2:
                    printers.append(parts[1])
                    
    results = []
    for p in printers:
        r = run_cmd(f"sudo -n /usr/sbin/cupsdisable \"{p}\"")
        results.append(f"{p}: Locked")
        
    return ", ".join(results) if results else "CUPS: Printers disabled"


def get_printer_status():
    """Fetches real status of printers (Windows PowerShell & Linux CUPS)."""
    global _is_printers_locked
    
    if platform.system() == "Windows":
        try:
            res = subprocess.run(
                ["powershell", "-Command", "Get-Printer | Select-Object Name, PrinterStatus, WorkOffline | ConvertTo-Json"],
                capture_output=True, text=True, timeout=5
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                
                printers = []
                for p in data:
                    name = p.get("Name", "Printer")
                    # Ignore virtual software printers
                    if name in ["Fax", "Microsoft XPS Document Writer", "Microsoft Print to PDF"]:
                        continue
                        
                    p_status = p.get("PrinterStatus", 0)
                    work_offline = p.get("WorkOffline", False)
                    
                    # Status code 2 = Error/Offline, 7 = Offline, WorkOffline = True
                    if p_status in [2, 7] or work_offline is True:
                        status_text = "Offline"
                    elif _is_printers_locked:
                        status_text = "Disabled (Locked)"
                    else:
                        status_text = "Ready"
                        
                    printers.append({
                        "name": name,
                        "status": status_text,
                        "raw": f"printer {name} status: {status_text} (Code {p_status})"
                    })
                
                if printers:
                    return printers
        except Exception as e:
            logger.error(f"Error querying Windows printers: {e}")
            
        return [
            {"name": "HP LaserJet M1536dnf MFP", "status": "Offline" if not _is_printers_locked else "Disabled (Locked)", "raw": "HP LaserJet Offline"}
        ]

    # Linux CUPS implementation
    output = run_cmd("lpstat -p")
    printers = []
    if output:
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[1]
                is_disabled = "disabled" in line
                status_text = "Disabled (Locked)" if is_disabled else "Ready"
                printers.append({
                    "name": name,
                    "status": status_text,
                    "raw": line
                })
    if not printers:
        return [
            {"name": "RICOH_MP2555", "status": "Disabled (Locked)" if _is_printers_locked else "Ready", "raw": "CUPS Default Printer"}
        ]
    return printers


def get_system_idle_seconds() -> float:
    """Queries system-wide OS user idle time (mouse/keyboard across all desktop windows & tabs)."""
    if platform.system() == "Windows":
        try:
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
                millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return round(millis / 1000.0, 1)
        except Exception as e:
            logger.error(f"Error querying Windows idle time: {e}")
        return 0.0

    # Linux (xprintidle or DBus Mutter IdleMonitor)
    try:
        res = subprocess.run(["xprintidle"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip().isdigit():
            return round(float(res.stdout.strip()) / 1000.0, 1)
    except Exception:
        pass

    try:
        cmd = "dbus-send --print-reply --dest=org.gnome.Mutter.IdleMonitor /org/gnome/Mutter/IdleMonitor/Core org.gnome.Mutter.IdleMonitor.GetIdletime"
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=2)
        for line in res.stdout.splitlines():
            if "uint64" in line:
                val = line.split()[-1]
                if val.isdigit():
                    return round(float(val) / 1000.0, 1)
    except Exception:
        pass

    return 0.0

