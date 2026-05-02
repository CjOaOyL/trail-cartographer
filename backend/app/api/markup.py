from fastapi import APIRouter

from app.ai.markup import interpret_markup
from app.models.project import MarkupRequest, MarkupResponse

router = APIRouter()


@router.post("/interpret", response_model=MarkupResponse)
async def interpret(req: MarkupRequest) -> MarkupResponse:
    return await interpret_markup(req)
