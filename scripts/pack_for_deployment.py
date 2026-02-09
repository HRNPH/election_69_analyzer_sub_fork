import os
import shutil
from pathlib import Path

def pack_site():
    # Define paths
    root_dir = Path(__file__).parent.parent
    docs_dir = root_dir / "docs"
    
    # Source files
    index_src = root_dir / "index.html"
    report_src = root_dir / "data" / "anomaly_report.json"
    
    # Clean and recreate docs directory
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir()
    
    # 1. Copy index.html
    shutil.copy2(index_src, docs_dir / "index.html")
    print(f"✅ Copied index.html to {docs_dir}/")
    
    # 2. Copy data/anomaly_report.json
    # We maintain the 'data/' folder structure so the fetch('data/...') in index.html works
    (docs_dir / "data").mkdir()
    shutil.copy2(report_src, docs_dir / "data" / "anomaly_report.json")
    print(f"✅ Copied anomaly_report.json to {docs_dir}/data/")
    
    # 3. Create .nojekyll (prevents GitHub from ignoring files starting with _)
    (docs_dir / ".nojekyll").touch()
    print(f"✅ Created .nojekyll")
    
    print("\n📦 Site packed successfully in 'docs/' folder!")
    print("👉 To deploy: Go to GitHub Repo > Settings > Pages > Build and deployment")
    print("   Select Source: 'Deploy from a branch'")
    print("   Select Branch: 'main' and Folder: '/docs'")

if __name__ == "__main__":
    pack_site()
