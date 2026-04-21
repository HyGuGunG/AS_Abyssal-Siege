"""
make_fx_sprites.py
Abyssal Siege - E스킬 FX 스프라이트 시트 생성

사용법: python make_fx_sprites.py

입력:  AS_Assets/fx_frames/fx_valk_sk1_<name>/frame_XXXX.png
출력:  AS_Assets/fx_sheets/fx_valk_sk1_<name>_sheet.png

배경 처리:
  - 검정(0,0,0) 배경을 알파 투명으로 변환
  - URP alpha=0 버그 보정: RGB > BLACK_THRESH 픽셀은 alpha=255 강제 설정
  - additive 파티클 효과는 검정 배경에서 자연스럽게 추출됨
"""

import os
import math
from PIL import Image

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(BASE_DIR, "AS_Assets", "fx_frames")
OUTPUT_DIR = os.path.join(BASE_DIR, "AS_Assets", "fx_sheets")

BLACK_THRESH = 5  # 이 이하 RGB는 검정 배경으로 판별

# ValkSkillCapture.cs 출력 폴더명과 일치시킬 것
SPECS = [
    dict(folder="fx_valk_sk1_body",   output="fx_valk_sk1_body_sheet.png",   fw=512, fh=512, cols=8),
    dict(folder="fx_valk_sk1_main",   output="fx_valk_sk1_main_sheet.png",   fw=512, fh=512, cols=8),
    dict(folder="fx_valk_sk1_weapon", output="fx_valk_sk1_weapon_sheet.png", fw=512, fh=512, cols=8),
]


def process_fx_frame(img: Image.Image) -> Image.Image:
    """검정 배경 제거 + URP alpha=0 보정"""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > BLACK_THRESH or g > BLACK_THRESH or b > BLACK_THRESH:
                pixels[x, y] = (r, g, b, 255)  # 이펙트 픽셀 → 완전 불투명
            else:
                pixels[x, y] = (0, 0, 0, 0)    # 검정 배경 → 투명
    return img


def make_sheet(spec: dict) -> bool:
    folder_path = os.path.join(FRAMES_DIR, spec["folder"])
    if not os.path.isdir(folder_path):
        print(f"  [SKIP] 폴더 없음: {folder_path}")
        return False

    frame_files = sorted([
        f for f in os.listdir(folder_path)
        if f.startswith("frame_") and f.endswith(".png")
    ])
    if not frame_files:
        print(f"  [SKIP] 프레임 없음: {folder_path}")
        return False

    fw, fh = spec["fw"], spec["fh"]
    cols   = spec["cols"]
    n      = len(frame_files)
    rows   = math.ceil(n / cols)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sheet = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))

    for i, fname in enumerate(frame_files):
        frame = Image.open(os.path.join(folder_path, fname)).convert("RGBA")
        # process 먼저, resize 나중 (premultiplied alpha 블렌딩 문제 방지)
        frame = process_fx_frame(frame)
        if frame.size != (fw, fh):
            frame = frame.resize((fw, fh), Image.LANCZOS)
        col = i % cols
        row = i // cols
        sheet.paste(frame, (col * fw, row * fh), frame)

    out_path = os.path.join(OUTPUT_DIR, spec["output"])
    sheet.save(out_path, "PNG")
    print(f"  OK {spec['output']}  ({cols}x{rows}  {n}frames  {fw}x{fh}px)")
    return True


def main():
    print("=" * 55)
    print("make_fx_sprites.py - E스킬 FX 스프라이트 시트 생성")
    print("=" * 55)

    if not os.path.isdir(FRAMES_DIR):
        print(f"[ERROR] 프레임 폴더 없음: {FRAMES_DIR}")
        print("ValkSkillCapture.cs 로 먼저 캡처를 진행하세요.")
        return

    ok = 0
    for spec in SPECS:
        print(f"\n  {spec['folder']}...")
        if make_sheet(spec):
            ok += 1

    print(f"\n{'=' * 55}")
    print(f"완료: {ok}/{len(SPECS)} 시트 생성됨")
    print(f"출력: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
