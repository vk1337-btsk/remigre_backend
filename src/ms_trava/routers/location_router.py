from fastapi import APIRouter


router = APIRouter(prefix="/location", tags=["Location"])


@router.get("/counties", summary="Список всех стран")
async def get_all_counties():
    pass


@router.get("/cities", summary="Список всех городов")
async def get_all_city():
    pass


@router.get("/country/{country_id}", summary="Получить страну по id")
async def get_country_by_id():
    pass


@router.get("/country/{county_name}", summary="Получить страну по name_eng")
async def get_country_by_name_eng():
    pass


@router.get("/city/{city_id}", summary="Получить город по id")
async def get_city_by_id():
    pass


@router.get("/city/{county_name}_{city_name}", summary="Получить город по названию страны и города")
async def get_city_by_country_id_and_eng():
    pass
