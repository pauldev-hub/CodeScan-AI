import uuid
from datetime import datetime, timedelta, timezone

from app import db
from app.models.report import Report
from app.models.scan import Scan


class ReportService:
    @staticmethod
    def _utc_now_naive():
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def share_scan(scan, user_id, expiration_days=30):
        report = Report.query.filter_by(scan_id=scan.id).first()
        expires_at = ReportService._utc_now_naive() + timedelta(days=expiration_days)

        if report:
            report.is_public = True
            report.expires_at = expires_at
            if not report.share_uuid:
                report.share_uuid = str(uuid.uuid4())
        else:
            report = Report(
                scan_id=scan.id,
                share_uuid=str(uuid.uuid4()),
                is_public=True,
                expires_at=expires_at,
                created_by_user_id=user_id,
            )
            db.session.add(report)

        db.session.commit()
        return report

    @staticmethod
    def revoke_share(scan):
        report = Report.query.filter_by(scan_id=scan.id).first()
        if not report:
            return None
        report.is_public = False
        db.session.commit()
        return report

    @staticmethod
    def get_public_report(share_uuid):
        report = Report.query.filter_by(share_uuid=share_uuid).first()
        if not report:
            return None, "not_found"
        if not report.is_public:
            return None, "revoked"
        if report.expires_at and report.expires_at < ReportService._utc_now_naive():
            return None, "expired"

        report.view_count += 1
        report.last_viewed_at = ReportService._utc_now_naive()
        db.session.commit()

        scan = db.session.get(Scan, report.scan_id)
        return scan, None
