from app.routes.chat import chat_bp
from app.routes.auth import auth_bp
from app.routes.export import export_bp
from app.routes.report import report_bp
from app.routes.scan import scan_bp
from app.routes.settings import settings_bp


ALL_BLUEPRINTS = [auth_bp, scan_bp, report_bp, export_bp, settings_bp, chat_bp]
