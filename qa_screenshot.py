"""
qa_screenshot.py  --  Abyssal Siege 전문 QA 자동화 시스템
사용법: python qa_screenshot.py [local|pages]
출력:   qa_out/ 폴더에 PNG + qa_report.txt
"""
import os, sys, json, datetime
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

LOCAL_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "index.html"))
PAGES_URL  = "https://hygugung.github.io/AS_Abyssal-Siege/"
OUT_DIR    = os.path.join(os.path.dirname(__file__), "qa_out")
W, H       = 1280, 720

# ═══════════════════════════════════════════════════════════════════
# QA 결과 수집
# ═══════════════════════════════════════════════════════════════════
_results = []

def _ok(cid, desc, detail=""):
    _results.append({"id": cid, "status": "PASS", "desc": desc, "detail": detail})
    print(f"  ✅ {cid}: {desc}" + (f"  ({detail})" if detail else ""))

def _fail(cid, desc, detail=""):
    _results.append({"id": cid, "status": "FAIL", "desc": desc, "detail": detail})
    print(f"  ❌ {cid}: {desc}" + (f"  [{detail}]" if detail else ""))

def _warn(cid, desc, detail=""):
    _results.append({"id": cid, "status": "WARN", "desc": desc, "detail": detail})
    print(f"  ⚠️  {cid}: {desc}" + (f"  ({detail})" if detail else ""))

# ═══════════════════════════════════════════════════════════════════
# 이미지 픽셀 분석 유틸
# ═══════════════════════════════════════════════════════════════════
def _load_region(img_path, x, y, w, h):
    """PNG에서 특정 영역 numpy 배열(RGB) 반환"""
    arr = np.array(Image.open(img_path).convert("RGB"))
    return arr[y:y+h, x:x+w]

def nonblack_count(region, threshold=25):
    """배경 검정이 아닌 픽셀 수 (R|G|B > threshold)"""
    return int(((region[:,:,0] > threshold) | (region[:,:,1] > threshold) | (region[:,:,2] > threshold)).sum())

def bright_count(region, threshold=150):
    """밝은 픽셀 수 (max channel > threshold)  — 이펙트/텍스트 감지"""
    return int((region.max(axis=2) > threshold).sum())

def color_std(region):
    """색상 표준편차 — 낮으면 단색(깨진 이미지)"""
    return float(region.astype(float).std())

def dominant_color_ratio(region, r_min, r_max, g_min, g_max, b_min, b_max):
    """특정 색상 범위 픽셀 비율 — 이펙트 색상 확인"""
    mask = (
        (region[:,:,0] >= r_min) & (region[:,:,0] <= r_max) &
        (region[:,:,1] >= g_min) & (region[:,:,1] <= g_max) &
        (region[:,:,2] >= b_min) & (region[:,:,2] <= b_max)
    )
    return mask.sum() / max(region.shape[0] * region.shape[1], 1)

def has_no_black_box(img_path, x, y, w, h, max_dark_ratio=0.85):
    """
    이미지 로드 실패 검은 박스 감지.
    영역 내 검정 픽셀 비율이 max_dark_ratio 초과면 깨진 이미지로 판단.
    """
    region = _load_region(img_path, x, y, w, h)
    dark = ((region[:,:,0] < 20) & (region[:,:,1] < 20) & (region[:,:,2] < 20)).sum()
    ratio = dark / max(region.shape[0] * region.shape[1], 1)
    return ratio <= max_dark_ratio, float(ratio)

# ═══════════════════════════════════════════════════════════════════
# 스크린샷 촬영
# ═══════════════════════════════════════════════════════════════════
def shot(page, name):
    path = f"{OUT_DIR}/{name}.png"
    page.screenshot(path=path)
    print(f"  [촬영] {name}.png")
    return path

# ═══════════════════════════════════════════════════════════════════
# JS 상태 검증 헬퍼
# ═══════════════════════════════════════════════════════════════════
def js_check(page, cid, desc, expr, expect=True):
    """expr 평가 결과 == expect 이면 PASS"""
    try:
        result = page.evaluate(expr)
        if bool(result) == expect:
            _ok(cid, desc, str(result))
        else:
            _fail(cid, desc, f"결과={result}")
    except Exception as e:
        _fail(cid, desc, f"평가 오류: {e}")

def dom_visible(page, cid, desc, selector):
    """selector 가 visible 이면 PASS"""
    try:
        el = page.locator(selector).first
        if el.is_visible():
            _ok(cid, desc)
        else:
            _fail(cid, desc, f"{selector} 숨김")
    except Exception as e:
        _fail(cid, desc, f"{selector} 없음: {e}")

