#!/usr/bin/env python3
"""
HRRR GIF Maker
Creates animated GIFs from HRRR forecast hour images
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image
import re


def find_matching_files(sample_file, max_hours=48, base_dir='.'):
    """
    Find all files matching the pattern of the sample file across forecast hours.
    
    Args:
        sample_file: Path to a sample file (e.g., sbcape_f00_REFACTORED.png)
        max_hours: Maximum forecast hours to include
        base_dir: Base directory for outputs
        
    Returns:
        List of (forecast_hour, file_path) tuples sorted by forecast hour
    """
    sample_path = Path(sample_file)
    
    # Extract parameter name and forecast hour from filename
    filename = sample_path.name
    match = re.match(r'(.+)_f(\d+)_REFACTORED\.png', filename)
    
    if not match:
        print(f"❌ Invalid filename format: {filename}")
        return []
    
    param_name = match.group(1)
    
    # Get the base directory structure
    # Handle different directory structures (with/without conus)
    parts = sample_path.parts
    
    # Find the model run directory (e.g., /outputs/hrrr/20250716/03z/)
    run_dir = None
    for i, part in enumerate(parts):
        if part.endswith('z') and i > 0 and parts[i-1].isdigit():
            run_dir = Path(*parts[:i+1])
            break
    
    if not run_dir:
        # Try to construct from base_dir
        run_dir = sample_path.parent.parent.parent.parent
    
    # Determine the category and structure
    category = None
    has_conus = 'conus' in parts
    
    # Extract category from path
    for i, part in enumerate(parts):
        if part.startswith('F') and part[1:].isdigit() and i < len(parts) - 1:
            # Found forecast hour directory, next should be conus or category
            if parts[i+1] == 'conus' and i+3 < len(parts):
                category = parts[i+3]
            elif parts[i+1] != 'conus':
                category = parts[i+1]
            break
    
    if not category:
        # Last directory before filename
        category = sample_path.parent.name
    
    # Search for all matching files
    matching_files = []
    
    for hour in range(max_hours + 1):
        # Try different path structures
        if has_conus:
            # New structure: F##/conus/F##/category/
            file_path = run_dir / f'F{hour:02d}' / 'conus' / f'F{hour:02d}' / category / f'{param_name}_f{hour:02d}_REFACTORED.png'
        else:
            # Old structure: F##/category/
            file_path = run_dir / f'F{hour:02d}' / category / f'{param_name}_f{hour:02d}_REFACTORED.png'
        
        if file_path.exists():
            matching_files.append((hour, file_path))
        else:
            # Try alternative structures
            alt_paths = [
                run_dir / f'F{hour:02d}' / f'F{hour:02d}' / category / f'{param_name}_f{hour:02d}_REFACTORED.png',
                run_dir / f'F{hour:02d}' / f'{param_name}_f{hour:02d}_REFACTORED.png'
            ]
            
            for alt_path in alt_paths:
                if alt_path.exists():
                    matching_files.append((hour, alt_path))
                    break
    
    # Sort by forecast hour
    matching_files.sort(key=lambda x: x[0])
    
    return matching_files


def create_gif(files, output_path, duration=500):
    """
    Create an animated GIF from a list of image files.
    
    Args:
        files: List of (forecast_hour, file_path) tuples
        output_path: Output GIF file path
        duration: Duration per frame in milliseconds
    """
    if not files:
        print("❌ No files to create GIF")
        return False
    
    # Load all images
    images = []
    for hour, file_path in files:
        try:
            img = Image.open(file_path)
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            images.append(img)
        except Exception as e:
            print(f"⚠️  Failed to load F{hour:02d}: {e}")
    
    if not images:
        print("❌ No valid images loaded")
        return False
    
    # Save as animated GIF
    try:
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=0
        )
        return True
    except Exception as e:
        print(f"❌ Failed to save GIF: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Create animated GIF from HRRR forecast images'
    )
    
    parser.add_argument('sample_file', help='Path to a sample image file')
    parser.add_argument('--output', '-o', required=True, help='Output GIF file path')
    parser.add_argument('--max-hours', type=int, default=48, help='Maximum forecast hours (default: 48)')
    parser.add_argument('--duration', type=int, default=250, help='Frame duration in ms (default: 250)')
    parser.add_argument('--base-dir', default='.', help='Base directory for outputs')
    
    args = parser.parse_args()
    
    # Find all matching files
    print(f"🔍 Finding files matching: {Path(args.sample_file).name}")
    files = find_matching_files(args.sample_file, args.max_hours, args.base_dir)
    
    if not files:
        print("❌ No matching files found")
        return 1
    
    print(f"📊 Found {len(files)} frames: F{files[0][0]:02d} to F{files[-1][0]:02d}")
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create the GIF
    print(f"🎬 Creating GIF...")
    if create_gif(files, output_path, args.duration):
        file_size = output_path.stat().st_size / (1024 * 1024)
        print(f"✅ GIF created: {output_path} ({file_size:.1f} MB)")
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())