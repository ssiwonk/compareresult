"""
Helper script to deploy output/ to GitHub Pages.

Usage:
  python deploy_gh_pages.py
"""
import os
import subprocess
import sys

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "output")
    
    if not os.path.exists(output_dir) or not os.path.exists(os.path.join(output_dir, "index.html")):
        print("[Error] output/index.html not found! Please run 'python build.py' first.")
        sys.exit(1)
        
    print("=" * 60)
    print("🌐 [GitHub Pages 1-Click Deploy Helper]")
    print("=" * 60)
    
    # Check git status
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
    except Exception:
        print("[Error] Git is not installed or not in PATH.")
        sys.exit(1)
        
    # Check if inside git repo
    is_git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=base_dir, capture_output=True).returncode == 0
    
    if not is_git:
        print("\n[안내] 현재 폴더가 Git 저장소로 초기화되지 않았습니다.")
        print("GitHub에 배포하려면 다음 단계로 진행하시면 됩니다:")
        print("  1. git init")
        print("  2. git remote add origin https://github.com/<사용자명>/<저장소명>.git")
        print("  3. git add .")
        print("  4. git commit -m 'Initial commit'")
        print("  5. git push -u origin main")
        print("\n또는 output 폴더를 Vercel / Netlify / Cloudflare Pages에 그대로 드래그앤드롭하여 배포할 수 있습니다.")
        return

    print("[*] Deploying output/ to gh-pages branch...")
    try:
        # Check if gh-pages worktree or sub-git
        cmd = f"git subtree push --prefix output origin gh-pages"
        res = subprocess.run(cmd, shell=True, cwd=base_dir)
        if res.returncode == 0:
            print("\n🎉 배포 성공! GitHub 저장소 Settings -> Pages에서 gh-pages 브랜치가 활성화되었는지 확인하세요.")
        else:
            print("\n[안내] git subtree 배포가 실패했습니다. 일반 커밋 & 푸시 후 GitHub Actions를 사용해 보세요.")
    except Exception as e:
        print(f"[Error] {e}")

if __name__ == "__main__":
    main()
