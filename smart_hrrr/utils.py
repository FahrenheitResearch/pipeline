import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List


def parse_hour_range(range_str: Optional[str]) -> Optional[List[int]]:
    """Parse forecast hour range string into a list of ints."""
    if not range_str:
        return None
    if "-" in range_str:
        start, end = map(int, range_str.split("-"))
        return list(range(start, end + 1))
    return [int(h) for h in range_str.split(",") if h]


def setup_logging(debug: bool = False, output_dir: Optional[Path] = None) -> logging.Logger:
    """Setup logging with organized output"""
    log_level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    if output_dir:
        log_dir = Path(output_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"processing_{timestamp}.log"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = Path(f"smart_hrrr_{timestamp}.log")

    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    ch.setLevel(log_level)

    logging.basicConfig(level=logging.DEBUG, handlers=[fh, ch])
    
    # Reduce cfgrib noise
    logging.getLogger('cfgrib').setLevel(logging.WARNING)
    logging.getLogger('cfgrib.dataset').setLevel(logging.WARNING)
    logging.getLogger('cfgrib.messages').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Smart HRRR processor initialized. Log: {log_file}")
    return logger


def check_system_memory():
    """Check system memory usage"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            "total_mb": memory.total / 1024 / 1024,
            "available_mb": memory.available / 1024 / 1024,
            "used_mb": memory.used / 1024 / 1024,
            "percent": memory.percent,
        }
    except Exception:
        return None