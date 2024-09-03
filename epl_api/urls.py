"""
URL configuration for epl_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from fastapi import APIRouter, status
from epl_api.views import get_fixtures, get_root, get_p_stats, get_table

router = APIRouter()

router.get("/", status_code=status.HTTP_200_OK)(get_root)
router.get("/stats/{p_name}", status_code=status.HTTP_200_OK, summary="get player stats", tags="pl-stats")(get_p_stats)
router.get("/table", status_code=status.HTTP_200_OK, summary="get epl table", tags="epl-table")(get_table)
router.get("/fixtures", status_code=status.HTTP_200_OK, summary="", tags="epl-fixtures")(get_fixtures)
