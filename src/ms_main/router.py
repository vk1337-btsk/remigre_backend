from fastapi import APIRouter


router = APIRouter(prefix="/info", tags=["Info"])


@router.get(
    "/{slug}",
    summary="Предоставляет информацию для наполнения основных разделов сайта",
)
async def get_info_by_slug():
    pass


