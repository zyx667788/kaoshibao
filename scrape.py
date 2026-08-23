"""考试宝题库爬取 - 命令行版（Chrome CDP连接）"""

import asyncio
import sys
import io
from playwright.async_api import async_playwright

from scraper_core import (
    OUTPUT_DIR, collect_questions, ensure_chrome_debug, open_cdp_page,
    save_to_excel, load_progress, save_progress, validate_paper_id
)

from logging_config import init_default_logger, get_logger
init_default_logger(level="INFO")
logger = get_logger("kaoshibao.scrape")

if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def main():
    raw_id = sys.argv[1] if len(sys.argv) > 1 else "13573440"
    paper_id, err = validate_paper_id(raw_id)
    if err:
        logger.error(f"错误: {err}")
        return
    output_file = OUTPUT_DIR / f"考试宝题库_{paper_id}.xlsx"

    questions = load_progress(paper_id)
    if questions:
        has_ans = sum(1 for q in questions if q.get('正确答案'))
        logger.info(f"已有进度: {len(questions)} 题, 有答案 {has_ans} 题，将从断点继续")

    # 确保Chrome调试模式
    ok, msg, restarted = ensure_chrome_debug()
    logger.info(msg)
    if not ok:
        return

    async with async_playwright() as p:
        browser, page = await open_cdp_page(p)
        if not browser:
            logger.error("无法连接Chrome，请确保Chrome已安装")
            return

        try:
            logger.info("已连接Chrome，打开新标签页")
            start_sequence = len(questions)

            result, status = await collect_questions(
                page, paper_id,
                log_fn=lambda m: logger.info(m),
                start_sequence=start_sequence
            )

            if status == 'auth_error':
                logger.error("登录超时或已取消，请在Chrome中登录考试宝后重试")
                return

            if result:
                existing_keys = {q.get('题目', '')[:80] for q in questions}
                added = 0
                for q in result:
                    key = q.get('题目', '')[:80]
                    if key and key not in existing_keys:
                        q['序号'] = len(questions) + 1
                        questions.append(q)
                        existing_keys.add(key)
                        added += 1
                logger.info(f"新增 {added} 题，总计 {len(questions)} 题")
            else:
                logger.info("未收集到新题目，保留已有数据")

            if questions:
                save_progress(paper_id, questions)
                save_to_excel(questions, output_file)
                has_ans = sum(1 for q in questions if q.get('正确答案'))
                logger.info(f"\n爬取完成! 总 {len(questions)} 道, 有答案 {has_ans} 道")
                logger.info(f"文件: {output_file}")
            else:
                logger.warning("未收集到任何题目")

        except Exception as e:
            logger.exception(f"运行出错: {e}")
        finally:
            try:
                await page.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
