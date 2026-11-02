"""Bridge to FIX85 analyze_document.py. Expects vendored source in cad_backend/legacy_fix85/.
FIX85 engine is intentionally not rewritten: its OCR, PDF page evidence and technical
signals remain intact. Outputs structured JSON, with provenance and warnings.
"""
import json
import subprocess
import sys
from pathlib import Path

def analyze_document(path, timeout=180):
    engine = Path(__file__).resolve().parent / "legacy_fix85" / "analyze_document.py"
    if not engine.is_file():
        raise FileNotFoundError("FIX85 document engine not bundled")
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(str(source))
    if source.suffix.lower() not in {".pdf",".png",".jpg",".jpeg",".tif",".tiff",".bmp"}:
        raise ValueError("Unsupported drawing format")
    p = subprocess.run([sys.executable,str(engine),str(source)],capture_output=True,text=True,timeout=timeout,check=False)
    if p.returncode:
        raise RuntimeError(f"FIX85 exited {p.returncode}: {p.stderr[-1500:]}")
    result=json.loads(p.stdout)
    return {"engine":"FIX85","source":str(source),"result":result}

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("file")
    args=parser.parse_args()
    print(json.dumps(analyze_document(args.file),ensure_ascii=False))
