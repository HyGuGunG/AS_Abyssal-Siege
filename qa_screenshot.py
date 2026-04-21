"""
qa_screenshot.py  --  Abyssal Siege 자동 QA 스크린샷 시스템
사용법: python qa_screenshot.py [local|pages]
출력:   qa_out/ 폴더에 PNG 저장
"""
import os, sys
from playwright.sync_api import sync_playwright

LOCAL_FILE  = os.path.abspath(os.path.join(os.path.dirname(__file__), "index.html"))
PAGES_URL   = "https://hygugung.github.io/AS_Abyssal-Siege/"
OUT_DIR     = os.path.join(os.path.dirname(__file__), "qa_out")
W, H        = 1280, 720

def shot(page, name):
    path = f"{OUT_DIR}/{name}.png"
    page.screenshot(path=path)
    print(f"  [촬영] {name}.png")
    return path

def run(mode="pages"):
    os.makedirs(OUT_DIR, exist_ok=True)
    saved = []

    url = PAGES_URL if mode == "pages" else "file:///" + LOCAL_FILE.replace("\\", "/")
    print(f"  URL: {url}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox",
                  "--disable-web-security",
                  "--allow-file-access-from-files",
                  "--autoplay-policy=no-user-gesture-required"]
        )
        ctx = browser.new_context(viewport={"width": W, "height": H})
        page = ctx.new_page()

        errors = []
        page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}")
                if m.type in ("error","warning") else None)
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

        # ── 타이틀 ──
        page.goto(url, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(2000)
        saved.append(shot(page, "01_title"))

        # ── 게임 시작 ──
        page.click("#btnStart")
        page.wait_for_timeout(2500)
        saved.append(shot(page, "02_game_start"))

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
        saved.append(shot(page, "03_after_draft"))

        # ── 발키리 스프라이트 시트 로드 대기 ──
        page.evaluate("""
            (async () => {
                const srcs = Object.values(VALK_ANIMS || {}).map(a => a.src);
                await Promise.all(srcs.map(src => new Promise(res => {
                    const img = new Image();
                    img.onload = img.onerror = res;
                    img.src = src;
                })));
            })()
        """)
        page.wait_for_timeout(1500)

        # ── 발키리 idle ──
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('idle')")
        page.wait_for_timeout(1000)
        saved.append(shot(page, "04_valk_idle"))

        # ── 발키리 attack_r / attack_l ──
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_r')")
        page.wait_for_timeout(500)
        saved.append(shot(page, "05_valk_attack_r"))
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_l')")
        page.wait_for_timeout(500)
        saved.append(shot(page, "06_valk_attack_l"))

        # ── 적 스폰 (각 타입별) ──
        for etype in ["sogari", "bangeo", "gaori", "agwi", "bokeo"]:
            page.evaluate(f"if(typeof spawnEnemy==='function') spawnEnemy('{etype}')")
            page.wait_for_timeout(300)
        page.wait_for_timeout(800)
        saved.append(shot(page, "07_all_enemies"))

        # ── 웨이브 진행 (4초) ──
        page.wait_for_timeout(4000)
        saved.append(shot(page, "08_wave_progress"))

        # ── 피격 이펙트 (일반) ──
        page.evaluate("""
            if(Array.isArray(enemies) && enemies.length>0 && typeof dealDamage==='function'){
                dealDamage(enemies[0], 15, false);
            }
        """)
        page.wait_for_timeout(250)
        saved.append(shot(page, "09_hit_normal"))

        # ── 치명타 피격 (가능한 모든 적) ──
        page.evaluate("""
            if(Array.isArray(enemies)){
                enemies.slice(0,3).forEach(e=>{
                    if(e && e._alive && typeof dealDamage==='function')
                        dealDamage(e, 50, true);
                });
            }
        """)
        page.wait_for_timeout(250)
        saved.append(shot(page, "10_hit_crit"))

        # ── E스킬 이펙트 ──
        page.evaluate("""
            if(typeof spawnESkillFx==='function' && typeof player!=='undefined')
                spawnESkillFx(player.x||640, player.y||360)
        """)
        page.wait_for_timeout(500)
        saved.append(shot(page, "11_eskill_fx"))

        # ── 게임플레이 (5초 후 전체 상황) ──
        page.wait_for_timeout(5000)
        saved.append(shot(page, "12_gameplay_final"))

        browser.close()

    # 에러 리포트
    report_path = f"{OUT_DIR}/_errors.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(errors) if errors else "에러 없음")

    print(f"\n총 {len(saved)}장 저장: {OUT_DIR}")
    if errors:
        print(f"콘솔 에러/경고 {len(errors)}건 → {report_path}")
    return OUT_DIR

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "pages"
    run(mode)
