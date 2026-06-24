from fastapi import APIRouter, HTTPException, Query, status

from backend.schemas.reports import ReportDetail, ReportListResponse
from backend.services.report_service import get_report, list_reports


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=ReportListResponse)
def reports() -> ReportListResponse:
    return ReportListResponse(reports=list_reports())


@router.get("/latest", response_model=ReportDetail)
def latest_report() -> ReportDetail:
    report = get_report()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly report is available yet.",
        )
    return report


@router.get("/document", response_model=ReportDetail)
def report_document(filename: str = Query(min_length=1, max_length=255)) -> ReportDetail:
    report = get_report(filename)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report
