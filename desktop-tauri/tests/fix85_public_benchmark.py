#!/usr/bin/env python3
"""Public third-party PDF benchmark. Execution success is NOT OCR accuracy."""
import hashlib, json, pathlib, subprocess, sys, time, urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/"fix85_benchmark_output"; OUT.mkdir(parents=True,exist_ok=True)
ENGINE=ROOT.parent/"cad_backend/legacy_fix85/analyze_document.py"
SOURCES=[
("bearing_block","https://raw.githubusercontent.com/arushi-kri/2D-Mechanical-Drawings/main/Bearing_Block.pdf"),
("connecting_rod","https://raw.githubusercontent.com/arushi-kri/2D-Mechanical-Drawings/main/Connecting_Rod.pdf"),
("gib_cutter","https://raw.githubusercontent.com/arushi-kri/2D-Mechanical-Drawings/main/Gib_and_Cutter.pdf"),
("random_component","https://raw.githubusercontent.com/arushi-kri/2D-Mechanical-Drawings/main/Random_Component.pdf"),
("screw_jack","https://raw.githubusercontent.com/arushi-kri/2D-Mechanical-Drawings/main/Screw_Jack.pdf"),
("keyway_shaft","https://raw.githubusercontent.com/sanskarshinde500-netizen/AutoCAD-2D-Drawing-/main/Keyway%20Shaft-Model.pdf"),
("taper_shaft","https://raw.githubusercontent.com/sanskarshinde500-netizen/AutoCAD-2D-Drawing-/main/Taper_Shaft-Model.pdf"),
("full_section","https://raw.githubusercontent.com/sanskarshinde500-netizen/AutoCAD-2D-Drawing-/main/Full_section_view-Model.pdf"),
("dimension_plate","https://raw.githubusercontent.com/sanskarshinde500-netizen/AutoCAD-2D-Drawing-/main/Fully%20Dimension%20Plate-Model.pdf"),
("half_section","https://raw.githubusercontent.com/sanskarshinde500-netizen/AutoCAD-2D-Drawing-/main/Half_section_-Model.pdf"),
("motor_mount","https://raw.githubusercontent.com/sanskarshinde500-netizen/AutoCAD-2D-Drawing-/main/motor_mounting_plate-Model.pdf"),
("historic_scan_1","https://archive.org/download/mechanicaldrawin01inte/mechanicaldrawin01inte.pdf"),
("historic_scan_2","https://archive.org/download/mechanicaldrawin00inte/mechanicaldrawin00inte.pdf"),
]
def run_engine(path, name):
    t=time.monotonic()
    try:
        p=subprocess.run([sys.executable,str(ENGINE),str(path)],capture_output=True,text=True,timeout=240)
        data=json.loads(p.stdout) if p.returncode==0 else None
        return {"status":"EXECUTED" if data is not None else "ERROR","seconds":round(time.monotonic()-t,2),"result":data,"stderr":p.stderr[-2000:],"returncode":p.returncode}
    except Exception as exc:
        return {"status":"ERROR","error":str(exc),"seconds":round(time.monotonic()-t,2)}
def main():
    if not ENGINE.is_file(): raise SystemExit("FIX85 engine absent: cannot benchmark")
    results=[]
    for name,url in SOURCES:
        record={"name":name,"url":url,"variants":{}}
        try:
            path=OUT/(name+".pdf")
            request=urllib.request.Request(url,headers={"User-Agent":"DS-Estimate-OCR-benchmark/1.0"})
            with urllib.request.urlopen(request,timeout=60) as response:
                with path.open("wb") as f:
                    while chunk:=response.read(1024*1024): f.write(chunk)
            if path.stat().st_size>100_000_000 or path.read_bytes()[:4]!=b"%PDF": raise ValueError("Invalid or oversized PDF")
            record["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
            record["variants"]["original_pdf"]=run_engine(path,name)
            # Rasterize first page: this is a genuine OCR-only PDF, not a text-layer PDF.
            import fitz
            from PIL import Image
            doc=fitz.open(path)
            if len(doc):
                pix=doc[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
                png=OUT/(name+"_scan.png"); pix.save(str(png))
                jpg=OUT/(name+"_compressed.jpg")
                with Image.open(png) as img: img.convert("RGB").save(jpg,quality=45)
                scanpdf=OUT/(name+"_scan.pdf")
                imgdoc=fitz.open(); page=imgdoc.new_page(width=pix.width,height=pix.height)
                page.insert_image(page.rect,filename=str(jpg)); imgdoc.save(str(scanpdf)); imgdoc.close()
                for variant,p in [("scan_png",png),("compressed_jpg",jpg),("image_only_pdf",scanpdf)]:
                    record["variants"][variant]=run_engine(p,name)
        except Exception as exc: record["download_error"]=str(exc)
        results.append(record)
        (OUT/"results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
        print(name,{k:v["status"] for k,v in record["variants"].items()},record.get("download_error",""),flush=True)
    summary={"documents":len(results),"downloaded":sum("sha256" in r for r in results),
             "executed":sum(v["status"]=="EXECUTED" for r in results for v in r["variants"].values()),
             "errors":sum(v["status"]=="ERROR" for r in results for v in r["variants"].values()),
             "accuracy":"NOT MEASURED: requires manual ground truth"}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(summary)
    if summary["downloaded"]<3 or summary["errors"]>0: raise SystemExit(1)
if __name__=="__main__":main()
