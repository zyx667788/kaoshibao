import asyncio, json, time, sys, os
sys.path.insert(0, r'D:\gdx\kaoshibao')
os.chdir(r'D:\gdx\kaoshibao')

from playwright.async_api import async_playwright
from scraper_core import (
    collect_questions, save_to_excel, load_progress, save_progress,
    close_popups, enable_recite_mode, check_login_required
)

PAPER_ID = '13573440'
LOG_FILE = r'D:\gdx\kaoshibao\debug\scrape_standalone.log'
PROGRESS_FILE = rf'D:\gdx\kaoshibao\data\progress_{PAPER_ID}_hybrid.json'
OUTPUT_FILE = rf'D:\gdx\kaoshibao\output\考试宝题库_{PAPER_ID}_hybrid.xlsx'

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

async def main():
    questions = load_progress(PAPER_ID, suffix='_hybrid')
    start_seq = len(questions)
    log(f"=== 断点续爬: 已有 {len(questions)} 题, 从第 {start_seq+1} 题继续 ===")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9223", timeout=15000)
        except Exception as e:
            log(f"CDP连接失败: {e}")
            return

        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        log("已连接Chrome，打开新标签页")

        stop_flag = {'stop': False}

        def stop_check():
            return stop_flag['stop']

        def on_progress(collected, with_answer):
            if collected % 50 == 0:
                log(f"进度: {collected} 题, 有答案 {with_answer} 题")

        try:
            result, status = await collect_questions(
                page, PAPER_ID,
                log_fn=lambda msg: log(msg),
                stop_check=stop_check,
                progress_fn=on_progress,
                start_sequence=start_seq,
                max_questions=0,
                mode='hybrid',
                existing_questions=questions,
                repeat_limit=60
            )

            if result:
                log(f"爬取完成: {len(result)} 题, status={status}")
                save_progress(PAPER_ID, result, suffix='_hybrid')
                save_to_excel(result, OUTPUT_FILE)
                has_ans = sum(1 for q in result if q.get('正确答案'))
                log(f"已保存: {OUTPUT_FILE}, {len(result)} 题, {has_ans} 道有答案")
            else:
                log(f"未收集到题目, status={status}")
        except Exception as e:
            log(f"爬取出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                await page.close()
            except Exception:
                pass

    log("=== 脚本结束 ===")

asyncio.run(main())
