from datetime import datetime
import uuid

from app import db


class Scan(db.Model):
    __tablename__ = "scans"
    __table_args__ = (
        db.CheckConstraint("input_type IN ('url', 'upload', 'paste')", name="ck_scans_input_type"),
        db.CheckConstraint(
            "status IN ('pending', 'running', 'complete', 'error')",
            name="ck_scans_status",
        ),
        db.Index("idx_scans_created_at", "created_at"),
        db.Index("idx_scans_user_created", "user_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    api_scan_id = db.Column(db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    input_type = db.Column(db.String(20), nullable=False)
    input_value = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    health_score = db.Column(db.Integer, nullable=True)
    total_findings = db.Column(db.Integer, nullable=True)
    celery_task_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    analysis_time_seconds = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    file_count = db.Column(db.Integer, nullable=True)
    code_size_bytes = db.Column(db.Integer, nullable=True)
    language_breakdown = db.Column(db.Text, nullable=True)
    pros_json = db.Column(db.Text, nullable=True)
    cons_json = db.Column(db.Text, nullable=True)
    refactor_suggestions_json = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="scans")
    findings = db.relationship(
        "Finding",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    report = db.relationship("Report", back_populates="scan", uselist=False)


class Finding(db.Model):
    __tablename__ = "findings"
    __table_args__ = (
        db.CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_findings_severity",
        ),
        db.CheckConstraint(
            "category IN ('security', 'bug', 'performance', 'logic')",
            name="ck_findings_category",
        ),
        db.CheckConstraint("exploit_risk >= 0 AND exploit_risk <= 100", name="ck_findings_exploit_risk"),
        db.Index("idx_findings_category", "category"),
        db.Index("idx_findings_scan_severity", "scan_id", "severity"),
    )

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    plain_english = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    line_number = db.Column(db.Integer, nullable=True)
    code_snippet = db.Column(db.Text, nullable=True)
    fix_suggestion = db.Column(db.Text, nullable=False)
    exploit_risk = db.Column(db.Integer, nullable=True)
    cwe_id = db.Column(db.String(20), nullable=True)
    owasp_category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    scan = db.relationship("Scan", back_populates="findings")
    comments = db.relationship(
        "Comment",
        back_populates="finding",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
