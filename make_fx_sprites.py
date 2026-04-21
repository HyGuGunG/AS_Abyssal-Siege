"""
make_fx_sprites.py
Abyssal Siege — E스킬 이펙트 스프라이트 시트 생성 스크립트

사용법:
    python make_fx_sprites.py

입력:  AS_Assets/fx_frames/<folder>/frame_XXXX.png
출력:  AS_Assets/fx_sheets/fx_valk_sk1_<name>_sheet.png

배경 처리 방식:
  - MAGENTA_FOLDERS: 마젠타(#FF00FF) 크로마키 → 알파 투명
  - BLACK_FOLDERS:   검정 배경 → 밝기 기반 알파 추출 (screen blend 용도)

origin-centered 방식:
  프레임 중앙(256,256) = Unity 원점으로 고정 → 이펙트 위치 정확한 정렬
"""

import os
import math
from PIL import Image

# ══ 경로 설정 ════════════════════════════════════════════════════════════
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR  = os.path.join(BASE_DIR, "AS_Assets", "fx_frames")
OUTPUT_DIR  = os.path.join(BASE_DIR, "AS_Assets", "fx_sheets")

# ══ 배경 제거 임계값 ═════════════════════════════════════════════════════
CHROMA_THRESHOLD = 130   # 마젠타 판별 임계값
BLACK_THRESHOLD  = 20    # 검정 배경 밝기 임계값 (이 이하 → 투명)

# ══ 스프라이트 시트 스펙 ════════════════════════════════════════════════
SPECS = [
    dict(folder="valk_sk1_main",   output="fx_valk_sk1_main_sheet.png",   fw=512, fh=512, cols=8, mode="magenta"),
    dict(folder="valk_sk1_body",   output="fx_valk_sk1_body_sheet.png",   fw=512, fh=512, cols=8, mode="black"),
    dict(folder="valk_sk1_weapon", output="fx_valk_sk1_weapon_sheet.png", fw=512, fh=512, cols=8, mode="black"),
]


def remove_magenta(img: Image.Image) -> Image.Image:
    """마젠타 배경 → 알파 투명"""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > CHROMA_THRESHOLD and g < 120 and b > CHROMA_THRESHOLD:
                pixels[x, y] = (0, 0, 0, 0)
    return img


def remove_black(img: Image.Image) -> Image.Image:
    """검정 배경 → 밝기 기반 알파 (screen blend 소재용)"""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            brightness = (int(r) + int(g) + int(b)) // 3
            if brightness <= BLACK_THRESHOLD:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                # 밝기를 알파로 변환 (밝을수록 불투명)
                new_alpha = min(255, brightness * 2)
                pixels[x, y] = (r, g, b, new_alpha)
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
        print(f"  [SKIP] 프레임 파일 없음: {folder_path}")
        return False

    fw, fh   = spec["fw"], spec["fh"]
    cols     = spec["cols"]
    n_frames = len(frame_files)
    rows     = math.ceil(n_frames / cols)

    sheet = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))

    for i, fname in enumerate(frame_files):
        fpath = os.path.join(folder_path, fname)
        frame = Image.open(fpath).convert("RGBA")

        if frame.size != (fw, fh):
            frame = frame.resize((fw, fh), Image.LANCZOS)

        if spec["mode"] == "magenta":
            frame = remove_magenta(frame)
        elif spec["mode"] == "black":
            frame = remove_black(frame)

        col = i % cols
        row = i // cols
        sheet.paste(frame, (col * fw, row * fh), frame)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, spec["output"])
    sheet.save(out_path, "PNG")
    print(f"  ✓ {spec['output']}  ({cols}×{rows}  {n_frames}frames)")
    return True


def main():
    print("=" * 60)
    print("make_fx_sprites.py — E스킬 이펙트 스프라이트 시트 생성")
    print("=" * 60)

    if not os.path.isdir(FRAMES_DIR):
        print(f"[ERROR] fx_frames 폴더 없음: {FRAMES_DIR}")
        print("EffectCaptureValkSk1.cs로 먼저 캡처를 진행하세요.")
        return

    ok = 0
    for spec in SPECS:
        print(f"\n▶ {spec['folder']}  ({spec['mode']})")
        if make_sheet(spec):
            ok += 1

    print(f"\n{'='*60}")
    print(f"완료: {ok}/{len(SPECS)} 시트 생성됨")
    print(f"출력: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
