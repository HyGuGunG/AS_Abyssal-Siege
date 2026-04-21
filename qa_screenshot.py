"""
qa_screenshot.py — Abyssal Siege 전문 QA 자동화 시스템 v2
사용법: python qa_screenshot.py [local|pages]
출력:   qa_out/ 폴더에 PNG + _qa_report.txt

★ 심해 습격 특화 QA 항목 ★
  타이틀 / 드래프트 / 발키리 스프라이트·폴백 / 적 5종(배경제거)
  성문 HP / 가호 게이지 / 웨이브 시스템 / 시설 시스템
  피격·치명타 이펙트 / E스킬 / 자원 드랍 / JS 에러
"""
import os, sys, datetime
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

LOCAL_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "index.html"))
PAGES_URL  = "https://hygugung.github.io/AS_Abyssal-Siege/"
OUT_DIR    = os.path.join(os.path.dirname(__file__), "qa_out")
W, H       = 1280, 720

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QA 결과 수집
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_results = []

def _ok(cid, desc, detail=""):
    _results.append({"id": cid, "status": "PASS", "desc": desc, "detail": detail})
    suffix = f"  ({detail})" if detail else ""
    print(f"  ✅ [{cid}] {desc}{suffix}")

def _fail(cid, desc, detail=""):
    _results.append({"id": cid, "status": "FAIL", "desc": desc, "detail": detail})
    suffix = f"  [{detail}]" if detail else ""
    print(f"  ❌ [{cid}] {desc}{suffix}")

