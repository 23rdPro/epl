from abc import ABC
import asyncio
from django.core.management.base import BaseCommand
import dlt
from playwright.async_api import async_playwright
from epl_api.v1.dependencies import get_page
from epl_api.views import get_results


class Command(BaseCommand, ABC):
    help = "Run get_results API function and process data"

    async def run_get_results(self):
        async with async_playwright() as p:
            async for page in get_page():
                results = await get_results(page=page)

                pipeline = dlt.pipeline(
                    pipeline_name="epl_pipeline",
                    destination="duckdb",
                    dataset_name="epl_results",
                )
                pipeline.run(results, table_name="results")

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run_get_results())
        self.stdout.write(f"{self.style.SUCCESS('Data processed successfully!')}")
