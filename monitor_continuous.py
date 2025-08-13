#!/usr/bin/env python3
"""
Fixed continuous HRRR monitor - addresses all known issues:
1. Proper cycle timing (data arrives 15-45 min after hour)
2. Checks correct nested directory structure
3. No reprocessing of completed hours
4. 10 second polling to NOMADS
5. Checks F00/F01 availability to detect new cycles
"""

import subprocess
import time
import sys
import os
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging

# Set up clean logging
logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_expected_max_forecast_hour(hour):
    """Get expected max forecast hour for a given cycle hour"""
    if hour in [0, 6, 12, 18]:
        return 48
    else:
        return 18

def check_forecast_hour_complete(cycle, fhr):
    """Check if a specific forecast hour is complete (has ~90-99 products)"""
    cycle_date = cycle[:8]
    cycle_hour = cycle[8:]
    
    # Check the correct nested structure: outputs/hrrr/YYYYMMDD/HHz/FXX/conus/FXX/category/*.png
    fhr_dir = Path(f"outputs/hrrr/{cycle_date}/{cycle_hour}z/F{fhr:02d}/conus/F{fhr:02d}")
    
    if not fhr_dir.exists():
        return False, 0
    
    # Count PNG files across all category subdirectories
    png_count = len(list(fhr_dir.glob("*/*_REFACTORED.png")))
    
    # Consider complete if has 90+ products (accounting for some variation)
    return png_count >= 90, png_count

def get_cycle_status(cycle):
    """Get detailed status of all forecast hours in a cycle"""
    hour = int(cycle[8:])
    max_fhr = get_expected_max_forecast_hour(hour)
    
    completed = []
    incomplete = []
    
    for fhr in range(max_fhr + 1):
        is_complete, count = check_forecast_hour_complete(cycle, fhr)
        if is_complete:
            completed.append(fhr)
        else:
            incomplete.append(fhr)
    
    return completed, incomplete, max_fhr

def check_nomads_availability(cycle, fhr):
    """Check if a forecast hour is available on NOMADS"""
    base_url = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod"
    date_str = cycle[:8]
    hour_str = cycle[8:]
    
    # Check for conus surface file
    surface_url = f"{base_url}/hrrr.{date_str}/conus/hrrr.t{hour_str}z.wrfsfcf{fhr:02d}.grib2.idx"
    
    try:
        response = requests.head(surface_url, timeout=5)
        return response.status_code == 200
    except:
        return False

def get_proper_cycle_to_process():
    """Determine which cycle to process based on current time and data availability"""
    now_utc = datetime.now(timezone.utc)
    current_minute = now_utc.minute
    current_hour = now_utc.hour
    
    # Always try current hour first - data can arrive as early as :35
    cycle_time = now_utc.replace(minute=0, second=0, microsecond=0)
    cycle_str = cycle_time.strftime("%Y%m%d%H")
    
    # Check if F00 is available (indicates cycle has started uploading)
    if check_nomads_availability(cycle_str, 0):
        return cycle_str
    
    # Check previous hour
    prev_cycle_time = cycle_time - timedelta(hours=1)
    prev_hour = prev_cycle_time.hour
    
    # If previous hour was a 6-hour cycle (00z, 06z, 12z, 18z), it might still be processing
    # These cycles go to F48 instead of F18, so they take longer
    if prev_hour in [0, 6, 12, 18]:
        # For 6-hour cycles, be more conservative about switching
        # Don't switch until :48 or when new cycle is actually available
        if current_minute < 48:
            return prev_cycle_time.strftime("%Y%m%d%H")
    else:
        # For regular cycles (F18 max), can switch earlier at :35
        if current_minute < 35:
            return prev_cycle_time.strftime("%Y%m%d%H")
    
    # After the cutoff time, still return previous as fallback
    # but main loop will aggressively check for new cycle
    return prev_cycle_time.strftime("%Y%m%d%H")

def run_processor_for_hours(cycle, forecast_hours):
    """Run processor for specific forecast hours only"""
    if not forecast_hours:
        return True
        
    # Build hour list string
    hour_list = ",".join(str(h) for h in sorted(forecast_hours))
    
    logger.info(f"🚀 Processing F{hour_list} for cycle {cycle}")
    
    cmd = [
        'python', 'processor_cli.py',
        cycle[:8],  # date
        cycle[8:],  # hour
        '--hours', hour_list,
        '--model', 'hrrr'
    ]
    
    # Enable parallel processing for speed
    os.environ['HRRR_USE_PARALLEL'] = 'true'
    
    logger.info(f"🔧 Running command: {' '.join(cmd)}")
    
    # Don't redirect stderr in debug mode
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Capture stderr instead of hiding it
            text=True,
            bufsize=1
        )
        
        # Read both stdout and stderr
        import threading
        
        def read_stdout():
            for line in process.stdout:
                line = line.strip()
                # Show important lines
                if line and any(keyword in line for keyword in [
                    'Processing', 'Downloading', 'completed', 'ERROR', 'Failed', 
                    '✅', '❌', '📥', '⬇️', 'NOMADS', 'AWS', 'Phase'
                ]):
                    logger.info(f"  {line}")
        
        def read_stderr():
            for line in process.stderr:
                line = line.strip()
                if line and not line.startswith("DEBUG:cfgrib"):  # Skip cfgrib debug
                    logger.info(f"  [STDERR] {line}")
        
        # Start threads to read both streams
        stdout_thread = threading.Thread(target=read_stdout)
        stderr_thread = threading.Thread(target=read_stderr)
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process to complete
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
        
        return process.returncode == 0
        
    except Exception as e:
        logger.error(f"Error running processor: {e}")
        return False

