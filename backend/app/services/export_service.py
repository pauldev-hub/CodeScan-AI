import csv
import io
import json
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.services.scan_service import ScanService


class ExportService:
    @staticmethod
    def build_json(scan):
        return json.dumps(ScanService.build_results_payload(scan), indent=2)

    @staticmethod
    def build_csv(scan):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["title", "severity", "category", "file_path", "line_number", "fix_suggestion"])
        for finding in scan.findings.all():
            writer.writerow([
                finding.title,
                finding.severity,
                finding.category,
                finding.file_path,
                finding.line_number,
                finding.fix_suggestion,
            ])
        return output.getvalue()

    @staticmethod
    def build_md(scan):
        payload = ScanService.build_results_payload(scan)
        lines = [
            f"# Scan Report: {payload['scan_id']}",
            "",
            f"- Health Score: {payload['health_score']}",
            f"- Total Findings: {payload['summary']['total_findings']}",
            "",
            "## Findings",
            "",
        ]
        for finding in payload["findings"]:
            lines.extend(
                [
                    f"### {finding['title']}",
                    f"- Severity: {finding['severity']}",
                    f"- Category: {finding['category']}",
                    f"- File: {finding['file_path']}:{finding['line_number'] or ''}",
                    f"- Fix: {finding['fix_suggestion']}",
                    "",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def build_pdf(scan):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        y = 750

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(72, y, f"CodeScan AI Report: {scan.api_scan_id}")
        y -= 24

        pdf.setFont("Helvetica", 11)
        pdf.drawString(72, y, f"Generated: {datetime.utcnow().isoformat()}Z")
        y -= 20
        pdf.drawString(72, y, f"Health Score: {scan.health_score}")
        y -= 20

        for finding in scan.findings.limit(20).all():
            if y < 90:
                pdf.showPage()
                y = 750
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(72, y, f"- {finding.title} ({finding.severity})")
            y -= 15
            pdf.setFont("Helvetica", 9)
            pdf.drawString(84, y, f"{finding.file_path}:{finding.line_number or ''}")
            y -= 15

        pdf.save()
        buffer.seek(0)
        return buffer
