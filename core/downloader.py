"""Weather model file downloader module"""

import urllib.request
import urllib.error
import socket
from datetime import datetime


def download_model_file(cycle, forecast_hour, output_dir, file_type, model_config):
    """Download weather model file with appropriate source fallbacks
    
    Args:
        cycle: Model cycle (YYYYMMDDHH)
        forecast_hour: Forecast hour
        output_dir: Output directory
        file_type: Generic file type ('pressure', 'surface', 'native')
        model_config: Model configuration object
    """
    cycle_dt = datetime.strptime(cycle, '%Y%m%d%H')
    date_str = cycle_dt.strftime('%Y%m%d')
    cycle_hour = int(cycle[-2:])
    
    # Get filename from model config
    filename = model_config.get_filename(cycle_hour, file_type, forecast_hour)
    output_path = output_dir / filename
    
    if output_path.exists():
        print(f"File exists: {filename}")
        return output_path
    
    # Get download URLs from model config
    urls = model_config.get_download_urls(date_str, cycle_hour, file_type, forecast_hour)
    
    for i, url in enumerate(urls):
        try:
            source_name = f"Source {i+1}"
            if "nomads" in url.lower():
                source_name = "NOMADS"
            elif "s3.amazonaws.com" in url.lower() or "noaa-" in url:
                source_name = "AWS S3"
            elif "pando" in url.lower():
                source_name = "Utah Pando"
            
            print(f"⬇️ Downloading {filename} from {source_name}...")
            
            # Set longer timeout for large files
            socket.setdefaulttimeout(600)  # 10 minutes
            
            urllib.request.urlretrieve(url, output_path)
            print(f"✅ Downloaded from {source_name}: {filename}")
            return output_path
        except urllib.error.URLError as e:
            if i < len(urls) - 1:
                print(f"⚠️ {source_name} failed ({e}), trying next source...")
            else:
                print(f"❌ {source_name} also failed ({e})")
            continue
    
    print(f"❌ Failed to download {filename} from all sources")
    return None


def download_hrrr_file(cycle, forecast_hour, output_dir, file_type, model_config):
    """Legacy method for backward compatibility - redirects to download_model_file"""
    # Map old HRRR file types to generic types
    type_map = {
        'wrfprs': 'pressure',
        'wrfsfc': 'surface',
        'wrfnat': 'native'
    }
    generic_type = type_map.get(file_type, 'pressure')
    return download_model_file(cycle, forecast_hour, output_dir, generic_type, model_config)