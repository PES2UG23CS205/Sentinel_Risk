import os
import zipfile
from pathlib import Path

def create_bundle():
    root_dir = Path("c:/Users/acer/Documents/SentinelRisk")
    bundle_path = root_dir / "sentinelrisk_project_bundle.zip"
    
    if bundle_path.exists():
        bundle_path.unlink()
        
    exclude_dirs = {".git", ".pytest_cache", "__pycache__", ".agents", ".gemini", "node_modules"}
    exclude_extensions = {".pyc", ".pyo"}
    
    file_count = 0
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in root_dir.rglob("*"):
            # Check exclusions
            parts = set(path.parts)
            if parts.intersection(exclude_dirs):
                continue
            if path.suffix in exclude_extensions:
                continue
            if path.name == "sentinelrisk_project_bundle.zip":
                continue
            if path.is_file():
                arcname = path.relative_to(root_dir)
                zipf.write(path, arcname)
                file_count += 1
                
    size_mb = bundle_path.stat().st_size / (1024 * 1024)
    print(f"Successfully created SentinelRisk bundle: {bundle_path}")
    print(f"Total files packaged: {file_count}")
    print(f"Bundle size: {size_mb:.2f} MB")

if __name__ == "__main__":
    create_bundle()
