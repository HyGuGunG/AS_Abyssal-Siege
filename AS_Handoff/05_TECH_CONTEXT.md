# 기술 컨텍스트 (2026-04-21 기준)

## 게임 아키텍처 (index.html)

### 구조
- **단일 HTML 파일** (CSS + JS 인라인, ~7000줄)
- Canvas 2D: 파티클, 이펙트, 투사체 렌더링
- DOM: 적/아이템/UI 요소 (`.obj` 클래스로 world div 내 배치)
- 해상도: 1280×720 고정

### 핵심 변수/상수
```javascript
const W = 1280, H = 720;
const ASSET = 'AS_Assets/';
const ENEMY_DEFS = { sogari, bangeo, gaori, agwi, bokeo };
const WAVE_DEFS = [ /* 7개: W1~W6 일반 + W7 보스 */ ];
const CARD_POOL = [ /* 영웅 카드 11종 */ ];
const FACILITY_POOL = [ /* 시설 카드 6종 */ ];
const FACILITY_SLOT_DEFS = [ /* 비용: 25,55,100,100,200 */ ];
const VALK_SK1_ANIMS = { main, body, weapon };  // E스킬 이펙트
```

### 게임 루프
```
requestAnimationFrame → update(dt) → render
  ├── updateEnemies()    — 적 이동/공격
  ├── updatePlayer()     — 플레이어 이동/자동공격
  ├── updateItems()      — 드랍 아이템 수집
  ├── updateFacilities() — 시설 공격
  ├── updateBoss()       — 보스 AI (페이즈/패턴)
  └── updateHUD()        — UI 갱신
```

### 충돌 판정
- Edge-based: `Math.hypot(dx, dy) - enemy.r` (히트박스 반경 차감)
- 수문 충돌: 적이 수문 Y좌표 도달 시 접촉피해

### 치트키 (개발용)
- `K`: 현재 적 전멸
- `L`: 웨이브 스킵
- `O`: 강제 패배

## 발키리 스프라이트 시스템

### 애니메이션 상태
```javascript
// 방향: front / back / right (left는 right를 CSS scaleX(-1)로 반전)
// 상태: idle / move / attack / skill_e
// 파일: AS_Assets/characters/valkyrie_[state]_[dir].png
valkPlayAnim(animName);  // 'idle', 'move_right', 'attack_front', 'skill_e' 등
```

### 발키리 CSS 핵심
```css
#player { width:100px; height:100px; position:absolute; z-index:18 }
#player .valk-sprite { filter:drop-shadow(0 0 12px rgba(0,229,255,.6)) }
```

### 알려진 버그
- 정면(front) 공격 스프라이트가 다른 방향보다 크기 작음
- E스킬 모션이 마지막 프레임만 표시되는 현상
- 뒤돌아보기 애니메이션이 의도치 않게 재생되는 케이스 존재

## GC 이펙트 파이프라인

