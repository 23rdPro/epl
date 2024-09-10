from playwright.async_api import async_playwright


# Dependency to initialize Playwright's page object
async def get_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        try:
            yield page
        finally:
            await browser.close()