# ═══════════════════════════════════════════════════════════════════
# 메인 QA 실행
# ═══════════════════════════════════════════════════════════════════
def run(mode="pages"):
    os.makedirs(OUT_DIR, exist_ok=True)
    _results.clear()
    saved = []
    console_errors = []

    url = PAGES_URL if mode == "pages" else "file:///" + LOCAL_FILE.replace("\\", "/")
    print("\n" + "="*60)
    print("Abyssal Siege QA 자동 촬영 시작")
    print("="*60)
    print(f"  URL: {url}")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-web-security",
                  "--allow-file-access-from-files",
                  "--autoplay-policy=no-user-gesture-required"]
        )
        ctx = browser.new_context(viewport={"width": W, "height": H})
        page = ctx.new_page()

        page.on("console", lambda m: console_errors.append(f"[{m.type}] {m.text}")
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: console_errors.append(f"[pageerror] {e}"))

        # ──────────────────────────────────────────────────────────
        print("[ 01. 타이틀 화면 ]")
        page.goto(url, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(2000)
        p = shot(page, "01_title")
        saved.append(p)

        # DOM: 게임 시작 버튼 존재
        dom_visible(page, "T01", "게임 시작 버튼 노출", "#btnStart")
        # 픽셀: 타이틀 텍스트 영역 (화면 중앙 상단) 에 밝은 픽셀 존재
        r = _load_region(p, 320, 120, 640, 220)
        bc = bright_count(r, 180)
        if bc > 500:
            _ok("T02", "타이틀 텍스트/캐릭터 노출", f"밝은픽셀={bc}")
        else:
            _fail("T02", "타이틀 텍스트/캐릭터 미노출", f"밝은픽셀={bc}")
        # 배경 이미지 (전체 화면에 내용 있음)
        r_bg = _load_region(p, 0, 0, W, H)
        std = color_std(r_bg)
        if std > 20:
            _ok("T03", "배경 이미지 정상", f"std={std:.1f}")
        else:
            _fail("T03", "배경 이미지 미표시 (단색)", f"std={std:.1f}")

        # ──────────────────────────────────────────────────────────
        print("\n[ 02. 게임 시작 ]")
        page.click("#btnStart")
        page.wait_for_timeout(2500)
        p = shot(page, "02_game_start")
        saved.append(p)

        # DOM: HUD 요소
        dom_visible(page, "G01", "좌측 상단 HUD 패널 노출", "#hudLeft, #statsPanel, .hud-left, [id*='hud'], [class*='hud']")
        # JS: 게임 루프 시작
        js_check(page, "G02", "player 객체 존재", "typeof player !== 'undefined' && player !== null")
        js_check(page, "G03", "player.hp > 0 (생존 중)", "typeof player !== 'undefined' && player.hp > 0")
        js_check(page, "G04", "valkPlayAnim 함수 존재", "typeof valkPlayAnim === 'function'")
        js_check(page, "G05", "wave 변수 >= 1", "typeof wave !== 'undefined' && wave >= 1")
        # 픽셀: 우상단 WAVE HUD (텍스트 있어야 함)
        r_wave = _load_region(p, 880, 5, 320, 55)
        bc_wave = bright_count(r_wave, 160)
        if bc_wave > 50:
            _ok("G06", "WAVE HUD 텍스트 노출", f"밝은픽셀={bc_wave}")
        else:
            _fail("G06", "WAVE HUD 미표시", f"밝은픽셀={bc_wave}")
        # 픽셀: 좌상단 체력 HUD
        r_hp = _load_region(p, 5, 30, 270, 175)
        bc_hp = bright_count(r_hp, 140)
        if bc_hp > 100:
            _ok("G07", "좌측 HUD(체력/스탯) 노출", f"밝은픽셀={bc_hp}")
        else:
            _fail("G07", "좌측 HUD 미표시", f"밝은픽셀={bc_hp}")
        # 픽셀: 우하단 스킬 버튼
        r_skill = _load_region(p, 1050, 530, 230, 190)
        bc_sk = bright_count(r_skill, 100)
        if bc_sk > 200:
            _ok("G08", "우하단 스킬 버튼 노출", f"밝은픽셀={bc_sk}")
        else:
            _warn("G08", "우하단 스킬 버튼 확인 필요", f"밝은픽셀={bc_sk}")

        # ──────────────────────────────────────────────────────────
        print("\n[ 03. 드래프트 ]")
        # 드래프트 카드 노출 여부 먼저 체크
        try:
            card = page.locator(".draft-card").first
            card.wait_for(state="visible", timeout=2000)
            _ok("D01", "드래프트 카드 노출 확인")
            # 드래프트 화면 촬영
            p_draft = shot(page, "02b_draft_screen")
            saved.append(p_draft)
            r_draft = _load_region(p_draft, 200, 100, 880, 500)
            bc_d = bright_count(r_draft, 120)
            if bc_d > 1000:
                _ok("D02", "드래프트 카드 픽셀 내용 정상", f"밝은픽셀={bc_d}")
            else:
                _fail("D02", "드래프트 카드 미표시 의심", f"밝은픽셀={bc_d}")
        except Exception:
            _warn("D01", "드래프트 카드 없음 (이미 완료됐거나 미노출)")

        # 드래프트 자동 선택 (최대 8회)
        for _ in range(8):
            try:
                card = page.locator(".draft-card").first
                card.wait_for(state="visible", timeout=600)
                card.click()
                page.wait_for_timeout(500)
            except:
                break
        page.wait_for_timeout(1000)
        p = shot(page, "03_after_draft")
        saved.append(p)

        # ──────────────────────────────────────────────────────────
        print("\n[ 04. 발키리 스프라이트 ]")
        # 스프라이트 시트 픽셀 내용 검증 (Canvas 방식)
        valk_check = page.evaluate("""
            (async () => {
                const a = VALK_ANIMS && VALK_ANIMS['idle'];
                if(!a) return {hasPixels: false, error: 'VALK_ANIMS 없음'};
                try {
                    const img = new Image();
                    img.crossOrigin = 'anonymous';
                    await new Promise(res => { img.onload = img.onerror = res; img.src = a.src; });
                    const c = document.createElement('canvas');
                    c.width = a.fw; c.height = a.fh;
                    const ctx = c.getContext('2d');
                    ctx.drawImage(img, 0, 0, a.fw, a.fh, 0, 0, a.fw, a.fh);
                    const d = ctx.getImageData(0, 0, a.fw, a.fh).data;
                    let cnt = 0;
                    for(let i = 3; i < d.length; i += 4) if(d[i] > 10) cnt++;
                    return {hasPixels: cnt > 100, pixelCount: cnt, fallback: window._valkFallbackMode};
                } catch(e) {
                    return {hasPixels: null, error: String(e), fallback: window._valkFallbackMode};
                }
            })()
        """)
        if valk_check.get('hasPixels') is True:
            _ok("V01", "발키리 스프라이트 시트 픽셀 정상", f"pixelCount={valk_check.get('pixelCount')}")
        elif valk_check.get('fallback'):
            _warn("V01", "발키리 스프라이트 빈 이미지 → SD 폴백 작동 중", f"pixelCount={valk_check.get('pixelCount',0)}")
        else:
            _fail("V01", "발키리 스프라이트 픽셀 없음 + 폴백도 미작동", str(valk_check))

        # JS: fallback 모드 여부 기록
        fb_mode = page.evaluate("typeof _valkFallbackMode !== 'undefined' ? _valkFallbackMode : null")
        if fb_mode is False:
            _ok("V02", "발키리 스프라이트 모드: 정식 애니메이션")
        elif fb_mode is True:
            _warn("V02", "발키리 스프라이트 모드: SD 폴백 (재캡처 필요)")
        else:
            _warn("V02", "발키리 폴백 모드 변수 확인 불가")

        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('idle')")
        page.wait_for_timeout(1000)
        p = shot(page, "04_valk_idle")
        saved.append(p)

        # 픽셀: 플레이어 중앙 영역 (SD 폴백이라도 뭔가 보여야 함)
        r_player = _load_region(p, 540, 320, 200, 200)
        nbc = nonblack_count(r_player, 30)
        std_p = color_std(r_player)
        if nbc > 500 and std_p > 10:
            _ok("V03", "발키리/플레이어 캐릭터 화면 노출", f"비검정픽셀={nbc}, std={std_p:.1f}")
        else:
            _fail("V03", "발키리/플레이어 미표시 의심", f"비검정픽셀={nbc}, std={std_p:.1f}")

        # 발키리 attack_r / attack_l
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_r')")
        page.wait_for_timeout(500)
        p = shot(page, "05_valk_attack_r")
        saved.append(p)
        r_atk = _load_region(p, 480, 280, 320, 240)
        if color_std(r_atk) > 12:
            _ok("V04", "발키리 attack_r 화면 노출")
        else:
            _fail("V04", "발키리 attack_r 미표시 의심")

        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_l')")
        page.wait_for_timeout(500)
        p = shot(page, "06_valk_attack_l")
        saved.append(p)
        r_atk2 = _load_region(p, 480, 280, 320, 240)
        if color_std(r_atk2) > 12:
            _ok("V05", "발키리 attack_l 화면 노출")
        else:
            _fail("V05", "발키리 attack_l 미표시 의심")

        # ──────────────────────────────────────────────────────────
        print("\n[ 05. 적 스프라이트 ]")
        for etype in ["sogari", "bangeo", "gaori", "agwi", "bokeo"]:
            page.evaluate(f"if(typeof spawnEnemy==='function') spawnEnemy('{etype}')")
            page.wait_for_timeout(300)
        page.wait_for_timeout(800)
        p = shot(page, "07_all_enemies")
        saved.append(p)

        # JS: enemies 배열 길이 확인
        enemy_count = page.evaluate("Array.isArray(enemies) ? enemies.filter(e=>e&&e._alive).length : 0")
        if enemy_count >= 5:
            _ok("E01", f"적 {enemy_count}마리 스폰 확인")
        elif enemy_count > 0:
            _warn("E01", f"적 일부만 스폰됨 ({enemy_count}/5마리)", "일부 사망했거나 스폰 실패")
        else:
            _fail("E01", "적 스폰 실패 (0마리)")

        # 픽셀: 게임 중앙 영역에 다채로운 색상 (적 스프라이트)
        r_arena = _load_region(p, 130, 80, 1020, 440)
        std_arena = color_std(r_arena)
        nb_arena = nonblack_count(r_arena, 30)
        if std_arena > 18 and nb_arena > 20000:
            _ok("E02", "게임 영역 적 스프라이트 표시 (색상 다양성 정상)", f"std={std_arena:.1f}")
        else:
            _fail("E02", "게임 영역 단색 의심 (적 스프라이트 미표시)", f"std={std_arena:.1f}")

        # 픽셀: 검은 박스 감지 — 이미지 로드 실패 시 나타나는 패턴
        # 상단 적 출현 영역에서 90% 이상 검정인 64x64 블록 탐지
        enemy_zones = [(180, 80, 180, 180), (550, 80, 180, 180), (900, 80, 180, 180)]
        black_box_found = False
        for (ex, ey, ew, eh) in enemy_zones:
            ok_bb, ratio = has_no_black_box(p, ex, ey, ew, eh, max_dark_ratio=0.90)
            if not ok_bb:
                black_box_found = True
                _fail("E03", f"검은 박스 감지 — 이미지 로드 실패 의심 ({ex},{ey})", f"검정비율={ratio:.2f}")
                break
        if not black_box_found:
            _ok("E03", "적 스프라이트 배경 제거 정상 (검은 박스 없음)")

        # JS: 각 적 타입의 이미지 src가 존재하는지
        enemy_img_check = page.evaluate("""
            (()=>{
                const missing = [];
                if(typeof ENEMY_DEFS === 'undefined') return {ok: false, error: 'ENEMY_DEFS 없음'};
                Object.entries(ENEMY_DEFS).forEach(([k,v])=>{
                    if(!v.img) missing.push(k + ':img없음');
                });
                return {ok: missing.length === 0, missing};
            })()
        """)
        if enemy_img_check.get('ok'):
            _ok("E04", "모든 적 타입 이미지 경로 정의됨")
        else:
            _warn("E04", "일부 적 이미지 경로 미정의", str(enemy_img_check.get('missing', [])))

        # ──────────────────────────────────────────────────────────
        print("\n[ 06. 웨이브 진행 ]")
        page.wait_for_timeout(4000)
        p = shot(page, "08_wave_progress")
        saved.append(p)

        wave_val = page.evaluate("typeof wave !== 'undefined' ? wave : -1")
        if wave_val >= 1:
            _ok("W01", f"웨이브 카운터 정상 (wave={wave_val})")
        else:
            _fail("W01", "웨이브 카운터 이상", f"wave={wave_val}")

        js_check(page, "W02", "게임 루프 진행 중 (player 생존)", "typeof player!=='undefined' && player.hp > 0")

        # 픽셀: 웨이브 진행 중 화면에 변화 있어야 함 (적/이펙트 등)
        r_w = _load_region(p, 130, 80, 1020, 440)
        if nonblack_count(r_w) > 15000:
            _ok("W03", "웨이브 진행 중 게임 영역 콘텐츠 정상")
        else:
            _fail("W03", "웨이브 진행 중 게임 영역 비어있음")

        # ──────────────────────────────────────────────────────────
        print("\n[ 07. 피격 이펙트 ]")
        page.evaluate("""
            if(Array.isArray(enemies) && enemies.length>0 && typeof dealDamage==='function'){
                dealDamage(enemies[0], 15, false);
            }
        """)
        page.wait_for_timeout(250)
        p = shot(page, "09_hit_normal")
        saved.append(p)

        # 픽셀: 피격 데미지 숫자 (밝은 분홍/흰색) 게임 영역 어딘가 노출
        r_hit = _load_region(p, 130, 80, 1020, 440)
        bc_hit = bright_count(r_hit, 180)
        if bc_hit > 30:
            _ok("H01", "일반 피격 데미지 숫자/이펙트 노출", f"밝은픽셀={bc_hit}")
        else:
            _warn("H01", "일반 피격 이펙트 확인 필요", f"밝은픽셀={bc_hit}")

        # 치명타 피격
        page.evaluate("""
            if(Array.isArray(enemies)){
                enemies.slice(0,3).forEach(e=>{
                    if(e && e._alive && typeof dealDamage==='function')
                        dealDamage(e, 50, true);
                });
            }
        """)
        page.wait_for_timeout(250)
        p = shot(page, "10_hit_crit")
        saved.append(p)

        # 픽셀: 치명타는 노란/오렌지 밝은 파티클
        r_crit = _load_region(p, 130, 80, 1020, 440)
        bc_crit = bright_count(r_crit, 180)
        # 노란~오렌지 색상 비율 (R>180, G>100, B<80)
        orange_ratio = dominant_color_ratio(r_crit, 180, 255, 100, 220, 0, 100)
        if bc_crit > 50:
            _ok("H02", "치명타 피격 이펙트 노출", f"밝은픽셀={bc_crit}, 오렌지비율={orange_ratio:.3f}")
        else:
            _warn("H02", "치명타 이펙트 확인 필요", f"밝은픽셀={bc_crit}")

        # JS: rgba 파티클 color 포맷 검증 (이전에 발생했던 버그 재발 여부)
        particle_fmt_ok = page.evaluate("""
            (()=>{
                // _hitColors 에서 rgba 포맷 확인
                if(typeof _hitColors === 'undefined') return {ok: null, msg: '_hitColors 없음'};
                for(const [k,v] of Object.entries(_hitColors)){
                    if(v.endsWith(')')) return {ok: false, key: k, val: v, msg: '닫힌 괄호로 끝남 (포맷 버그)'};
                }
                return {ok: true};
            })()
        """)
        if particle_fmt_ok.get('ok') is True:
            _ok("H03", "_hitColors rgba 포맷 정상 (닫힌괄호 버그 없음)")
        elif particle_fmt_ok.get('ok') is False:
            _fail("H03", "_hitColors rgba 포맷 버그 감지", str(particle_fmt_ok))
        else:
            _warn("H03", "_hitColors 변수 확인 불가", str(particle_fmt_ok))

        # ──────────────────────────────────────────────────────────
        print("\n[ 08. E스킬 이펙트 ]")
        page.evaluate("""
            if(typeof spawnESkillFx==='function' && typeof player!=='undefined')
                spawnESkillFx(player.x||640, player.y||360)
        """)
        page.wait_for_timeout(500)
        p = shot(page, "11_eskill_fx")
        saved.append(p)

        # 픽셀: 중앙 영역에 골든 이펙트 (밝은 황금색 픽셀)
        r_esk = _load_region(p, 300, 200, 680, 340)
        bc_esk = bright_count(r_esk, 160)
        gold_ratio = dominant_color_ratio(r_esk, 170, 255, 150, 255, 0, 120)
        if bc_esk > 100:
            _ok("S01", "E스킬 이펙트 노출", f"밝은픽셀={bc_esk}, 골드비율={gold_ratio:.3f}")
        else:
            _warn("S01", "E스킬 이펙트 확인 필요 (밝기 부족)", f"밝은픽셀={bc_esk}")

        # JS: spawnESkillFx 함수 존재
        js_check(page, "S02", "spawnESkillFx 함수 정의됨", "typeof spawnESkillFx === 'function'")

        # ──────────────────────────────────────────────────────────
        print("\n[ 09. 게임플레이 종합 ]")
        page.wait_for_timeout(5000)
        p = shot(page, "12_gameplay_final")
        saved.append(p)

        js_check(page, "F01", "게임 루프 5초 후 player 생존", "typeof player!=='undefined' && player.hp > 0")
        js_check(page, "F02", "게임 루프 5초 후 게임 종료 안됨", "typeof gameOver==='undefined' || !gameOver")

        r_final = _load_region(p, 0, 0, W, H)
        std_final = color_std(r_final)
        if std_final > 20:
            _ok("F03", "최종 게임플레이 화면 정상", f"std={std_final:.1f}")
        else:
            _fail("F03", "최종 화면 단색 의심 (크래시/프리즈)", f"std={std_final:.1f}")

        # 캐시 버스팅 코드 존재 여부
        js_check(page, "F04", "캐시 버스팅 _VER 변수 존재", "typeof _VER !== 'undefined' && _VER.includes('?v=')")

        # ──────────────────────────────────────────────────────────
        print("\n[ 10. JS 콘솔 에러 집계 ]")
        browser.close()

    # 콘솔 에러를 QA 결과에 반영
    real_errors = [e for e in console_errors if '[error]' in e.lower() or '[pageerror]' in e.lower()]
    if not real_errors:
        _ok("JS01", "JS 런타임 에러 없음")
    else:
        for e in real_errors[:5]:
            _fail("JS01", "JS 런타임 에러 발생", e[:120])

    warnings = [e for e in console_errors if '[warning]' in e.lower()]
    if not warnings:
        _ok("JS02", "JS 경고 없음")
    else:
        _warn("JS02", f"JS 경고 {len(warnings)}건", warnings[0][:80] if warnings else "")

    # ═══════════════════════════════════════════════════════════════
    # 리포트 생성
    # ═══════════════════════════════════════════════════════════════
    total  = len(_results)
    passed = sum(1 for r in _results if r["status"] == "PASS")
    failed = sum(1 for r in _results if r["status"] == "FAIL")
    warned = sum(1 for r in _results if r["status"] == "WARN")

    lines = [
        "=" * 60,
        f"Abyssal Siege QA 리포트  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"URL: {url}",
        "=" * 60,
        f"총 {total}개 항목  |  PASS {passed}  |  FAIL {failed}  |  WARN {warned}",
        "",
    ]
    categories = {}
    for r in _results:
        cat = r["id"][0]
        categories.setdefault(cat, []).append(r)

    cat_names = {
        "T": "타이틀 화면", "G": "게임 시작/HUD", "D": "드래프트",
        "V": "발키리 스프라이트", "E": "적 스프라이트", "W": "웨이브 진행",
        "H": "피격 이펙트", "S": "E스킬", "F": "게임플레이 종합", "J": "JS 에러"
    }
    for cat, items in categories.items():
        lines.append(f"── {cat_names.get(cat, cat)} ──")
        for r in items:
            icon = "✅" if r["status"] == "PASS" else ("❌" if r["status"] == "FAIL" else "⚠️ ")
            line = f"  {icon} [{r['id']}] {r['desc']}"
            if r["detail"]:
                line += f"\n        └ {r['detail']}"
            lines.append(line)
        lines.append("")

    if console_errors:
        lines.append("── 콘솔 로그 ──")
        for e in console_errors[:20]:
            lines.append(f"  {e}")
        lines.append("")

    report_path = f"{OUT_DIR}/_qa_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 기존 _errors.txt 도 유지 (하위 호환)
    with open(f"{OUT_DIR}/_errors.txt", "w", encoding="utf-8") as f:
        fail_items = [r for r in _results if r["status"] == "FAIL"]
        if not fail_items and not real_errors:
            f.write("에러 없음")
        else:
            msgs = [f"[{r['id']}] {r['desc']}: {r['detail']}" for r in fail_items]
            msgs += real_errors
            f.write("\n".join(msgs))

    print()
    print("=" * 60)
    print(f"QA 완료: PASS {passed} / FAIL {failed} / WARN {warned}  (총 {total}항목)")
    print(f"리포트: {report_path}")
    print(f"스크린샷 {len(saved)}장: {OUT_DIR}")
    if failed > 0:
        print(f"\n❌ FAIL 항목:")
        for r in _results:
            if r["status"] == "FAIL":
                print(f"   [{r['id']}] {r['desc']}")
    print("=" * 60)
    return OUT_DIR


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pages"
    run(mode)
