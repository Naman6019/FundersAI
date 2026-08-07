from app.services import report_service

from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
from app.workflows.report_graph import report_workflow

router = APIRouter()

#Define the exoected input
class ReportRequest(BaseModel):
    scheme_code: int

@router.post("/api/v1/reports/generate")
async def generate_report(request:ReportRequest):
    try:
        initial_state = {"scheme_code": request.scheme_code}
        final_state = await report_workflow.ainvoke(initial_state)

        return {
            "status": "success",
            "message": f"Report generated for fund: {request.scheme_code}",
            "report_markdown": final_state["final_report"],
            "metrics_used": final_state["metrics"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))