"""
Master Build Script for Printer Database
==========================================
Merges FDM (OrcaSlicer) and SLA (UVtools) printer data into a unified JSON.
Designed for automated weekly updates via GitHub Actions.

Output:
  - data/printers.json - Complete printer database
  - data/metadata.json - Build metadata with timestamp and counts
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict

from extract_fdm import extract_fdm_printers
from extract_sla import extract_sla_printers


# --- CONFIGURATION ---
OUTPUT_DIR = "data"
PRINTERS_FILE = os.path.join(OUTPUT_DIR, "printers.json")
METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")


def normalize_key(brand: str, model: str) -> str:
    """
    Creates a normalized key for deduplication.
    Handles case, spaces, and special characters.
    """
    brand_norm = brand.lower().strip().replace(' ', '_')
    model_norm = model.lower().strip().replace(' ', '_').replace('-', '_')
    return f"{brand_norm}|{model_norm}"


def merge_printers(fdm_list: List[Dict], sla_list: List[Dict]) -> List[Dict]:
    """
    Merges FDM and SLA printer lists with deduplication.
    
    Priority rules:
    - SLA technology: prefer UVtools data
    - FDM technology: prefer OrcaSlicer data
    - Same brand+model with different tech: keep both
    """
    merged = {}
    
    # Add FDM printers first
    for printer in fdm_list:
        key = normalize_key(printer['brand'], printer['model'])
        tech_key = f"{key}|fdm"
        merged[tech_key] = printer
    
    # Add SLA printers (may override FDM if same brand/model but SLA)
    for printer in sla_list:
        key = normalize_key(printer['brand'], printer['model'])
        tech_key = f"{key}|sla"
        merged[tech_key] = printer
    
    # Convert back to list and sort
    result = list(merged.values())
    result.sort(key=lambda p: (p['brand'].lower(), p['model'].lower()))
    
    return result


def generate_metadata(printers: List[Dict]) -> Dict:
    """
    Generates metadata about the build.
    """
    fdm_count = len([p for p in printers if p['technology'] == 'FDM'])
    sla_count = len([p for p in printers if p['technology'] == 'SLA'])
    with_image = len([p for p in printers if p.get('image_url')])
    
    brands = sorted(set(p['brand'] for p in printers))
    
    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_printers": len(printers),
        "fdm_count": fdm_count,
        "sla_count": sla_count,
        "with_images": with_image,
        "brand_count": len(brands),
        "brands": brands,
        "sources": {
            "fdm": "https://github.com/SoftFever/OrcaSlicer",
            "sla": "https://github.com/sn4k3/UVtools"
        }
    }


def save_json(data: any, filepath: str) -> None:
    """Saves data to JSON file with proper formatting."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"   💾 Saved: {filepath}")


def main():
    """Main build process."""
    print("=" * 60)
    print("🚀 PRINTER DATABASE BUILD")
    print("=" * 60)
    
    # Extract FDM printers
    print("\n📦 Phase 1: FDM Extraction (OrcaSlicer)")
    print("-" * 40)
    fdm_printers = extract_fdm_printers()
    
    # Extract SLA printers
    print("\n📦 Phase 2: SLA Extraction (UVtools)")
    print("-" * 40)
    sla_printers = extract_sla_printers()
    
    # Merge databases
    print("\n🔀 Phase 3: Merging Databases")
    print("-" * 40)
    all_printers = merge_printers(fdm_printers, sla_printers)
    print(f"   ✅ Merged: {len(all_printers)} unique printers")
    
    # Generate metadata
    print("\n📊 Phase 4: Generating Metadata")
    print("-" * 40)
    metadata = generate_metadata(all_printers)
    
    # Save files
    print("\n💾 Phase 5: Saving Files")
    print("-" * 40)
    save_json(all_printers, PRINTERS_FILE)
    save_json(metadata, METADATA_FILE)
    
    # Summary
    print("\n" + "=" * 60)
    print("✨ BUILD COMPLETE")
    print("=" * 60)
    print(f"   Total Printers: {metadata['total_printers']}")
    print(f"   FDM: {metadata['fdm_count']}")
    print(f"   SLA: {metadata['sla_count']}")
    print(f"   With Images: {metadata['with_images']}")
    print(f"   Brands: {metadata['brand_count']}")
    print(f"   Updated: {metadata['last_updated']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
