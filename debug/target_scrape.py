import asyncio, json, time, sys, os
sys.path.insert(0, r'D:\gdx\kaoshibao')
os.chdir(r'D:\gdx\kaoshibao')

from playwright.async_api import async_playwright
from scraper_core import (
    _navigate_to_practice, _init_recite_mode, get_current_question,
    wait_for_question, close_popups, check_login_required, _is_valid_question_text
)

PAPER_ID = '13573440'
LOG_FILE = r'D:\gdx\kaoshibao\debug\target_scrape.log'
OUTPUT_FILE = r'D:\gdx\kaoshibao\debug\target_results.json'

# 历史题号(1-based) -> 预期关键词（用于验证是否爬对）
TARGETS = {
    589: ['频率', '概率'],
    639: ['胶水语言', 'Python'],
    651: ['广播变量', 'PySpark', 'Broadcast'],
    653: ['AgglomerativeClustering', '层次聚类', 'distance'],
    654: ['流形学习', 'LLE', 'PCA', 'LDA'],
}

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

async def main():
    log("=== 针对性补爬启动 ===")
    results = {}

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9223", timeout=15000)
        except Exception as e:
            log(f"CDP连接失败: {e}")
            return

        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        stop_flag = {'stop': False}
        def stop_check():
            return stop_flag['stop']

        for n in sorted(TARGETS):
            seq = n - 1
            page = await ctx.new_page()
            log(f"--- 处理历史题号 {n} (sequence={seq}) ---")
            try:
                status = await _navigate_to_practice(page, PAPER_ID, seq, log, stop_check)
                if status != 'ok':
                    log(f"导航失败: {status}")
                    continue
                if not await _init_recite_mode(page, log):
                    log("背题模式开启失败")
                    continue
                if not await wait_for_question(page, timeout=12):
                    log("未加载到题目")
                    continue
                data = await get_current_question(page, mode='hybrid')
                if data:
                    q = data.get('question', '')
                    ans = data.get('answer', '')
                    typ = data.get('type', '')
                    log(f"题号{n}: type={typ}, ans={ans}")
                    log(f"  题目: {str(q)[:80]}")
                    kw = TARGETS[n]
                    hit = sum(1 for k in kw if k.lower() in str(q).lower())
                    log(f"  关键词命中: {hit}/{len(kw)} -> {'OK' if hit >= 1 else '可能不对'}")
                    results[str(n)] = {
                        'type': typ,
                        'question': q,
                        'options': data.get('options', []),
                        'answer': ans,
                        'analysis': data.get('analysis', ''),
                        'keyword_hit': hit,
                    }
                else:
                    log(f"题号{n}: 读取题目失败")
            except Exception as e:
                log(f"题号{n} 出错: {e}")
            finally:
                try:
                    await page.close()
                except Exception:
                    pass
            await asyncio.sleep(2)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"结果已保存: {OUTPUT_FILE}, 成功 {len(results)}/{len(TARGETS)}")
    log("=== 脚本结束 ===")

asyncio.run(main())
