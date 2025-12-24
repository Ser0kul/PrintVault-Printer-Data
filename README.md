# PrintVault Printer Data Repository

A headless data repository that automatically updates printer specifications from upstream sources using GitHub Actions.

## 📊 Data Sources

| Source | Technology | Repository |
|--------|------------|------------|
| OrcaSlicer | FDM | [SoftFever/OrcaSlicer](https://github.com/SoftFever/OrcaSlicer) |
| UVtools | SLA/DLP | [sn4k3/UVtools](https://github.com/sn4k3/UVtools) |

## 📁 Files

```
printer-data-repo/
├── data/
│   ├── printers.json     # Unified printer database
│   └── metadata.json     # Build metadata & statistics
├── extract_fdm.py        # FDM extraction script
├── extract_sla.py        # SLA extraction script
├── main_build.py         # Master build script
├── requirements.txt      # Python dependencies
└── .github/workflows/
    └── update_db.yml     # Automated update workflow
```

## 🚀 Usage

### Local Build

```bash
pip install -r requirements.txt
python main_build.py
```

### Automated Updates

The database updates automatically every Sunday at 00:00 UTC via GitHub Actions.

You can also trigger a manual update from the Actions tab.

## 📋 Data Schema

Each printer entry follows this structure:

```json
{
  "brand": "BrandName",
  "model": "Model Name",
  "technology": "FDM" | "SLA",
  "volume": {
    "x": 250.0,
    "y": 250.0,
    "z": 250.0
  },
  "image_url": "https://..." | null,
  "source": "OrcaSlicer" | "UVtools"
}
```

## 📈 Current Statistics

See `data/metadata.json` for current database statistics.

## 📄 License

MIT License - Data is sourced from open-source projects.
