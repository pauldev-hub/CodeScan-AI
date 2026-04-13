from datetime import datetime

from app import db


class ChatConversation(db.Model):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        db.Index("idx_chat_conversations_user_updated", "user_id", "updated_at"),
        db.Index("idx_chat_conversations_scan_id", "scan_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    user = db.relationship("User", back_populates="chat_conversations")
    scan = db.relationship("Scan", back_populates="chat_conversations")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        db.CheckConstraint("feedback IN ('like', 'dislike')", name="ck_chat_messages_feedback"),
        db.Index("idx_chat_messages_conversation_created", "conversation_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    feedback = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    conversation = db.relationship("ChatConversation", back_populates="messages")
