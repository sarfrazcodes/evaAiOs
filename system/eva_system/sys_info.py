import platform
import psutil

def get_system_info():
    """Returns basic system information as a dictionary."""
    try:
        os_release = platform.freedesktop_os_release()
        os_info = os_release.get("PRETTY_NAME", platform.system() + " " + platform.release())
    except Exception:
        os_info = platform.system() + " " + platform.release()

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    cpu_name = platform.processor()
    if not cpu_name:
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        cpu_name = line.split(':')[1].strip()
                        break
        except Exception:
            cpu_name = "Unknown CPU"

    return {
        "hostname": platform.node(),
        "os": os_info,
        "cpu": cpu_name,
        "cpu_cores": psutil.cpu_count(logical=True),
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "ram_used_gb": round(ram.used / (1024**3), 2),
        "ram_percent": ram.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": disk.percent,
    }
