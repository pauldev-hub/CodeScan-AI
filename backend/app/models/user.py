from datetime import datetime

from app import bcrypt, db


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (db.Index("idx_users_created_at", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(120), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    about_me = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    plan = db.Column(db.String(20), nullable=False, default="free")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    settings = db.Column(db.Text, nullable=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    scans = db.relationship(
        "Scan",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    comments = db.relationship("Comment", back_populates="user", lazy="dynamic")
    chat_conversations = db.relationship("ChatConversation", back_populates="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "name": self.name,
            "age": self.age,
            "about_me": self.about_me,
            "plan": self.plan,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