### 1단계: Unity 캡처 (EffectCaptureValkSk1.cs)
```
위치: grandcross-client/Assets/02.Scripts/EffectCaptureValkSk1.cs
메뉴: Tools → Effect Capture → ▶ Valk SK1 ScreenCapture (Play Mode)
출력: C:\Users\wonil.cho.SUPERCAT\Desktop\Abyssal Siege\AS_Assets\fx_frames\
```
- Game View를 512×512 해상도로 설정 후 실행
- **중요**: Game View에서 "Gizmos" 버튼 반드시 끌 것 (기즈모가 프레임에 포함됨)
- 마젠타(#FF00FF) 배경으로 캡처 (발키리 이펙트는 초록 파티클 사용 → 그린스크린 충돌 방지)
- valk_sk1_main(2.5초=75프레임), body(2.0초=60프레임), weapon(2.0초=60프레임)

### 2단계: Python 처리 (make_fx_sprites.py)
```
위치: C:\Users\wonil.cho.SUPERCAT\Desktop\Abyssal Siege\make_fx_sprites.py
실행: python make_fx_sprites.py
출력: AS_Assets/fx_sheets/fx_[name]_sheet.png
```
- 마젠타 크로마키 제거 (R>130 AND G<120 AND B>130)
- **origin-centered 방식**: Unity 원점(0,0) = 프레임 중앙(256,256)으로 고정
  → tight_crop 사용 안 함 → 플레이어 위치에 정확히 정렬
- CHROMA_THRESHOLD = 130, SHEET_COLS = 8

### 3단계: 게임 적용 (index.html)
```javascript
const VALK_SK1_ANIMS = {
  main:   { src:'AS_Assets/fx_sheets/fx_valk_sk1_main_sheet.png',   fw:512, fh:512, cols:8, frames:75, fps:30 },
  body:   { src:'AS_Assets/fx_sheets/fx_valk_sk1_body_sheet.png',   fw:512, fh:512, cols:8, frames:60, fps:30 },
  weapon: { src:'AS_Assets/fx_sheets/fx_valk_sk1_weapon_sheet.png', fw:512, fh:512, cols:8, frames:60, fps:30 },
};

// playValkSprite(x, y, src, dispW, dispH, fw, fh, cols, frames, fps, filter, flipX)
// 위치 계산: left = x - dispW/2, top = y - dispH/2
// origin(256,256) → scale 460/512 → 화면 좌표 (x, y) 완전 정렬
```

## 오디오 시스템

### BGM (Chrome 미디어 오버레이 방지)
- 3.8초 코드(chord) 단위로 재생 후 AudioContext.suspend()
- Chrome이 '재생 중' 상태로 인식하지 못하도록 하여 스피커/슬라이더 오버레이 방지
- `_scheduleBGMChord()` → 3.8s 재생 → suspend() → 0.2s 대기 → 반복

### SFX
```javascript
playTone(freq, duration, type, vol)  // 오실레이터 기반 효과음
playNoise(duration, vol)             // 화이트노이즈 (피격음 등)
// 모두 ctx.resume() 호출 후 재생 (suspend 상태 안전 처리)
```

## 기획서 아키텍처 (spec.html)

### 구조
- 단일 HTML, CSS 인라인, 하단에 JS (캐러셀 + 네비게이션)
- 섹션: hero → concept → trigger → difficulty → gameplay → enemies → systems → boss → reward

### CSS 핵심 클래스
```css
.glass          — 반투명 카드 컨테이너
.badge .b-teal  — 일반 등급 (초록)
.badge .b-amber — 희귀 등급 (주황)
.badge .b-violet — 영웅 등급 (보라)
.badge .b-cyan  — 시안 강조
.badge .b-coral — 위험/경고 (빨강)
.carousel-wrap  — 스크린샷 캐러셀 (6장)
.badge-upcoming — 업데이트 예정 펄싱 뱃지
```

## 자동화 파이프라인

### QA 스크린샷
```powershell
# headless Chrome (PowerShell)
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' `
  --headless=new --screenshot='경로.png' --window-size=1280,720 --disable-gpu 'file:///...'
# 확인 후 즉시 삭제 (피드백 정책)
```

### ZIP 패키징
```powershell
Compress-Archive -Path 'index.html','AS_Assets','make_fx_sprites.py' `
  -DestinationPath 'abyssal-siege.zip' -Force
```

### GitHub 배포
```bash
cd "C:/Users/wonil.cho.SUPERCAT/Desktop/Abyssal Siege"
git add [파일들]
git commit -m "메시지"
git push origin main
# GitHub Pages 자동 배포 (1~2분 소요)
```

## 주의사항

- **gh auth**: 현재 CLI 인증 안 됨. GitHub API 작업은 브라우저에서 수행
- **ESET**: 임시 스크립트 파일 작성 시 ESET 백신 탐지 가능. /tmp 대신 프로젝트 폴더 내 작성 후 삭제
- **git 설정**: Abyssal Siege 폴더는 grandcross-client와 별도 git 저장소. 혼동 주의
- **Unity 캡처 시**: Game View "Gizmos" 반드시 OFF (ON이면 기즈모 기즈모가 프레임에 포함됨)
