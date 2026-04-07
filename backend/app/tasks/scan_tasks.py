from celery import shared_task

from app.services.scan_service import ScanService


@shared_task(bind=True, max_retries=2)
def process_scan_task(self, scan_id):
    del self
    ScanService.process_scan(scan_id)
    return {"scan_id": scan_id, "status": "processed"}
