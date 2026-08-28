"""
Multi-Project Slide Comparison Hub & Viewer Generator.

Usage:
  python build.py               # Build all projects and open Hub dashboard
  python build.py --serve       # Keep local web server running
  python build.py --port 8080   # Custom port
  python build.py --no-open     # Build without opening browser
"""
import os
import sys
import shutil
import json
import argparse
import webbrowser
import http.server
import socketserver
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from src.converter import process_file
from src.aligner import generate_comparison_data

VALID_EXTS = ('.pdf', '.pptx', '.ppt')

def get_project_files_in_dir(folder_path):
    """Returns sorted list of valid PDF/PPTX files in a directory."""
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(VALID_EXTS) and not f.startswith('~')]
    files.sort()
    return [os.path.join(folder_path, f) for f in files]

def discover_projects(input_dir):
    """
    Discovers projects from input directory.
    Supports:
      1. Subfolders containing 2+ files (e.g. input/1주차/, input/2주차/)
      2. Direct files in input/ (treated as a default project)
    """
    projects = []
    
    # 1. Check subdirectories
    for item in sorted(os.listdir(input_dir)):
        item_path = os.path.join(input_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            p_files = get_project_files_in_dir(item_path)
            if len(p_files) >= 2:
                projects.append({
                    "name": item,
                    "folder_path": item_path,
                    "files": p_files
                })

    # 2. Check direct files in input/
    direct_files = get_project_files_in_dir(input_dir)
    if len(direct_files) >= 2:
        # Determine a title from the first file name
        base_name = os.path.splitext(os.path.basename(direct_files[0]))[0]
        # Clean title
        title = base_name.replace("1_", "").replace("-원고_v1", "").replace("_", " ").strip()
        if not title:
            title = "기본 프로젝트"
        projects.append({
            "name": title,
            "folder_path": input_dir,
            "files": direct_files
        })

    return projects

def make_safe_slug(name):
    slug = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in name])
    return slug.strip("_") or "project"

def build_single_project(proj, output_projects_dir, templates_dir):
    """Builds one comparison viewer project."""
    slug = make_safe_slug(proj["name"])
    proj_out_dir = os.path.join(output_projects_dir, slug)
    os.makedirs(proj_out_dir, exist_ok=True)
    
    print("\n" + "-" * 50)
    print(f"[*] Processing Project: {proj['name']} ({len(proj['files'])} files)")
    print("-" * 50)

    # 1. Convert and render slides
    file_results = []
    for fpath in proj["files"]:
        res = process_file(fpath, proj_out_dir)
        file_results.append(res)

    # 2. DP Sequence Alignment
    comparison_data = generate_comparison_data(file_results)
    comparison_data["project_title"] = proj["name"]

    # 3. Copy project viewer templates
    shutil.copy2(os.path.join(templates_dir, "index.html"), os.path.join(proj_out_dir, "index.html"))
    shutil.copy2(os.path.join(templates_dir, "style.css"), os.path.join(proj_out_dir, "style.css"))
    shutil.copy2(os.path.join(templates_dir, "app.js"), os.path.join(proj_out_dir, "app.js"))

    # 4. Save data.json and data.js
    with open(os.path.join(proj_out_dir, "data.json"), "w", encoding="utf-8") as f:
        json.dump(comparison_data, f, ensure_ascii=False, indent=2)

    with open(os.path.join(proj_out_dir, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.SLIDE_DATA = " + json.dumps(comparison_data, ensure_ascii=False, indent=2) + ";\n")

    # Get thumbnail from first slide of base file
    first_img = ""
    if file_results and file_results[0]["slides"]:
        first_img = file_results[0]["slides"][0]["image"]

    return {
        "id": slug,
        "title": proj["name"],
        "url": f"projects/{slug}/index.html",
        "thumbnail": f"projects/{slug}/{first_img}" if first_img else "",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "files": comparison_data["files"]
    }

def main():
    parser = argparse.ArgumentParser(description="Slide Comparison Hub Generator")
    parser.add_argument("--input", default="input", help="Path to input directory")
    parser.add_argument("--output", default="output", help="Path to output directory")
    parser.add_argument("--templates", default="templates", help="Path to templates directory")
    parser.add_argument("--port", type=int, default=8000, help="Local server port")
    parser.add_argument("--no-serve", action="store_true", help="Do not keep local HTTP server running after build")
    parser.add_argument("--no-open", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, args.input)
    output_dir = os.path.join(base_dir, args.output)
    templates_dir = os.path.join(base_dir, args.templates)
    output_projects_dir = os.path.join(output_dir, "projects")

    print("=" * 60)
    print("[Slide Comparison Hub & Viewer Multi-Project Builder]")
    print("=" * 60)

    if not os.path.exists(input_dir):
        print(f"[Error] Input directory not found: {input_dir}")
        sys.exit(1)

    projects = discover_projects(input_dir)
    if not projects:
        print(f"[Error] No valid projects found in '{input_dir}'.")
        print("  Place at least 2 PDF/PPTX files directly in input/ or in subdirectories (e.g. input/1주차/).")
        sys.exit(1)

    print(f"[*] Discovered {len(projects)} comparison project(s):")
    for idx, p in enumerate(projects):
        print(f"    {idx + 1}. {p['name']} ({len(p['files'])} files)")

    os.makedirs(output_projects_dir, exist_ok=True)

    # Build all projects
    projects_meta = []
    for p in projects:
        meta = build_single_project(p, output_projects_dir, templates_dir)
        projects_meta.append(meta)

    # Generate Hub Dashboard in output/
    print("\n" + "=" * 60)
    print("[*] Generating Main Dashboard Hub in output/...")
    print("=" * 60)

    shutil.copy2(os.path.join(templates_dir, "dashboard.html"), os.path.join(output_dir, "index.html"))
    shutil.copy2(os.path.join(templates_dir, "dashboard.css"), os.path.join(output_dir, "dashboard.css"))
    shutil.copy2(os.path.join(templates_dir, "dashboard.js"), os.path.join(output_dir, "dashboard.js"))

    with open(os.path.join(output_dir, "projects.json"), "w", encoding="utf-8") as f:
        json.dump(projects_meta, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "projects.js"), "w", encoding="utf-8") as f:
        f.write("window.PROJECTS_DATA = " + json.dumps(projects_meta, ensure_ascii=False, indent=2) + ";\n")

    print("\n" + "=" * 60)
    print("[ALL BUILDS COMPLETE!]")
    print(f"    Dashboard Hub: {os.path.join(output_dir, 'index.html')}")
    print(f"    Total Projects: {len(projects_meta)}")
    print("=" * 60)

    # Start local web server
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=output_dir, **kw)
        def log_message(self, format, *args):
            pass

    port = args.port
    for p in range(port, port + 20):
        try:
            httpd = socketserver.TCPServer(("", p), QuietHandler)
            port = p
            break
        except OSError:
            continue

    url = f"http://localhost:{port}/index.html"
    print(f"\n>> Local Dashboard URL: {url}")

    if not args.no_open:
        print("[*] Opening browser...")
        webbrowser.open(url)

    if not args.no_serve:
        print("\n" + "=" * 60)
        print(f"[*] 로컬 웹 서버가 실행 중입니다: {url}")
        print("[*] 브라우저에서 슬라이드 비교 뷰어를 자유롭게 확인하세요.")
        print("[*] 서버를 종료하시려면 이 터미널 창에서 Ctrl + C 를 누르세요.")
        print("=" * 60 + "\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] 로컬 서버를 종료했습니다.")
    else:
        print(f"[*] Done! You can view {url} or open index.html directly.")

if __name__ == "__main__":
    main()
