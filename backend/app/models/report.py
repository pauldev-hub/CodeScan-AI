from datetime import datetime

from app import db


class Report(db.Model):
    __tablename__ = "reports"
    __table_args__ = (
        db.Index("idx_reports_scan_id", "scan_id"),
        db.Index("idx_reports_is_public", "is_public"),
    )

    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, unique=True)
    share_uuid = db.Column(db.String(36), nullable=False, unique=True, index=True)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    last_viewed_at = db.Column(db.DateTime, nullable=True)

    scan = db.relationship("Scan", back_populates="report")


class Comment(db.Model):
    __tablename__ = "comments"
    __table_args__ = (
        db.Index("idx_comments_user_id", "user_id"),
        db.Index("idx_comments_finding_user", "finding_id", "user_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.Integer, db.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    finding = db.relationship("Finding", back_populates="comments")
    user = db.relationship("User", back_populates="comments")
