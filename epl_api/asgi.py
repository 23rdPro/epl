"""
ASGI config for epl_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from epl_api.urls import router

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "epl_api.settings")

application = get_asgi_application()

app = FastAPI(
    title="EPL API",
    description="""An open source Premier League API client, designed to 
    retrieve player statistics, fixtures, tables, and results from the Premier League. 
    Built with Django, BeautifulSoup, FastAPI, and Pydantic, the API scrapes data 
    directly from the Premier League website and parses it into JSON.""",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can limit to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
