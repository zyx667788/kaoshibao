import asyncio
import os
from playwright.async_api import async_playwright

OUT = r'D:\gdx\kaoshibao\docs\screenshots'
os.makedirs(OUT, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await browser.new_page(viewport={'width': 1600, 'height': 1100}, device_scale_factor=1.5)
        await page.goto('http://100.91.60.84:9007/web/', wait_until='domcontentloaded', timeout=45000)
        await page.wait_for_timeout(6000)
        body = await page.inner_text('body')
        print('has 任务列表:', '任务列表' in body, '| has 收集中:', '收集中' in body, '| has 已生成文件:', '已生成文件' in body)
        await page.screenshot(path=os.path.join(OUT, 'server_home.png'))
        print('saved server_home.png')
        await browser.close()


asyncio.run(main())
