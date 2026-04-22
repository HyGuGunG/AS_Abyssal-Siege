"""
make_fx_sprites.py
Abyssal Siege - E스킬 FX 스프라이트 시트 생성

사용법: python make_fx_sprites.py

입력:  AS_Assets/fx_frames/fx_valk_sk1_<name>/frame_XXXX.png
출력:  AS_Assets/fx_sheets/fx_valk_sk1_<name>_sheet.png

배경 처리:
  - 검정(0,0,0) 배경을 알파 투명으로 변환
  - brightness 배율로 HDR bloom 효과 베이크 (런타임 filter 제거 위해 필요)
  - hue_shift로 색상 보정 (additive 파티클은 약간 탈색되므로 채도/색상 보강)
  - main/weapon: brightness=4, body: brightness=80 (극히 어두운 additive dim 픽셀 가시화)
"""

import os
import math
import colorsys
from PIL import Image

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(BASE_DIR, "AS_Assets", "fx_frames")
OUTPUT_DIR = os.path.join(BASE_DIR, "AS_Assets", "fx_sheets")

# brightness: HDR bloom 베이크 배율 (GC 게임의 HDR post-processing 보상)
# sat_boost:  채도 강화 배율 (1.0=원본, 2.0=2배 채도)
# black_thresh: 이 값보다 큰 RGB 픽셀을 이펙트 픽셀로 판별 (0=모든 비순수검정 보존)
SPECS = [
    dict(folder="fx_valk_sk1_body",   output="fx_valk_sk1_body_sheet.png",
         fw=512, fh=512, cols=8, black_thresh=0, brightness=80.0, sat_boost=2.0),
    dict(folder="fx_valk_sk1_main",   output="fx_valk_sk1_main_sheet.png",
         fw=512, fh=512, cols=8, black_thresh=5, brightness=4.5, sat_boost=1.8),
    dict(folder="fx_valk_sk1_weapon", output="fx_valk_sk1_weapon_sheet.png",
         fw=512, fh=512, cols=8, black_thresh=5, brightness=4.0, sat_boost=1.6),
]


def boost_pixel(r: int, g: int, b: int, brightness: float, sat_boost: float):
    """밝기 부스트 + 채도 강화 (hue 비율 보존, soft clamp)"""
    # 채도 부스트 (HSV 공간에서)
    if sat_boost != 1.0 and (r or g or b):
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        s = min(1.0, s * sat_boost)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        r, g, b = int(r*255), int(g*255), int(b*255)

    # 밝기 부스트 (hue 비율 보존 soft clamp)
    if brightness != 1.0:
        r2, g2, b2 = r * brightness, g * brightness, b * brightness
        max_v = max(r2, g2, b2)
        if max_v > 255:
            scale = 255.0 / max_v
            r2, g2, b2 = r2 * scale, g2 * scale, b2 * scale
        r, g, b = int(r2), int(g2), int(b2)

    return r, g, b


def process_fx_frame(img: Image.Image, black_thresh: int,
                     brightness: float, sat_boost: float) -> Image.Image:
    """검정 배경 제거 + URP alpha=0 보정 + HDR bloom 베이크"""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > black_thresh or g > black_thresh or b > black_thresh:
                r, g, b = boost_pixel(r, g, b, brightness, sat_boost)
                pixels[x, y] = (r, g, b, 255)
            else:
                pixels[x, y] = (0, 0, 0, 0)
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

    fw, fh       = spec["fw"], spec["fh"]
    cols         = spec["cols"]
    thresh       = spec["black_thresh"]
    brightness   = spec["brightness"]
    sat_boost    = spec["sat_boost"]
    n            = len(frame_files)
    rows         = math.ceil(n / cols)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sheet = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))

    for i, fname in enumerate(frame_files):
        frame = Image.open(os.path.join(folder_path, fname)).convert("RGBA")
        frame = process_fx_frame(frame, thresh, brightness, sat_boost)
        if frame.size != (fw, fh):
            frame = frame.resize((fw, fh), Image.LANCZOS)
        col = i % cols
        row = i // cols
        sheet.paste(frame, (col * fw, row * fh), frame)

    out_path = os.path.join(OUTPUT_DIR, spec["output"])
    sheet.save(out_path, "PNG")
    print(f"  OK {spec['output']}  ({cols}x{rows}  {n}frames  {fw}x{fh}px"
          f"  bright={brightness}x  sat={sat_boost}x)")
    return True


def main():
    print("=" * 60)
    print("make_fx_sprites.py - E스킬 FX 스프라이트 시트 생성")
    print("=" * 60)

    if not os.path.isdir(FRAMES_DIR):
        print(f"[ERROR] 프레임 폴더 없음: {FRAMES_DIR}")
        print("ValkSkillCapture.cs 로 먼저 캡처를 진행하세요.")
        return

    ok = 0
    for spec in SPECS:
        print(f"\n  {spec['folder']}...")
        if make_sheet(spec):
            ok += 1

    print(f"\n{'=' * 60}")
    print(f"완료: {ok}/{len(SPECS)} 시트 생성됨")
    print(f"출력: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
