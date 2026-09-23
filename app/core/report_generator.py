import json
import html
import logging
from typing import Dict, Any
from pathlib import Path

from app.config import EXPORTS_DIR

logger = logging.getLogger(__name__)

class ReportGenerator:
    @staticmethod
    def generate_json_report(analysis_data: Dict[str, Any]) -> str:
        """Export comprehensive JSON audit report."""
        filename = f"contract_audit_{analysis_data.get('doc_id', 'doc')}.json"
        filepath = EXPORTS_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2)
        return str(filepath)

    @staticmethod
    def generate_html_report(analysis_data: Dict[str, Any]) -> str:
        """Generate high-quality printable HTML executive audit report."""
        filename = f"contract_audit_{analysis_data.get('doc_id', 'doc')}.html"
        filepath = EXPORTS_DIR / filename
        
        risk = analysis_data.get("risk_analysis", {})
        entities = analysis_data.get("entities", {})
        score = risk.get("composite_score", 0)
        tier = html.escape(str(risk.get("risk_tier", "LOW")))
        color = html.escape(str(risk.get("risk_color", "#10B981")))
        doc_name = html.escape(str(analysis_data.get("filename", "Contract Document")))

        parties = entities.get("parties", [])
        parties_html = "".join([
            f"<li><strong>{html.escape(p['name'])}</strong> ({html.escape(p.get('role', 'Party'))})</li>"
            for p in parties
        ]) if parties else "<li>Not detected</li>"

        anomalies = risk.get("anomalies", [])
        anomalies_html = ""
        for a in anomalies:
            cat = html.escape(str(a.get('category', 'Risk Flag')))
            sev = html.escape(str(a.get('severity', 'HIGH')))
            rat = html.escape(str(a.get('rationale', '')))
            flag_txt = html.escape(str(a.get('flagged_text', ''))[:300])
            redline = html.escape(str(a.get('recommended_redline', '')))
            anomalies_html += f"""
            <div style="border-left: 4px solid #EF4444; background: #FEF2F2; padding: 12px; margin-bottom: 12px; border-radius: 4px;">
                <div style="font-weight: 700; color: #991B1B;">⚠️ {cat} ({sev})</div>
                <div style="margin: 6px 0; font-size: 13px; color: #374151;"><strong>Rationale:</strong> {rat}</div>
                <div style="margin: 6px 0; font-size: 13px; color: #1F2937; background: #FFFFFF; padding: 8px; border: 1px dashed #FCA5A5; border-radius: 4px;"><strong>Flagged Language:</strong> "{flag_txt}..."</div>
                <div style="font-size: 13px; color: #065F46; background: #ECFDF5; padding: 6px; border-radius: 4px;"><strong>Recommended Standard Redline:</strong> {redline}</div>
            </div>
            """

        recs = risk.get("actionable_recommendations", [])
        recs_html = "".join([
            f"<li><strong>[{html.escape(str(r.get('priority', 'Medium')))} Priority] {html.escape(str(r.get('action', '')))}:</strong> {html.escape(str(r.get('guidance', '')))}</li>"
            for r in recs
        ])

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Contract Intelligence & Risk Audit Report - {doc_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1E293B; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ border-bottom: 2px solid #E2E8F0; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
        .title {{ font-size: 24px; font-weight: 800; color: #0F172A; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 14px; text-transform: uppercase; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .kpi-card {{ background: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 8px; text-align: center; }}
        .kpi-val {{ font-size: 24px; font-weight: 800; color: #0F172A; }}
        .kpi-label {{ font-size: 12px; color: #64748B; text-transform: uppercase; margin-top: 4px; }}
        .section {{ margin-bottom: 30px; }}
        .section-title {{ font-size: 18px; font-weight: 700; color: #1E293B; border-bottom: 1px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 15px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        @media print {{ body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">Contract Intelligence & Legal Risk Audit</div>
            <div style="color: #64748B; font-size: 14px; margin-top: 4px;">Document: <strong>{doc_name}</strong></div>
        </div>
        <div>
            <span class="badge" style="background: {color}; color: #FFFFFF;">{tier} RISK ({score}/100)</span>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-val" style="color: {color};">{score}/100</div>
            <div class="kpi-label">Overall Risk Score</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{len(parties)}</div>
            <div class="kpi-label">Contracting Parties</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{entities.get('governing_law', {}).get('jurisdiction', 'N/A')}</div>
            <div class="kpi-label">Jurisdiction</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{len(anomalies)}</div>
            <div class="kpi-label">Risk Flags Detected</div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Executive Summary</div>
        <p style="background: #F1F5F9; padding: 15px; border-radius: 8px; font-size: 14px;">{risk.get('executive_summary', 'Analysis completed successfully.')}</p>
    </div>

    <div class="section">
        <div class="section-title">Contracting Metadata & Identified Entities</div>
        <ul>
            {parties_html}
            <li><strong>Effective Date:</strong> {entities.get('effective_date', {}).get('value', 'Not explicitly stated')}</li>
            <li><strong>Expiration Date:</strong> {entities.get('expiration_date', {}).get('value', 'Not explicitly stated')}</li>
            <li><strong>Governing Law:</strong> {entities.get('governing_law', {}).get('jurisdiction', 'Not specified')}</li>
        </ul>
    </div>

    <div class="section">
        <div class="section-title">High-Risk Language & Legal Anomalies</div>
        {anomalies_html or '<p style="color: #10B981;">No critical anomalous risk flags detected.</p>'}
    </div>

    <div class="section">
        <div class="section-title">Actionable Legal Negotiation Checklist</div>
        <ul>
            {recs_html or '<li>No critical redlining required. Standard execution terms approved.</li>'}
        </ul>
    </div>

    <div style="margin-top: 40px; border-top: 1px solid #E2E8F0; padding-top: 15px; font-size: 12px; color: #94A3B8; text-align: center;">
        Generated by AI-Powered Contract Intelligence Platform • CUAD Benchmark Compliant
    </div>
</body>
</html>"""
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return str(filepath)

    @classmethod
    def generate_pdf_report(cls, analysis_data: Dict[str, Any]) -> str:
        """Generate PDF report using reportlab."""
        filename = f"contract_audit_{analysis_data.get('doc_id', 'doc')}.pdf"
        filepath = EXPORTS_DIR / filename

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            doc = SimpleDocTemplate(str(filepath), pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor('#0F172A')
            )
            
            h2_style = ParagraphStyle(
                'ReportH2',
                parent=styles['Heading2'],
                fontSize=14,
                leading=18,
                textColor=colors.HexColor('#1E293B'),
                spaceBefore=12,
                spaceAfter=6
            )
            
            body_style = ParagraphStyle(
                'ReportBody',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#334155')
            )

            story = []
            
            # Title
            story.append(Paragraph("Contract Intelligence & Legal Risk Audit", title_style))
            story.append(Paragraph(f"Document: <b>{analysis_data.get('filename', 'Contract')}</b>", body_style))
            story.append(Spacer(1, 12))

            # Risk Summary Table
            risk = analysis_data.get("risk_analysis", {})
            score = risk.get("composite_score", 0)
            tier = risk.get("risk_tier", "LOW")
            
            summary_data = [
                ["Risk Score", "Risk Tier", "Jurisdiction", "Anomalies"],
                [f"{score}/100", tier, analysis_data.get("entities", {}).get("governing_law", {}).get("jurisdiction", "N/A"), str(len(risk.get("anomalies", [])))]
            ]
            t = Table(summary_data, colWidths=[120, 120, 150, 100])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
            ]))
            story.append(t)
            story.append(Spacer(1, 15))

            # Executive Narrative
            story.append(Paragraph("Executive Summary", h2_style))
            story.append(Paragraph(risk.get("executive_summary", "Analysis completed."), body_style))
            story.append(Spacer(1, 12))

            # Recommendations
            story.append(Paragraph("Actionable Recommendations", h2_style))
            for rec in risk.get("actionable_recommendations", []):
                story.append(Paragraph(f"• <b>[{rec.get('priority')} Priority] {rec.get('action')}:</b> {rec.get('guidance')}", body_style))
                story.append(Spacer(1, 4))

            doc.build(story)
            return str(filepath)
        except Exception as e:
            logger.error("Failed to generate PDF via reportlab: %s. Falling back to HTML.", str(e))
            return cls.generate_html_report(analysis_data)

report_generator = ReportGenerator()
