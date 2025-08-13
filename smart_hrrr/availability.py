from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import urllib.request


def check_cycle_availability(cycle: str, model: str = "hrrr") -> bool:
    """Check if a cycle is available by testing F00 file"""
    try:
        from model_config import get_model_registry
        
        reg = get_model_registry()
        model_cfg = reg.get_model(model.lower())
        
        if not model_cfg:
            return False
        
        cycle_dt = datetime.strptime(cycle, "%Y%m%d%H")
        date_str = cycle_dt.strftime("%Y%m%d")
        cycle_hour = int(cycle[-2:])
        
        urls = model_cfg.get_download_urls(date_str, cycle_hour, 'pressure', 0)
        if not urls:
            return False
        
        req = urllib.request.Request(urls[0])
        req.get_method = lambda: "HEAD"
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.getcode() == 200
    except Exception:
        return False


def get_latest_cycle(model: str = "hrrr") -> Tuple[Optional[str], Optional[datetime]]:
    """Get the most recent model cycle that should be available"""
    now = datetime.utcnow()
    
    try:
        from model_config import get_model_registry
        reg = get_model_registry()
        model_cfg = reg.get_model(model.lower())
    except Exception:
        model_cfg = None

    for back in range(0, 12):
        t = now - timedelta(hours=back)
        cyc = t.strftime("%Y%m%d%H")
        
        if model_cfg and hasattr(model_cfg, "forecast_cycles"):
            if t.hour not in model_cfg.forecast_cycles:
                continue
        
        if check_cycle_availability(cyc, model):
            return cyc, t

    fallback = now - timedelta(hours=6)
    return fallback.strftime("%Y%m%d%H"), fallback


def get_expected_max_forecast_hour(cycle: str) -> int:
    """Get expected maximum forecast hour for this cycle"""
    hour = int(cycle[-2:])
    return 48 if hour in (0, 6, 12, 18) else 18


def check_forecast_hour_availability(cycle: str, forecast_hour: int, file_types: List[str] = ["wrfprs", "wrfsfc"]) -> List[str]:
    """Check if specific forecast hour is available"""
    cycle_dt = datetime.strptime(cycle, "%Y%m%d%H")
    date_str = cycle_dt.strftime("%Y%m%d")
    hr = cycle[-2:]

    ok: List[str] = []
    for ft in file_types:
        filename = f"hrrr.t{hr}z.{ft}f{forecast_hour:02d}.grib2"
        url = f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod/hrrr.{date_str}/conus/{filename}"
        
        try:
            req = urllib.request.Request(url)
            req.get_method = lambda: "HEAD"
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.getcode() == 200:
                ok.append(ft)
        except Exception:
            continue
            
    return ok