def main():
    """Main monitoring loop"""
    print("="*60)
    print("FIXED CONTINUOUS HRRR MONITORING")
    print("="*60)
    print("Features:")
    print("- Proper cycle timing (waits for data availability)")
    print("- No reprocessing of completed hours")
    print("- 10 second polling interval")
    print("- Clean output without cfgrib spam")
    print("- Continues previous cycle if new one isn't ready")
    print("\nPress Ctrl+C to stop")
    print("="*60)
    
    last_complete_cycle = None
    currently_processing_cycle = None
    
    try:
        while True:
            # Determine which cycle to process
            available_cycle = get_proper_cycle_to_process()
            
            # Check if we should switch to a new cycle
            if currently_processing_cycle and available_cycle != currently_processing_cycle:
                # Check if new cycle is really available (not just a fallback)
                if check_nomads_availability(available_cycle, 0):
                    logger.info(f"\n🆕 Switching to new cycle {available_cycle} (was processing {currently_processing_cycle})")
                    currently_processing_cycle = available_cycle
                # Otherwise keep processing current cycle
            elif not currently_processing_cycle:
                currently_processing_cycle = available_cycle
            
            # Get current status of the cycle we're actually processing
            completed, incomplete, max_fhr = get_cycle_status(currently_processing_cycle)
            
            # Show status
            now_str = datetime.now().strftime("%H:%M:%S")
            if incomplete:
                logger.info(f"\nCycle {currently_processing_cycle}: {len(completed)}/{max_fhr+1} complete")
                
                if completed:
                    # Show completed ranges
                    ranges = []
                    i = 0
                    while i < len(completed):
                        start = completed[i]
                        end = start
                        while i + 1 < len(completed) and completed[i + 1] == completed[i] + 1:
                            i += 1
                            end = completed[i]
                        if start == end:
                            ranges.append(f"F{start:02d}")
                        else:
                            ranges.append(f"F{start:02d}-F{end:02d}")
                        i += 1
                    logger.info(f"  Complete: {', '.join(ranges)}")
                
                # Process only incomplete hours
                hours_to_process = []
                for fhr in incomplete:
                    # Check NOMADS availability before attempting
                    if check_nomads_availability(currently_processing_cycle, fhr):
                        hours_to_process.append(fhr)
                    else:
                        break  # Stop at first unavailable hour
                
                if hours_to_process:
                    run_processor_for_hours(currently_processing_cycle, hours_to_process)
                else:
                    logger.info("  No new data available yet")
                    
            else:
                # Cycle complete
                if last_complete_cycle != currently_processing_cycle:
                    logger.info(f"\n✅ Cycle {currently_processing_cycle} COMPLETE (F00-F{max_fhr:02d})")
                    last_complete_cycle = currently_processing_cycle
                
                # Check if a new cycle might be available now
                available_cycle = get_proper_cycle_to_process()
                if available_cycle != currently_processing_cycle and check_nomads_availability(available_cycle, 0):
                    logger.info(f"\n🆕 New cycle {available_cycle} is now available!")
                    continue  # Jump to processing new cycle
                
                # Show brief waiting message
                now_utc = datetime.now(timezone.utc)
                prev_hour = int(currently_processing_cycle[8:])
                
                # Different timing for 6-hour vs regular cycles
                if prev_hour in [0, 6, 12, 18]:
                    # This was a 6-hour cycle (F48)
                    if now_utc.minute < 48:
                        mins_to_check = 48 - now_utc.minute
                        logger.info(f"⏰ 6-hour cycle complete. Will check for new cycle in ~{mins_to_check} min")
                    else:
                        logger.info(f"⏰ Checking for new cycle (6-hour cycles can run until :48)")
                else:
                    # Regular cycle (F18)
                    if now_utc.minute < 35:
                        mins_to_check = 35 - now_utc.minute
                        logger.info(f"⏰ Will start checking for new cycle in ~{mins_to_check} min")
                    else:
                        logger.info(f"⏰ Checking for new cycle (data can arrive :35-:45)")
            
            # Fixed 10 second polling interval
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()