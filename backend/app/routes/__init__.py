from app.routes.auth import auth_bp
from app.routes.export import export_bp
from app.routes.report import report_bp
from app.routes.scan import scan_bp


ALL_BLUEPRINTS = [auth_bp, scan_bp, report_bp, export_bp]
