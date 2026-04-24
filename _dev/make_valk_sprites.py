"""
make_valk_sprites.py
Abyssal Siege — 발키리 스프라이트 시트 생성 스크립트

사용법:
    python make_valk_sprites.py

입력:  AS_Assets/valk_frames/<folder>/frame_XXXX.png
출력:  AS_Assets/valk2_<name>_sheet.png

원리:
- 마젠타(#FF00FF) 배경 크로마키 제거 → 알파 투명 처리
- origin-centered 방식: 프레임 크기(fw×fh) 고정 유지 (tight-crop 없음)
  → 플레이어 위치와 스프라이트가 정확히 정렬됨
- 스프라이트 시트: cols × ceil(frames/cols) 행으로 배치

칼 끝 잘림 주의:
  attack_l/r 의 fw=720px — 크로마키 후에도 칼 끝이 프레임 내에 있어야 함
  만약 잘린다면 ValkyrieCapture2.cs의 orthoSize/camDist 조정 필요
"""

import os
import math
from PIL import Image

# ══ 경로 설정 ════════════════════════════════════════════════════════════
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR  = os.path.join(BASE_DIR, "AS_Assets", "valk_frames")
OUTPUT_DIR  = os.path.join(BASE_DIR, "AS_Assets")

# ══ 크로마키 설정 ════════════════════════════════════════════════════════
# 마젠타 (#FF00FF) 판별: R > THRESH AND G < 120 AND B > THRESH
CHROMA_THRESHOLD = 130

# ══ 스프라이트 시트 스펙 ════════════════════════════════════════════════
# folder: valk_frames 하위 폴더명
# output: 출력 파일명 (AS_Assets/ 아래)
# fw, fh: 프레임 해상도 (ValkyrieCapture2.cs와 일치시킬 것)
# cols: 시트 열 수
SPECS = [
    dict(folder="valk2_idle",     output="valk2_idle_sheet.png",     fw=340, fh=420, cols=6),
    dict(folder="valk2_attack_f", output="valk2_attack_f_sheet.png", fw=500, fh=560, cols=6),
    dict(folder="valk2_attack_l", output="valk2_attack_l_sheet.png", fw=1024, fh=560, cols=6),  # 시각 우향
    dict(folder="valk2_attack_r", output="valk2_attack_r_sheet.png", fw=1024, fh=580, cols=6),  # 시각 좌향
    dict(folder="valk2_skill",    output="valk2_skill_sheet.png",    fw=500, fh=560, cols=6),
    dict(folder="valk2_move_l",   output="valk2_move_l_sheet.png",   fw=260, fh=500, cols=6),  # 시각 우향
    dict(folder="valk2_move_r",   output="valk2_move_r_sheet.png",   fw=260, fh=460, cols=6),  # 시각 좌향
]


def remove_chroma(img: Image.Image) -> Image.Image:
    """마젠타 배경을 알파 투명으로 변환 (URP alpha=0 보정 포함)"""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > CHROMA_THRESHOLD and g < 120 and b > CHROMA_THRESHOLD:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (r, g, b, 255)  # URP가 alpha=0으로 클리어하므로 강제 복구
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

        # 크로마키 제거 먼저 (리사이즈 전에 해야 함)
        # 리사이즈를 먼저 하면 PIL이 alpha=0 상태에서 premultiplied 블렌딩을 해
        # RGB까지 0으로 만들어버려 크로마키 조건(R>130)을 통과 못함 → 100% fill 버그
        frame = remove_chroma(frame)

        # 크기 불일치 시 리사이즈 (크로마키 후 리사이즈해야 엣지 블렌딩 정상)
        if frame.size != (fw, fh):
            frame = frame.resize((fw, fh), Image.LANCZOS)

        col = i % cols
        row = i // cols
        sheet.paste(frame, (col * fw, row * fh), frame)

    out_path = os.path.join(OUTPUT_DIR, spec["output"])
    sheet.save(out_path, "PNG")
    print(f"  ✓ {spec['output']}  ({cols}×{rows}  {n_frames}frames  {fw}×{fh}px)")
    return True


def main():
    print("=" * 60)
    print("make_valk_sprites.py — 발키리 스프라이트 시트 생성")
    print("=" * 60)

    if not os.path.isdir(FRAMES_DIR):
        print(f"[ERROR] 프레임 폴더가 없습니다: {FRAMES_DIR}")
        print("ValkyrieCapture2.cs 로 먼저 캡처를 진행하세요.")
        return

    ok_count = 0
    for spec in SPECS:
        print(f"\n▶ {spec['folder']}")
        if make_sheet(spec):
            ok_count += 1

    print(f"\n{'=' * 60}")
    print(f"완료: {ok_count}/{len(SPECS)} 시트 생성됨")
    print(f"출력 위치: {OUTPUT_DIR}")
    print()
    print("[다음 단계]")
    print("index.html의 VALK_ANIMS fw/fh 값을 아래와 맞게 확인:")
    for sp in SPECS:
        key = sp["folder"].replace("valk2_", "")
        print(f"  {key}: fw:{sp['fw']}, fh:{sp['fh']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
