# 현재 프로젝트 상태 (2026-04-21 기준)

## 파일 구조

```
C:\Users\wonil.cho.SUPERCAT\Desktop\Abyssal Siege\
├── index.html              # 게임 본체 (단일 HTML, ~7000줄)
├── spec.html               # 기획서 v2.5
├── README.md               # GitHub README
├── abyssal-siege.zip       # 오프라인 배포용 ZIP
├── make_fx_sprites.py      # 이펙트 스프라이트 시트 생성 스크립트
├── .git/                   # Git 저장소 (origin: GitHub)
└── AS_Assets/
    ├── bg/
    │   └── castle_gate.png
    ├── characters/
    │   ├── valkyrie_idle_front.png         # SD 발키리 — 방향별 스프라이트
    │   ├── valkyrie_idle_back.png
    │   ├── valkyrie_idle_right.png
    │   ├── valkyrie_move_front.png
    │   ├── valkyrie_move_back.png
    │   ├── valkyrie_move_right.png
    │   ├── valkyrie_attack_front.png
    │   ├── valkyrie_attack_back.png
    │   ├── valkyrie_attack_right.png
    │   └── valkyrie_skill_e.png            # E스킬 모션
    ├── enemies/
    │   ├── sogari.png / bangeo.png / gaori.png / agwi.png / bokeo.png / kraken.png
    ├── gate/
    │   └── castle_gate_object.png
    ├── items/
    │   ├── oxygen.png / repairkit.png / resource_normal.png / resource_rare.png / resource_epic.png
    ├── skills/
    │   ├── wind_dash.png / holy_shock.png
    ├── fx_frames/                          # Unity 원본 캡처 프레임 (폴더별)
    │   ├── valk_sk1_main/ (75프레임)
    │   ├── valk_sk1_body/ (60프레임)
    │   ├── valk_sk1_weapon/ (60프레임)
    │   └── ... (기타 이펙트 폴더들)
    ├── fx_sheets/                          # 처리된 스프라이트 시트 PNG
    │   ├── fx_valk_sk1_main_sheet.png     # 512×512 × 75프레임 (origin-centered)
    │   ├── fx_valk_sk1_body_sheet.png     # 512×512 × 60프레임
    │   ├── fx_valk_sk1_weapon_sheet.png   # 512×512 × 60프레임
    │   └── ... (기타 이펙트 시트들)
    └── screenshots/
        ├── ss_title.png / ss_gameplay.png / ss_carddraft.png
        ├── ss_boss.png / ss_result.png / ss_facilitydraft.png
```

## Git 상태

- **브랜치**: main
- **리모트**: https://github.com/HyGuGunG/AS_Abyssal-Siege.git
- **최신 커밋**: `a2b7552` — fix: 게임플레이/타이틀 스크린샷 재촬영
- **미커밋 변경**: index.html (v1.8.0 업데이트 + E스킬 이펙트 수정)
- **GitHub Pages**: 활성화됨

## 라이브 URL

| 페이지 | URL |
|--------|-----|
| 게임 플레이 | https://hygugung.github.io/AS_Abyssal-Siege/ |
| 기획서 | https://hygugung.github.io/AS_Abyssal-Siege/spec.html |
| ZIP 다운로드 | https://hygugung.github.io/AS_Abyssal-Siege/abyssal-siege.zip |
| GitHub 리포 | https://github.com/HyGuGunG/AS_Abyssal-Siege |

## 주요 게임 수치 (index.html v1.8.0 기준)

### 플레이어
- 공격력: 22, 공속: 0.65s, 사거리: 200px, 이동속도: 220px/s
- 수문 HP: 1500
- 아이템 흡입 반경: 140px

### 발키리 애니메이션 시스템
- 방향: front / back / right (left는 right 좌우반전)
- 상태: idle / move / attack / skill_e
- 스프라이트 시트: 각 `AS_Assets/characters/valkyrie_[state]_[dir].png`
- `valkPlayAnim(animName)` 함수로 제어

### E스킬 이펙트 (VALK_SK1_ANIMS)
```javascript
const VALK_SK1_ANIMS = {
  main:   { src:'AS_Assets/fx_sheets/fx_valk_sk1_main_sheet.png',   fw:512, fh:512, cols:8, frames:75, fps:30 },
  body:   { src:'AS_Assets/fx_sheets/fx_valk_sk1_body_sheet.png',   fw:512, fh:512, cols:8, frames:60, fps:30 },
  weapon: { src:'AS_Assets/fx_sheets/fx_valk_sk1_weapon_sheet.png', fw:512, fh:512, cols:8, frames:60, fps:30 },
};
// 표시 크기: main=460×460, body=320×320, weapon=320×320
// origin-centered: Unity 원점이 프레임 중앙(256,256)에 위치 → 플레이어 좌표에 정확히 겹침
```

### Wave 스케일링
- 적 HP: +12% / Wave (보스 제외)
- 적 피해: +8% / Wave (보스 제외)

### 드랍 확률
- 가호 보주: 적 처치 시 orbRate × 0.72 (기본 orbRate: 적별 상이)
- 건설 자원: 50% (drops 정의된 적만)
