"""
SLA Printer Extractor for UVtools
==================================
Extracts resin printer definitions from UVtools GitHub repository.
Designed for automated weekly updates via GitHub Actions.

Source: https://github.com/sn4k3/UVtools
"""

import requests
import re
import json
from typing import List, Dict

# --- CONFIGURATION ---
UVTOOLS_MACHINE_URL = "https://raw.githubusercontent.com/sn4k3/UVtools/master/UVtools.Core/Printer/Machine.cs"

# Blacklist for generic/custom entries
BLACKLIST_MODELS = ['custom', 'default', 'generic', 'unknown', 'test']


def fetch_machine_cs() -> str:
    """
    Downloads the Machine.cs file from UVtools GitHub repository.
    Returns the C# source code as a string.
    """
    print("🔍 Downloading UVtools Machine.cs...")
    
    try:
        response = requests.get(UVTOOLS_MACHINE_URL, timeout=30)
        response.raise_for_status()
        print(f"   ✅ Downloaded ({len(response.text)} bytes)")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️ Error downloading: {e}")
        return ""


def parse_machines(cs_content: str) -> List[Dict]:
    """
    Parses the C# Machine.cs file to extract printer definitions.
    
    The format in C# is:
    new(PrinterBrand.Anycubic, "Photon M3", 4096, 2560, 163.84f, 102.40f, 180f, FlipDirection.Horizontally),
    
    Returns a list of printer dictionaries.
    """
    print("🔧 Parsing SLA printer definitions...")
    
    # Regex to match machine definitions
    # Pattern: new(PrinterBrand.BRAND, "MODEL", resX, resY, displayWidth, displayHeight, machineZ, ...)
    pattern = r'new\s*\(\s*PrinterBrand\.(\w+)\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)f?\s*,\s*([\d.]+)f?\s*,\s*([\d.]+)f?'
    
    matches = re.findall(pattern, cs_content)
    
    printers = []
    seen = set()  # For deduplication
    
    for match in matches:
        brand, model, res_x, res_y, display_width, display_height, machine_z = match
        
        # Skip blacklisted models
        if model.lower() in BLACKLIST_MODELS:
            continue
        
        # Create unique key for deduplication
        unique_key = f"{brand.lower()}|{model.lower()}"
        if unique_key in seen:
            continue
        seen.add(unique_key)
        
        # Build printer object
        printers.append({
            "brand": brand,
            "model": model,
            "technology": "SLA",
            "volume": {
                "x": round(float(display_width), 2),
                "y": round(float(display_height), 2),
                "z": round(float(machine_z), 2)
            },
            "image_url": None,  # UVtools doesn't provide images
            "source": "UVtools"
        })
    
    return printers


def extract_sla_printers() -> List[Dict]:
    """
    Main extraction function for SLA printers.
    Returns list of printer dictionaries in standardized format.
    """
    cs_content = fetch_machine_cs()
    
    if not cs_content:
        print("   ⚠️ No content to parse")
        return []
    
    printers = parse_machines(cs_content)
    
    # Sort by brand and model
    printers.sort(key=lambda p: (p['brand'].lower(), p['model'].lower()))
    
    print(f"   ✅ Extracted {len(printers)} SLA printers")
    return printers


if __name__ == "__main__":
    # Test extraction
    printers = extract_sla_printers()
    print(f"\nTotal: {len(printers)} printers")
    if printers:
        print(f"Sample: {json.dumps(printers[0], indent=2)}")
