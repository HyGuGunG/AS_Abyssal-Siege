"""
qa_run.py  --  QA 실행 진입점
사용법: python qa_run.py
- qa_screenshot.py 실행 → 스크린샷 촬영
- qa_out/ 폴더에 저장
- 에러 로그 출력
"""
import subprocess, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))

def main():
    print("=" * 50)
    print("Abyssal Siege QA 자동 촬영 시작")
    print("=" * 50)

    # 이전 스크린샷 정리
    out = os.path.join(BASE, "qa_out")
    if os.path.isdir(out):
        import shutil
        shutil.rmtree(out)

    result = subprocess.run(
        [sys.executable, os.path.join(BASE, "qa_screenshot.py")],
        capture_output=True, text=True, encoding="utf-8"
    )
    print(result.stdout)
    if result.returncode != 0:
        print("[ERROR]", result.stderr[-1000:] if result.stderr else "알 수 없는 오류")
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
