import asyncio
import os
from playwright.async_api import async_playwright

BASE = 'http://127.0.0.1:5678/'
OUT = r'D:\gdx\kaoshibao\docs\screenshots'
os.makedirs(OUT, exist_ok=True)


async def main():
    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            print('browser: chromium')
        except Exception as e:
            print('chromium failed:', repr(e)[:200])
            browser = await p.chromium.launch(headless=True, channel='msedge', args=['--no-sandbox'])
            print('browser: msedge')
        page = await browser.new_page(viewport={'width': 1600, 'height': 1100}, device_scale_factor=1.5)
        await page.goto(BASE, wait_until='networkidle', timeout=45000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path=os.path.join(OUT, 'home_top.png'))
        print('saved home_top.png')
        await page.screenshot(path=os.path.join(OUT, 'home_full.png'), full_page=True)
        print('saved home_full.png')
        try:
            await page.locator('.files-section').scroll_into_view_if_needed()
            await page.wait_for_timeout(800)
            await page.screenshot(path=os.path.join(OUT, 'files_section.png'))
            print('saved files_section.png')
        except Exception as e:
            print('files-section shot skipped:', repr(e)[:200])
        await browser.close()
    print('ALL DONE')


asyncio.run(main())
