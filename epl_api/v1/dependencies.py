import logging
from playwright.async_api import async_playwright


async def get_page():
    browser = None  
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
            page = await browser.new_page()
            try:
                yield page
            finally:
                if browser:  
                    await browser.close()
        except Exception as e:
            logging.error(f"Failed to launch Playwright: {e}")
            raise
