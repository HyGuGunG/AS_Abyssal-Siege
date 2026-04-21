"""
qa_screenshot.py  --  Abyssal Siege 자동 QA 스크린샷 시스템
사용법: python qa_screenshot.py
출력:   qa_out/ 폴더에 PNG 저장
"""
import os
from playwright.sync_api import sync_playwright

GAME_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "index.html"))
OUT_DIR   = os.path.join(os.path.dirname(__file__), "qa_out")
W, H      = 1280, 720

def shot(page, name):
    path = f"{OUT_DIR}/{name}.png"
    page.screenshot(path=path)
    print(f"  [촬영] {name}.png")
    return path

def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    saved = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-web-security",
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
        url = "file:///" + GAME_FILE.replace("\\", "/")
        page.goto(url, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(1500)
        saved.append(shot(page, "01_title"))

        # ── 게임 시작 ──
        page.click("#btnStart")
        page.wait_for_timeout(2000)  # 화면전환 + 드래프트 대기
        saved.append(shot(page, "02_after_start"))

        # 드래프트 화면이면 첫 카드 자동 선택
        for _ in range(6):  # 최대 6회 드래프트
            try:
                card = page.locator(".draft-card").first
                card.wait_for(state="visible", timeout=800)
                card.click()
                page.wait_for_timeout(600)
            except:
                break
        page.wait_for_timeout(800)
        saved.append(shot(page, "03_draft_done"))

        # ── 발키리 아이들 ──
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('idle')")
        page.wait_for_timeout(600)
        saved.append(shot(page, "04_valk_idle"))

        # ── 발키리 attack_r / attack_l ──
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_r')")
        page.wait_for_timeout(400)
        saved.append(shot(page, "05_valk_attack_r"))
        page.evaluate("if(typeof valkPlayAnim==='function') valkPlayAnim('attack_l')")
        page.wait_for_timeout(400)
        saved.append(shot(page, "06_valk_attack_l"))

        # ── 적 스폰 ──
        for etype in ["sogari","bangeo","gaori","agwi","bokeo"]:
            page.evaluate(f"if(typeof spawnEnemy==='function') spawnEnemy('{etype}')")
            page.wait_for_timeout(200)
        page.wait_for_timeout(600)
        saved.append(shot(page, "07_enemies_spawned"))

        # ── 웨이브 진행 ──
        page.wait_for_timeout(3500)
        saved.append(shot(page, "08_wave_progress"))

        # ── E스킬 이펙트 ──
        page.evaluate("""
            if(typeof spawnESkillFx==='function' && typeof player!=='undefined')
                spawnESkillFx(player.x||640, player.y||360)
        """)
        page.wait_for_timeout(400)
        saved.append(shot(page, "09_eskill_fx"))

        # ── 피격 이펙트 ──
        page.evaluate("""
            if(Array.isArray(enemies) && enemies[0] && typeof dealDamage==='function')
                dealDamage(enemies[0], 15, false);
        """)
        page.wait_for_timeout(200)
        saved.append(shot(page, "10_hit_fx"))

        # ── 치명타 피격 ──
        page.evaluate("""
            if(Array.isArray(enemies) && enemies[0] && typeof dealDamage==='function')
                dealDamage(enemies[0], 50, true);
        """)
        page.wait_for_timeout(200)
        saved.append(shot(page, "11_crit_fx"))

        # ── 게임오버 직전 상태 ──
        page.wait_for_timeout(5000)
        saved.append(shot(page, "12_gameplay_late"))

        browser.close()

    # 에러 리포트
    report_path = f"{OUT_DIR}/_errors.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(errors) if errors else "에러 없음")

    print(f"\n총 {len(saved)}장 저장: {OUT_DIR}")
    if errors:
        print(f"콘솔 에러/경고 {len(errors)}건")
    return OUT_DIR

if __name__ == "__main__":
    run()
