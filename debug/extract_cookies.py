import asyncio
import json
from playwright.async_api import async_playwright

OUT = r'D:\gdx\kaoshibao\debug\ksb_cookies.json'


async def main():
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp('http://127.0.0.1:9223')
        ctx = b.contexts[0]
        page = await ctx.new_page()
        await page.goto('https://www.kaoshibao.com/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(4000)
        text = await page.inner_text('body')
        print('TITLE:', await page.title())
        print('URL:', page.url)
        print('has 退出:', '退出' in text, '| has 登录:', '登录' in text, '| has 注册:', '注册' in text)
        cookies = await ctx.cookies(['https://www.kaoshibao.com'])
        print('cookie_count:', len(cookies))
        names = [c['name'] for c in cookies]
        print('cookie_names:', names)
        with open(OUT, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=1)
        print('saved to', OUT)
        await b.close()


asyncio.run(main())