def _warn(cid, desc, detail=""):
    _results.append({"id": cid, "status": "WARN", "desc": desc, "detail": detail})
    suffix = f"  ({detail})" if detail else ""
    print(f"  ⚠️  [{cid}] {desc}{suffix}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 이미지 픽셀 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _region(img_path, x, y, w, h):
    arr = np.array(Image.open(img_path).convert("RGB"))
    return arr[y:y+h, x:x+w]

def nonblack(r, t=25):
    return int(((r[:,:,0]>t)|(r[:,:,1]>t)|(r[:,:,2]>t)).sum())

def bright(r, t=150):
    return int((r.max(axis=2)>t).sum())

def std(r):
    return float(r.astype(float).std())

def color_ratio(r, r0,r1, g0,g1, b0,b1):
    m=((r[:,:,0]>=r0)&(r[:,:,0]<=r1)&(r[:,:,1]>=g0)&(r[:,:,1]<=g1)&(r[:,:,2]>=b0)&(r[:,:,2]<=b1))
    return m.sum()/max(r.shape[0]*r.shape[1],1)

def no_black_box(img_path, x, y, w, h, limit=0.90):
    r = _region(img_path, x, y, w, h)
    dark = ((r[:,:,0]<20)&(r[:,:,1]<20)&(r[:,:,2]<20)).sum()
    ratio = dark / max(r.shape[0]*r.shape[1], 1)
    return float(ratio) <= limit, float(ratio)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Playwright 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def shot(page, name):
    path = f"{OUT_DIR}/{name}.png"
    page.screenshot(path=path)
    print(f"  [촬영] {name}.png")
    return path

def js(page, cid, desc, expr, expect=True):
    try:
        v = page.evaluate(expr)
        ((_ok if bool(v)==expect else _fail))(cid, desc, str(v))
    except Exception as e:
        _fail(cid, desc, f"평가오류: {e}")

def dom_ok(page, cid, desc, sel):
    try:
        vis = page.locator(sel).first.is_visible()
        (_ok if vis else _fail)(cid, desc, sel)
    except:
        _fail(cid, desc, f"{sel} 없음")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 QA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run(mode="pages"):
    os.makedirs(OUT_DIR, exist_ok=True)
    _results.clear()
    console_errs = []

    url = PAGES_URL if mode == "pages" else "file:///" + LOCAL_FILE.replace("\\", "/")
    print("\n" + "="*60)
    print("Abyssal Siege QA 자동 촬영 시작")
    print("="*60)
    print(f"  URL: {url}\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-web-security",
                  "--allow-file-access-from-files",
                  "--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": W, "height": H})
        page = ctx.new_page()
        page.on("console", lambda m: console_errs.append(f"[{m.type}] {m.text}")
                if m.type in ("error","warning") else None)
        page.on("pageerror", lambda e: console_errs.append(f"[pageerror] {e}"))

        # ─────────────────────────────────────────────────
        print("[ T. 타이틀 화면 ]")
        page.goto(url, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(2000)
        p = shot(page, "01_title")

        # DOM
        dom_ok(page, "T01", "게임 시작 버튼(#btnStart) 노출", "#btnStart")
        # 픽셀: 타이틀 텍스트·발키리 캐릭터 영역 (중앙)
        b_title = bright(_region(p, 300, 100, 680, 280), 170)
        (_ok if b_title>400 else _fail)("T02", "타이틀 텍스트/발키리 이미지 노출", f"밝은픽셀={b_title}")
        # 픽셀: 심해 배경 — 파란/청록 톤 비율 (>=30%)
        bg = _region(p, 0, 0, W, H)
        blue_ratio = color_ratio(bg, 0,100, 30,120, 80,220)   # 파랑 계열
        (_ok if blue_ratio>0.15 else _warn)("T03", "심해 배경 파란 톤 확인", f"blue_ratio={blue_ratio:.3f}")
        # JS
        js(page, "T04", "state.phase == 'title'", "state.phase === 'title'")

        # ─────────────────────────────────────────────────
        print("\n[ D. 드래프트 시스템 ]")
        page.click("#btnStart")
        # 드래프트 화면 최대한 빠르게 감지 (200ms 후 바로 시도)
        page.wait_for_timeout(200)
        draft_caught = False
        for _attempt in range(4):   # 최대 4회, 500ms 간격
            try:
                page.locator(".draft-card").first.wait_for(state="visible", timeout=1500)
                _ok("D01", "드래프트 카드 노출")
                p_d = shot(page, "02_draft_screen")
                r_d = _region(p_d, 160, 80, 960, 560)
                b_d = bright(r_d, 100)
                (_ok if b_d>2000 else _fail)("D02", "드래프트 카드 픽셀 내용 정상", f"밝은픽셀={b_d}")
                js(page, "D03", "state.phase == 'draft'", "state.phase === 'draft'")
                draft_caught = True
                break
            except:
                page.wait_for_timeout(500)
        if not draft_caught:
            _warn("D01", "드래프트 카드 미감지 — 즉시 게임 진입됐거나 selector 변경됨")

        # 드래프트 자동 선택 (최대 8회)
        for _ in range(8):
            try:
                c = page.locator(".draft-card").first
                c.wait_for(state="visible", timeout=600)
                c.click()
                page.wait_for_timeout(500)
            except:
                break
        page.wait_for_timeout(1500)
        p = shot(page, "03_game_start")

        # ─────────────────────────────────────────────────
        print("\n[ G. 게임 시작 · HUD ]")
        js(page, "G01", "state.phase == 'playing'", "state.phase === 'playing'")
        js(page, "G02", "state.running == true", "state.running === true")
        # 성문 HP (심해 습격의 '생명')
        gateHp = page.evaluate("typeof state !== 'undefined' ? state.gateHp : -1")
        gateMax = page.evaluate("typeof state !== 'undefined' ? state.gateHpMax : 1")
        if gateHp > 0:
            _ok("G03", f"성문 HP 정상", f"{gateHp}/{gateMax}")
        else:
            _fail("G03", "성문 HP 0 이하 (게임 오버 상태)", f"gateHp={gateHp}")
        # 가호 게이지 (발키리 → 성문 방어선)
        gauge = page.evaluate("typeof state !== 'undefined' ? state.gauge : -1")
        if gauge > 0:
            _ok("G04", "가호 게이지 정상", f"gauge={gauge:.1f}/100")
        else:
            _fail("G04", "가호 게이지 0 이하", f"gauge={gauge}")
        # 웨이브 번호
        wave = page.evaluate("typeof state !== 'undefined' ? state.wave : -1")
        waveMax = page.evaluate("typeof state !== 'undefined' ? state.waveMax : -1")
        (_ok if wave>=1 else _fail)("G05", f"웨이브 카운터 정상", f"wave={wave}/{waveMax}")
        # 시설 슬롯 (드래프트 결과)
        fac_cnt = page.evaluate("Array.isArray(state.facilitySlots) ? state.facilitySlots.length : 0")
        (_ok if fac_cnt>0 else _warn)("G06", "시설 슬롯 배정됨 (드래프트 결과)", f"슬롯수={fac_cnt}")
        # DOM: HUD 요소
        dom_ok(page, "G07", "WAVE HUD 노출 (#waveNum)", "#waveNum")
        dom_ok(page, "G08", "성문 HP 바 노출 (#gateHpBar)", "#gateHpBar")
        dom_ok(page, "G09", "가호 게이지 바 노출 (#playerGaugeTop)", "#playerGaugeTop")
        # 픽셀: 우상단 WAVE 텍스트
        b_wave = bright(_region(p, 880, 5, 320, 60), 160)
        (_ok if b_wave>50 else _fail)("G10", "우상단 WAVE HUD 픽셀 노출", f"밝은픽셀={b_wave}")
        # 픽셀: 좌상단 스탯 패널
        b_hud = bright(_region(p, 5, 30, 270, 180), 140)
        (_ok if b_hud>100 else _fail)("G11", "좌상단 스탯 HUD 픽셀 노출", f"밝은픽셀={b_hud}")
        # 스킬 정의 확인
        js(page, "G12", "E스킬(성검 폭풍) 정의됨", "typeof skills !== 'undefined' && typeof skills.E !== 'undefined'")
        js(page, "G13", "Q스킬(성창 질주) 정의됨", "typeof skills !== 'undefined' && typeof skills.Q !== 'undefined'")

        # ─────────────────────────────────────────────────
        print("\n[ V. 발키리 스프라이트 ]")
        # Canvas로 스프라이트 시트 픽셀 검증
        vk = page.evaluate("""
            (async()=>{
                const a=VALK_ANIMS&&VALK_ANIMS['idle'];
                if(!a) return {ok:false,err:'VALK_ANIMS 없음'};
                try{
                    const img=new Image(); img.crossOrigin='anonymous';
                    await new Promise(r=>{img.onload=img.onerror=r; img.src=a.src;});
                    const c=document.createElement('canvas'); c.width=a.fw; c.height=a.fh;
                    const ctx=c.getContext('2d'); ctx.drawImage(img,0,0,a.fw,a.fh,0,0,a.fw,a.fh);
                    const d=ctx.getImageData(0,0,a.fw,a.fh).data;
                    let cnt=0; for(let i=3;i<d.length;i+=4) if(d[i]>10) cnt++;
                    return {ok:cnt>100, pixelCount:cnt, fallback:window._valkFallbackMode};
                }catch(e){return {ok:null, err:String(e), fallback:window._valkFallbackMode};}
            })()
        """)
        if vk.get('ok') is True:
            _ok("V01", "발키리 스프라이트 시트 정상 (픽셀 있음)", f"pixelCount={vk.get('pixelCount')}")
        elif vk.get('fallback'):
            _warn("V01", "스프라이트 빈 이미지 → SD 폴백 작동 중 (Unity 재캡처 필요)", f"pixelCount={vk.get('pixelCount',0)}")
        else:
            _fail("V01", "스프라이트 픽셀 없음 + 폴백 미작동", str(vk))

        fb = page.evaluate("typeof _valkFallbackMode!=='undefined'?_valkFallbackMode:null")
        if fb is False:
            _ok("V02", "발키리: 정식 스프라이트 애니메이션 모드")
        elif fb is True:
            _warn("V02", "발키리: SD 폴백 모드 (재캡처 필요)")
        else:
            _warn("V02", "발키리 폴백 상태 변수 감지 불가")

        # 발키리 idle
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('idle')")
        page.wait_for_timeout(1000)
        p = shot(page, "04_valk_idle")
        # 픽셀: 플레이어 중앙 영역 — SD 폴백이어도 뭔가 보여야 함
        rp = _region(p, 530, 310, 220, 220)
        nb = nonblack(rp, 30); sd_p = std(rp)
        (_ok if nb>400 and sd_p>8 else _fail)("V03", "발키리 캐릭터 화면 노출", f"비검정={nb}, std={sd_p:.1f}")

        # 발키리 attack_r
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_r')")
        page.wait_for_timeout(500)
        p5 = shot(page, "05_valk_attack_r")
        (_ok if std(_region(p5,480,280,320,240))>12 else _fail)("V04", "발키리 attack_r 화면 노출")

        # 발키리 attack_l
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_l')")
        page.wait_for_timeout(500)
        p6 = shot(page, "06_valk_attack_l")
        (_ok if std(_region(p6,480,280,320,240))>12 else _fail)("V05", "발키리 attack_l 화면 노출")

        # GC 공격 이펙트 리소스 로드 확인
        gc_ok = page.evaluate("""
            (()=>{
                if(typeof GC_FX==='undefined') return {ok:false,err:'GC_FX 없음'};
                const keys=Object.keys(GC_FX);
                const loaded=keys.filter(k=>GC_FX[k]&&GC_FX[k].naturalWidth>0);
                return {ok:loaded.length>=3, total:keys.length, loaded:loaded.length};
            })()
        """)
        if gc_ok.get('ok'):
            _ok("V06", "GC 공격 이펙트 이미지 로드됨", f"{gc_ok.get('loaded')}/{gc_ok.get('total')}")
        else:
            _warn("V06", "GC 이펙트 이미지 로드 미확인", str(gc_ok))

        # ─────────────────────────────────────────────────
        print("\n[ E. 적 스프라이트 (5종) ]")
        for et in ["sogari","bangeo","gaori","agwi","bokeo"]:
            page.evaluate(f"if(typeof spawnEnemy==='function') spawnEnemy('{et}')")
            page.wait_for_timeout(300)
        page.wait_for_timeout(800)
        p7 = shot(page, "07_all_enemies")

        alive = page.evaluate("Array.isArray(enemies)?enemies.filter(e=>e&&e._alive).length:0")
        (_ok if alive>=5 else (_warn if alive>0 else _fail))("E01", f"적 5종 스폰", f"생존={alive}")

        # 픽셀: 아레나 영역 색상 다양성 (적 스프라이트 표시)
        ra = _region(p7, 130, 80, 1020, 440)
        sd_a = std(ra); nb_a = nonblack(ra)
        (_ok if sd_a>18 and nb_a>20000 else _fail)("E02", "적 스프라이트 색상 다양성 정상", f"std={sd_a:.1f}")

        # 검은 박스 감지 (이미지 로드 실패 패턴)
        bb_found = False
        for bx, by, bw, bh in [(180,80,180,180),(550,80,180,180),(900,80,180,180)]:
            ok_bb, ratio = no_black_box(p7, bx, by, bw, bh)
            if not ok_bb:
                _fail("E03", f"검은 박스 감지 — 이미지 로드 실패 ({bx},{by})", f"검정비율={ratio:.2f}")
                bb_found = True; break
        if not bb_found:
            _ok("E03", "적 스프라이트 배경 제거 정상 (검은 박스 없음)")

        # JS: ENEMY_DEFS 각 타입 이미지 경로 존재
        ed = page.evaluate("""
            (()=>{
                if(typeof ENEMY_DEFS==='undefined') return {ok:false};
                const miss=Object.entries(ENEMY_DEFS).filter(([k,v])=>!v.img).map(([k])=>k);
                return {ok:miss.length===0, missing:miss};
            })()
        """)
        (_ok if ed.get('ok') else _warn)("E04", "모든 적 이미지 경로 정의됨", str(ed.get('missing',[])))

        # ─────────────────────────────────────────────────
        print("\n[ W. 웨이브 진행 ]")
        page.wait_for_timeout(4000)
        p8 = shot(page, "08_wave_progress")

        wave2 = page.evaluate("typeof state!=='undefined'?state.wave:-1")
        (_ok if wave2>=1 else _fail)("W01", "웨이브 카운터 유효", f"wave={wave2}/{waveMax}")
        js(page, "W02", "성문 HP 아직 남아있음 (게임 지속)", "typeof state!=='undefined' && state.gateHp > 0")
        js(page, "W03", "state.running == true (게임 루프 동작)", "state.running === true")
        # 픽셀: 4초 후에도 콘텐츠 존재
        nb_w = nonblack(_region(p8, 130, 80, 1020, 440))
        (_ok if nb_w>15000 else _fail)("W04", "웨이브 진행 중 게임 화면 정상", f"비검정픽셀={nb_w}")

        # ─────────────────────────────────────────────────
        print("\n[ H. 피격 · 치명타 이펙트 ]")
        page.evaluate("""
            if(Array.isArray(enemies)&&enemies.length>0&&typeof dealDamage==='function')
                dealDamage(enemies[0],15,false);
        """)
        page.wait_for_timeout(250)
        p9 = shot(page, "09_hit_normal")
        b9 = bright(_region(p9, 130, 80, 1020, 440), 180)
        (_ok if b9>30 else _warn)("H01", "일반 피격 데미지 이펙트 노출", f"밝은픽셀={b9}")

        page.evaluate("""
            if(Array.isArray(enemies))
                enemies.slice(0,3).forEach(e=>{
                    if(e&&e._alive&&typeof dealDamage==='function') dealDamage(e,50,true);
                });
        """)
        page.wait_for_timeout(250)
        p10 = shot(page, "10_hit_crit")
        r10 = _region(p10, 130, 80, 1020, 440)
        b10 = bright(r10, 180)
        # 치명타 특유 오렌지/노란 색상 비율
        orange_r = color_ratio(r10, 180,255, 100,230, 0,100)
        (_ok if b10>50 else _warn)("H02", "치명타 피격 이펙트 노출", f"밝은픽셀={b10}, 오렌지={orange_r:.3f}")

        # JS: _particles 배열 또는 파티클 시스템 동작 확인
        pcount = page.evaluate("(typeof _particles!=='undefined'&&Array.isArray(_particles))?_particles.length:null")
        if pcount is not None:
            (_ok if pcount>=0 else _warn)("H03", "파티클 시스템 활성화됨", f"파티클수={pcount}")
        else:
            _warn("H03", "_particles 변수 미감지 (전역 노출 안됨)")

        # ─────────────────────────────────────────────────
        print("\n[ S. E스킬 (성검 폭풍) ]")
        page.evaluate("""
            if(typeof spawnESkillFx==='function'&&typeof player!=='undefined')
                spawnESkillFx(player.x||640,player.y||360)
        """)
        page.wait_for_timeout(500)
        p11 = shot(page, "11_eskill_fx")
        r11 = _region(p11, 300, 180, 680, 360)
        b11 = bright(r11, 160)
        gold_r = color_ratio(r11, 170,255, 150,255, 0,130)
        (_ok if b11>100 else _warn)("S01", "E스킬(성검 폭풍) 이펙트 노출", f"밝은픽셀={b11}, 골드={gold_r:.3f}")
        js(page, "S02", "spawnESkillFx 함수 존재", "typeof spawnESkillFx==='function'")
        # 스킬 쿨다운 리셋 가능 여부
        ecdmax = page.evaluate("typeof skills!=='undefined'&&skills.E?skills.E.max:null")
        (_ok if ecdmax and ecdmax>0 else _warn)("S03", "E스킬 쿨다운 설정 정상", f"max={ecdmax}s")

        # ─────────────────────────────────────────────────
        print("\n[ F. 게임플레이 종합 ]")
        page.wait_for_timeout(5000)
        p12 = shot(page, "12_gameplay_final")

        js(page, "F01", "5초 후 성문 HP 잔존 (게임 지속)", "typeof state!=='undefined'&&state.gateHp>0")
        js(page, "F02", "5초 후 game over 아님", "typeof state!=='undefined'&&state.phase==='playing'")
        js(page, "F03", "캐시 버스팅 _VER 적용됨", "typeof _VER!=='undefined'&&_VER.includes('?v=')")
        # 자원 드랍/킬 통계
        stats = page.evaluate("typeof state!=='undefined'?{kill:state.stats.kill,orb:state.stats.orb,crit:state.stats.crit}:{}")
        if stats:
            _ok("F04", "게임 통계 객체 존재", f"kill={stats.get('kill')}, orb={stats.get('orb')}, crit={stats.get('crit')}")
        else:
            _warn("F04", "게임 통계 미확인")
        # 픽셀: 최종 화면 정상 렌더링
        sf = std(_region(p12, 0, 0, W, H))
        (_ok if sf>20 else _fail)("F05", "최종 화면 정상 렌더링 (크래시/프리즈 없음)", f"std={sf:.1f}")

        # ─────────────────────────────────────────────────
        print("\n[ J. JS 런타임 에러 ]")
        browser.close()

    real_err = [e for e in console_errs if "[error]" in e.lower() or "[pageerror]" in e.lower()]
    warns    = [e for e in console_errs if "[warning]" in e.lower()]
    (_ok if not real_err else None)
    if not real_err:
        _ok("J01", "JS 런타임 에러 없음")
    else:
        for e in real_err[:3]:
            _fail("J01", "JS 런타임 에러 발생", e[:120])
    if not warns:
        _ok("J02", "JS 경고 없음")
    else:
        _warn("J02", f"JS 경고 {len(warns)}건", warns[0][:80])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 리포트 생성
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    total  = len(_results)
    passed = sum(1 for r in _results if r["status"]=="PASS")
    failed = sum(1 for r in _results if r["status"]=="FAIL")
    warned = sum(1 for r in _results if r["status"]=="WARN")

    cat_name = {
        "T":"타이틀 화면", "D":"드래프트 시스템", "G":"게임 시작·HUD·시설",
        "V":"발키리 스프라이트·이펙트", "E":"적 스프라이트(5종)",
        "W":"웨이브 진행", "H":"피격·치명타 이펙트",
        "S":"E스킬(성검 폭풍)", "F":"게임플레이 종합", "J":"JS 런타임"
    }
    lines = [
        "="*60,
        f"Abyssal Siege QA 리포트  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"URL: {url}",
        "="*60,
        f"총 {total}항목  |  ✅ PASS {passed}  |  ❌ FAIL {failed}  |  ⚠️  WARN {warned}",
        "",
    ]
    cats = {}
    for r in _results:
        cats.setdefault(r["id"][0], []).append(r)
    for cat, items in cats.items():
        lines.append(f"── {cat_name.get(cat, cat)} ──")
        for r in items:
            ic = "✅" if r["status"]=="PASS" else ("❌" if r["status"]=="FAIL" else "⚠️ ")
            line = f"  {ic} [{r['id']}] {r['desc']}"
            if r["detail"]: line += f"\n       └ {r['detail']}"
            lines.append(line)
        lines.append("")

    if console_errs:
        lines += ["── 콘솔 로그 ──"] + [f"  {e}" for e in console_errs[:20]] + [""]

    report = f"{OUT_DIR}/_qa_report.txt"
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    # _errors.txt 하위호환
    with open(f"{OUT_DIR}/_errors.txt", "w", encoding="utf-8") as f:
        fails = [r for r in _results if r["status"]=="FAIL"]
        if not fails and not real_err:
            f.write("에러 없음")
        else:
            f.write("\n".join(f"[{r['id']}] {r['desc']}: {r['detail']}" for r in fails) +
                    ("\n" + "\n".join(real_err) if real_err else ""))

    print()
    print("="*60)
    print(f"QA 완료: PASS {passed} / FAIL {failed} / WARN {warned}  (총 {total}항목)")
    print(f"리포트: {report}")
    if failed:
        print("\n❌ FAIL 목록:")
        for r in _results:
            if r["status"]=="FAIL":
                print(f"   [{r['id']}] {r['desc']}")
    print("="*60)
    return OUT_DIR

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pages"
    run(mode)
