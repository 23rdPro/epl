import logging
from playwright.async_api import async_playwright


# async def get_page():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
#         page = await browser.new_page()
#         try:
#             yield page
#         finally:
#             await browser.close()


async def get_page():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            yield page
    except Exception as e:
        logging.error(f"Failed to launch Playwright: {e}")
        raise
    finally:
        await browser.close()
