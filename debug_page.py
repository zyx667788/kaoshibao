"""诊断脚本：连接Chrome，打开题库页面，输出页面结构"""

import asyncio
import sys
import io
from playwright.async_api import async_playwright
from scraper_core import ensure_chrome_debug, open_cdp_page

if not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def main():
    paper_id = sys.argv[1] if len(sys.argv) > 1 else "17177508"

    ok, msg = ensure_chrome_debug()
    print(msg)
    if not ok:
        return

    async with async_playwright() as p:
        browser, page = await open_cdp_page(p)
        if not browser:
            print("无法连接Chrome")
            return

        try:
            url = f'https://www.kaoshibao.com/ti/{paper_id}/'
            print(f"\n1. 打开 {url}")
            await page.goto(url, wait_until='networkidle')
            await asyncio.sleep(3)

            print(f"   当前URL: {page.url}")
            print(f"   标题: {await page.title()}")

            if 'login' in page.url.lower():
                print("   *** 需要登录! 请在Chrome中扫码 ***")
                print("   等待登录... (每3秒检查一次)")
                for i in range(60):
                    await asyncio.sleep(3)
                    await page.reload(wait_until='networkidle')
                    if 'login' not in page.url.lower():
                        print(f"   登录成功! URL: {page.url}")
                        break
                else:
                    print("   登录超时")
                    return

            # 输出页面所有链接
            print("\n2. 页面链接:")
            links = await page.evaluate('''() => {
                const result = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const text = a.innerText?.trim().substring(0, 60);
                    const href = a.href;
                    const visible = a.offsetParent !== null || a.offsetHeight > 0;
                    if (text) result.push({text, href, visible});
                });
                return result;
            }''')
            for l in links[:30]:
                vis = "可见" if l['visible'] else "隐藏"
                print(f"   [{vis}] [{l['text']}] -> {l['href']}")

            # 输出所有按钮
            print("\n3. 页面按钮:")
            buttons = await page.evaluate('''() => {
                const result = [];
                document.querySelectorAll('button, [role="button"], .btn, [onclick], .el-button').forEach(b => {
                    const text = b.innerText?.trim().substring(0, 60);
                    const visible = b.offsetParent !== null || b.offsetHeight > 0;
                    const cls = b.className?.substring(0, 60);
                    if (text) result.push({text, visible, cls});
                });
                return result;
            }''')
            for b in buttons[:20]:
                vis = "可见" if b['visible'] else "隐藏"
                print(f"   [{vis}] [{b['text']}] class={b.get('cls', '')}")

            # 输出页面主要文本
            print("\n4. 页面文本(前500字):")
            body_text = await page.evaluate('() => document.body?.innerText?.substring(0, 500) || ""')
            for line in body_text.split('\n')[:20]:
                if line.strip():
                    print(f"   {line.strip()}")

            # 查找"顺序练习"相关元素
            print("\n5. 查找'顺序练习':")
            seq_info = await page.evaluate('''() => {
                const result = [];
                document.querySelectorAll('*').forEach(el => {
                    const text = el.innerText?.trim();
                    if (text && text.includes('顺序练习') && text.length < 100) {
                        result.push({
                            tag: el.tagName,
                            text: text.substring(0, 60),
                            href: el.href || el.getAttribute('onclick') || '',
                            visible: el.offsetParent !== null,
                            cls: el.className?.substring(0, 60)
                        });
                    }
                });
                return result;
            }''')
            for s in seq_info:
                print(f"   <{s['tag']}> [{s['text']}] href={s['href']} visible={s['visible']} class={s.get('cls', '')}")

            # 尝试点击"顺序练习"并观察
            print("\n6. 尝试点击'顺序练习':")
            old_url = page.url
            clicked = await page.evaluate('''() => {
                for (const el of document.querySelectorAll('a, button, [onclick]')) {
                    if (el.innerText?.includes('顺序练习') && el.offsetParent !== null) {
                        el.click();
                        return {tag: el.tagName, href: el.href || '', text: el.innerText.trim().substring(0, 50)};
                    }
                }
                return null;
            }''')
            if clicked:
                print(f"   点击了: <{clicked['tag']}> [{clicked['text']}] href={clicked['href']}")
            else:
                print("   未找到可点击的'顺序练习'元素")

            await asyncio.sleep(5)
            print(f"   点击后URL: {page.url}")
            if page.url != old_url:
                print("   URL已变化!")
            else:
                print("   URL未变化")

            # 如果进入了练习页面，输出题目信息
            if page.url != old_url or 'practice' in page.url or 'do' in page.url:
                print("\n7. 练习页面内容:")
                q_info = await page.evaluate('''() => {
                    const q = document.querySelector('.topic-top .question, .question-content, .topic-tit');
                    const opts = document.querySelectorAll('.option-item');
                    return {
                        question: q ? q.innerText.substring(0, 100) : 'NOT FOUND',
                        optionCount: opts.length,
                        bodySnippet: document.body?.innerText?.substring(0, 300)
                    };
                }''')
                print(f"   题目: {q_info['question']}")
                print(f"   选项数: {q_info['optionCount']}")
                print(f"   页面文本: {q_info.get('bodySnippet', '')[:200]}")

        except Exception as e:
            print(f"出错: {e}")
        finally:
            try:
                await page.close()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
