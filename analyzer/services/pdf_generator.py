"""
PDF Report Generator for RepoSleuth using ReportLab.
Produces a clean, academic-grade project analysis report.
"""

import io
from datetime import datetime
from typing import Any, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Custom canvas that adds page numbers and running footer to every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Top Header
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, letter[1] - 30, letter[0] - 36, letter[1] - 30)
        self.drawString(36, letter[1] - 25, "RepoSleuth Codebase Analysis & Architecture Report")

        # Running Bottom Footer
        self.line(36, 36, letter[0] - 36, 36)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 25, page_text)
        self.drawString(36, 25, "Confidential & Academic Evaluation — Static Analysis (AST)")
        self.restoreState()


def generate_project_pdf_report(project, analysis) -> bytes:
    """
    Builds a complete PDF report for a given project and its analysis.
    Returns raw PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1e1b4b')
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b')
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#312e81'),
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1e293b')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1e293b')
    )

    code_cell_style = ParagraphStyle(
        'TableCodeCell',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0f172a')
    )

    story = []

    # Title & Metadata Banner
    story.append(Paragraph(f"RepoSleuth Analysis Report", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>Project:</b> {project.name} &nbsp;|&nbsp; "
        f"<b>Analyzed:</b> {project.uploaded_at.strftime('%B %d, %Y at %H:%M UTC')} &nbsp;|&nbsp; "
        f"<b>Code Health Score:</b> {analysis.health_score}/100",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#4f46e5'), spaceAfter=14))

    # 1. Executive Summary Table
    story.append(Paragraph("1. Codebase Summary & Metrics", section_heading))
    metrics_data = [
        [
            Paragraph("<b>Total Files:</b>", body_style), Paragraph(str(project.total_files), body_style),
            Paragraph("<b>Total Directories:</b>", body_style), Paragraph(str(project.total_folders), body_style),
        ],
        [
            Paragraph("<b>Total Lines of Code:</b>", body_style), Paragraph(f"{project.total_lines_of_code:,}", body_style),
            Paragraph("<b>Total Size:</b>", body_style), Paragraph(project.formatted_size, body_style),
        ],
        [
            Paragraph("<b>Detected Entry Points:</b>", body_style), Paragraph(str(len(analysis.entry_points)), body_style),
            Paragraph("<b>Total Issues Detected:</b>", body_style), Paragraph(str(analysis.issue_counts.get('total', 0)), body_style),
        ],
        [
            Paragraph("<b>Confirmed Dependencies:</b>", body_style), Paragraph(str(analysis.internal_dependencies.get('confirmed_count', 0)), body_style),
            Paragraph("<b>Estimated Dependencies:</b>", body_style), Paragraph(str(analysis.internal_dependencies.get('estimated_count', 0)), body_style),
        ]
    ]

    metrics_table = Table(metrics_data, colWidths=[1.8 * inch, 1.4 * inch, 1.8 * inch, 1.4 * inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 14))

    # 2. Language Breakdown Table
    story.append(Paragraph("2. Programming Languages Breakdown", section_heading))
    lang_headers = [
        Paragraph("Language", table_header_style),
        Paragraph("Files Count", table_header_style),
        Paragraph("Lines of Code", table_header_style),
        Paragraph("Size", table_header_style)
    ]
    lang_rows = [lang_headers]

    languages = project.languages_breakdown or {}
    for lang_name, stats in sorted(languages.items(), key=lambda x: x[1].get('lines', 0), reverse=True):
        bytes_val = stats.get('bytes', 0)
        formatted_size = f"{bytes_val / 1024:.1f} KB" if bytes_val > 1024 else f"{bytes_val} B"
        lang_rows.append([
            Paragraph(f"<b>{lang_name}</b>", cell_style),
            Paragraph(str(stats.get('files', 0)), cell_style),
            Paragraph(f"{stats.get('lines', 0):,}", cell_style),
            Paragraph(formatted_size, cell_style)
        ])

    if len(lang_rows) == 1:
        lang_rows.append([Paragraph("No files cataloged", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])

    lang_table = Table(lang_rows, colWidths=[2.2 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])
    lang_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(lang_table)
    story.append(Spacer(1, 14))

    # 3. Detected Entry Points
    story.append(Paragraph("3. Detected Application Entry Points", section_heading))
    entry_headers = [
        Paragraph("File Path", table_header_style),
        Paragraph("Framework / Type", table_header_style),
        Paragraph("Confidence", table_header_style),
        Paragraph("Detection Rationale", table_header_style)
    ]
    entry_rows = [entry_headers]

    for ep in analysis.entry_points:
        conf = ep.get('confidence', 'Medium')
        conf_color = '#15803d' if conf == 'High' else '#b45309'
        entry_rows.append([
            Paragraph(ep.get('file', ''), code_cell_style),
            Paragraph(ep.get('framework', 'Generic'), cell_style),
            Paragraph(f"<font color='{conf_color}'><b>{conf}</b></font>", cell_style),
            Paragraph(ep.get('summary_reason', ''), cell_style)
        ])

    if len(entry_rows) == 1:
        entry_rows.append([
            Paragraph("No standard entry points identified", cell_style),
            Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("Files inspected showed no main or runner hooks", cell_style)
        ])

    entry_table = Table(entry_rows, colWidths=[1.8 * inch, 1.3 * inch, 0.9 * inch, 2.4 * inch])
    entry_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e1b4b')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(entry_table)
    story.append(Spacer(1, 14))

    # 4. Code Issues and Warnings
    story.append(Paragraph("4. Code Issues & Quality Findings", section_heading))
    issue_headers = [
        Paragraph("Severity", table_header_style),
        Paragraph("Category", table_header_style),
        Paragraph("File & Line", table_header_style),
        Paragraph("Details & Snippet", table_header_style)
    ]
    issue_rows = [issue_headers]

    for issue in analysis.issues[:35]:  # Cap to top 35 issues in printable PDF
        sev = issue.get('severity', 'Medium')
        sev_color = '#b91c1c' if sev == 'High' else ('#b45309' if sev == 'Medium' else '#3b82f6')
        file_line = f"{issue.get('file', '')}:{issue.get('line', 1)}"
        snippet = issue.get('snippet', '')
        desc = issue.get('description', '')
        detail_html = f"<b>{desc}</b>"
        if snippet:
            detail_html += f"<br/><font color='#64748b' face='Courier'>{snippet[:80]}</font>"

        issue_rows.append([
            Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", cell_style),
            Paragraph(issue.get('category', '').replace('_', ' ').title(), cell_style),
            Paragraph(file_line, code_cell_style),
            Paragraph(detail_html, cell_style)
        ])

    if len(issue_rows) == 1:
        issue_rows.append([
            Paragraph("Clean", cell_style), Paragraph("None", cell_style),
            Paragraph("-", cell_style), Paragraph("No code issues or syntax errors detected.", cell_style)
        ])

    issue_table = Table(issue_rows, colWidths=[0.8 * inch, 1.2 * inch, 1.8 * inch, 2.6 * inch])
    issue_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(issue_table)

    if len(analysis.issues) > 35:
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<i>* Note: Showing first 35 of {len(analysis.issues)} total issues. View full interactive report online for complete issue details.</i>",
            subtitle_style
        ))

    story.append(Spacer(1, 14))

    # 5. External Third-Party Dependencies
    story.append(Paragraph("5. External Third-Party Dependencies", section_heading))
    ext_deps = analysis.external_dependencies or []
    if ext_deps:
        ext_headers = [
            Paragraph("Package Name", table_header_style),
            Paragraph("Import Occurrences", table_header_style),
            Paragraph("Referencing Files Sample", table_header_style)
        ]
        ext_rows = [ext_headers]
        for dep in ext_deps[:20]:
            ext_rows.append([
                Paragraph(f"<b>{dep.get('package', '')}</b>", cell_style),
                Paragraph(str(dep.get('count', 0)), cell_style),
                Paragraph(", ".join(dep.get('files', [])[:3]), code_cell_style)
            ])
        ext_table = Table(ext_rows, colWidths=[2.0 * inch, 1.5 * inch, 2.9 * inch])
        ext_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(ext_table)
    else:
        story.append(Paragraph("No external third-party packages detected. Codebase uses only standard libraries.", cell_style))

    # Build PDF with custom canvas for page numbering
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
