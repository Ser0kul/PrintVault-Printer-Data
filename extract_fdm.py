"""
FDM Printer Extractor for OrcaSlicer
=====================================
Extracts FDM printer definitions from OrcaSlicer GitHub repository.
Designed for automated weekly updates via GitHub Actions.

Source: https://github.com/SoftFever/OrcaSlicer
"""

import requests
import re
import json
from typing import List, Dict, Optional

# --- CONFIGURATION ---
GITHUB_API_BASE = "https://api.github.com/repos/SoftFever/OrcaSlicer"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/SoftFever/OrcaSlicer/main"
PROFILES_PATH = "resources/profiles"

# Keywords to identify FDM technology
FDM_KEYWORDS = ['nozzle_diameter', 'filament', 'extruder', 'retraction', 'bed_temperature', 'fff']

# Blacklist for non-printer items (accessories, hotends, kits)
BLACKLIST_KEYWORDS = [
    'hotend', 'hot end', 'all-metal', 'nozzle', 'plate', 'kit', 'extruder',
    'sheet', 'smooth', 'textured', 'satin', 'cool', 'engineering', 
    'high temp', 'hardened', 'chamber', 'auxiliary'
]


def get_brands() -> List[str]:
    """
    Fetches the list of brand directories from OrcaSlicer profiles.
    Returns a list of brand folder names.
    """
    url = f"{GITHUB_API_BASE}/contents/{PROFILES_PATH}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        contents = response.json()
        return [item['name'] for item in contents if item['type'] == 'dir']
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching brands: {e}")
        return []


def get_machine_files(brand: str) -> List[Dict]:
    """
    Fetches machine JSON files for a specific brand.
    Looks in the 'machine' subdirectory of each brand folder.
    """
    url = f"{GITHUB_API_BASE}/contents/{PROFILES_PATH}/{brand}/machine"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            # Try direct brand folder if no 'machine' subfolder
            url = f"{GITHUB_API_BASE}/contents/{PROFILES_PATH}/{brand}"
            response = requests.get(url, timeout=30)
        response.raise_for_status()
        contents = response.json()
        return [item for item in contents if item['name'].endswith('.json')]
    except requests.exceptions.RequestException:
        return []


def parse_machine_json(json_url: str) -> Optional[Dict]:
    """
    Downloads and parses a machine JSON file.
    Returns parsed data or None if invalid.
    """
    try:
        response = requests.get(json_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return None


def parse_volume(data: Dict) -> Dict[str, float]:
    """
    Extracts print volume from OrcaSlicer machine JSON.
    Returns dict with x, y, z dimensions in mm.
    """
    volume = {"x": 0, "y": 0, "z": 0}
    
    # Method 1: printable_area (polygon)
    if 'printable_area' in data:
        area = data['printable_area']
        if isinstance(area, list) and len(area) >= 4:
            x_coords = []
            y_coords = []
            for point in area:
                if isinstance(point, str) and 'x' in point:
                    try:
                        parts = point.split('x')
                        x_coords.append(float(parts[0]))
                        y_coords.append(float(parts[1]))
                    except (ValueError, IndexError):
                        pass
            if x_coords and y_coords:
                volume['x'] = round(max(x_coords) - min(x_coords), 2)
                volume['y'] = round(max(y_coords) - min(y_coords), 2)
    
    # Method 2: Direct values
    if volume['x'] == 0:
        volume['x'] = float(data.get('bed_width', 0))
        volume['y'] = float(data.get('bed_depth', 0))
    
    # Height
    if 'printable_height' in data:
        volume['z'] = float(data['printable_height'])
    elif 'machine_max_print_height' in data:
        volume['z'] = float(data['machine_max_print_height'])
    
    return volume


def find_image_url(brand: str, model: str) -> Optional[str]:
    """
    Attempts to find a cover image for the printer.
    Returns raw GitHub URL or None.
    """
    # Standard naming: Brand Model_cover.png
    safe_name = f"{brand} {model}".replace(' ', '_')
    candidates = [
        f"{GITHUB_RAW_BASE}/{PROFILES_PATH}/{brand}/{brand} {model}_cover.png",
        f"{GITHUB_RAW_BASE}/{PROFILES_PATH}/{brand}/{safe_name}_cover.png",
    ]
    
    for url in candidates:
        try:
            response = requests.head(url.replace(' ', '%20'), timeout=10)
            if response.status_code == 200:
                return url.replace(' ', '%20')
        except requests.exceptions.RequestException:
            pass
    
    return None


def get_base_model_name(name: str, brand: str) -> str:
    """
    Cleans model name by removing brand prefix and technical suffixes.
    """
    # Remove brand prefix
    if name.lower().startswith(brand.lower() + " "):
        name = name[len(brand) + 1:].strip()
    
    # Remove nozzle specifications
    name = re.sub(r'\s+\d+(\.\d+)?\s*(mm)?\s*nozzle', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(.*nozzle.*\)', '', name, flags=re.IGNORECASE)
    
    return name.strip()


def is_blacklisted(name: str) -> bool:
    """Checks if the model name contains blacklisted keywords."""
    return any(kw in name.lower() for kw in BLACKLIST_KEYWORDS)


def extract_fdm_printers() -> List[Dict]:
    """
    Main extraction function for FDM printers.
    Returns list of printer dictionaries in standardized format.
    """
    print("🔍 Extracting FDM printers from OrcaSlicer...")
    
    printers = []
    seen = set()
    
    brands = get_brands()
    print(f"   Found {len(brands)} brands")
    
    for brand in brands:
        machine_files = get_machine_files(brand)
        
        for file_info in machine_files:
            # Download and parse JSON
            json_url = file_info.get('download_url')
            if not json_url:
                continue
                
            data = parse_machine_json(json_url)
            if not data:
                continue
            
            # Check if it's a printer definition
            if 'printable_area' not in data and 'printable_height' not in data:
                continue
            
            # Get model name
            raw_name = data.get('printer_model', data.get('name', file_info['name'].replace('.json', '')))
            
            # Skip blacklisted items
            if is_blacklisted(raw_name):
                continue
            
            model = get_base_model_name(raw_name, brand)
            
            # Deduplicate
            unique_key = f"{brand.lower()}|{model.lower()}"
            if unique_key in seen:
                continue
            seen.add(unique_key)
            
            # Parse volume
            volume = parse_volume(data)
            if volume['x'] < 10:  # Skip invalid entries
                continue
            
            # Find image
            image_url = find_image_url(brand, model)
            
            printers.append({
                "brand": brand,
                "model": model,
                "technology": "FDM",
                "volume": volume,
                "image_url": image_url,
                "source": "OrcaSlicer"
            })
    
    print(f"   ✅ Extracted {len(printers)} FDM printers")
    return printers


if __name__ == "__main__":
    # Test extraction
    printers = extract_fdm_printers()
    print(f"\nTotal: {len(printers)} printers")
    if printers:
        print(f"Sample: {json.dumps(printers[0], indent=2)}")
