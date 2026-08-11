from __future__ import annotations

from datetime import datetime
from io import BytesIO

from django.db.models import Avg, Count, Max, Min

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PDF yaratish uchun reportlab o‘rnatilishi kerak: pip install reportlab") from exc

from .metrics import load_fusion_metrics
from .smart_services import build_smart_dashboard


REPLACEMENTS = str.maketrans({
    "‘": "'", "’": "'", "–": "-", "—": "-", "ₖ": "k", "ᵢ": "i",
    "ρ": "rho", "ε": "eps", "Σ": "SUM", "→": "->", "≈": "~",
})


def safe_text(value) -> str:
    return str(value if value is not None else "").translate(REPLACEMENTS)


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=17, leading=21, textColor=colors.HexColor("#163b70"), alignment=TA_CENTER,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=colors.HexColor("#163b70"), spaceBefore=8, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BodySmall", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=8.5, leading=11,
    ))
    return styles


def _table(data, widths=None, header=True, font_size=7.5):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163b70")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    table.setStyle(TableStyle(commands))
    return table


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(18 * mm, 10 * mm, "GeoAI SMART-ONLINE scientific analytical platform")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_model_results_pdf(history_record: dict | None = None) -> bytes:
    metrics = load_fusion_metrics()
    styles = _styles()
    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=16 * mm, bottomMargin=17 * mm, title="GeoAI model results",
    )
    story = [
        Paragraph("GeoAI MODEL RESULTS REPORT", styles["ReportTitle"]),
        Paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}", styles["BodySmall"]),
        Spacer(1, 5 * mm),
    ]
    if not metrics.get("available"):
        story.append(Paragraph("The GeoAI Fusion model has not yet been trained.", styles["BodySmall"]))
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return output.getvalue()

    story.extend([
        Paragraph("1. Model metadata", styles["Section"]),
        _table([
            ["Indicator", "Value"],
            ["Algorithm version", safe_text(metrics.get("algorithm_version", "-"))],
            ["Training date", safe_text(metrics.get("trained_at", "-"))],
            ["Dataset / train / test", f"{metrics.get('dataset_size', 0)} / {metrics.get('train_size', 0)} / {metrics.get('test_size', 0)}"],
            ["Classes", ", ".join(map(safe_text, metrics.get("classes", [])))],
            ["Training duration, sec", f"{float(metrics.get('training_duration_seconds', 0) or 0):.3f}"],
        ], widths=[65 * mm, 105 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("2. General evaluation metrics", styles["Section"]),
        _table([
            ["Accuracy", "Precision", "Recall", "F1-score", "Macro ROC-AUC"],
            [
                f"{metrics.get('accuracy', 0):.4f}",
                f"{metrics.get('precision_weighted', 0):.4f}",
                f"{metrics.get('recall_weighted', 0):.4f}",
                f"{metrics.get('f1_weighted', 0):.4f}",
                f"{metrics.get('roc_auc_macro_ovr', 0):.4f}",
            ],
        ], widths=[34 * mm] * 5),
        Spacer(1, 4 * mm),
        Paragraph("3. Classification report", styles["Section"]),
    ])
    class_rows = [["Class", "Precision", "Recall", "F1", "Support"]]
    for row in metrics.get("classification_rows", []):
        class_rows.append([
            safe_text(row.get("label")), f"{row.get('precision', 0):.4f}",
            f"{row.get('recall', 0):.4f}", f"{row.get('f1', 0):.4f}",
            safe_text(row.get("support", 0)),
        ])
    story.append(_table(class_rows, widths=[58 * mm, 28 * mm, 28 * mm, 28 * mm, 28 * mm]))

    story.extend([Spacer(1, 4 * mm), Paragraph("4. Confusion matrix", styles["Section"])])
    classes = [safe_text(x) for x in metrics.get("classes", [])]
    matrix_data = [["Actual / Predicted"] + classes]
    for row in metrics.get("confusion_rows", []):
        matrix_data.append([safe_text(row.get("label"))] + list(row.get("values", [])))
    story.append(_table(matrix_data, font_size=7.2))

    story.extend([Spacer(1, 4 * mm), Paragraph("5. Layer importance and TOP features", styles["Section"])])
    groups = metrics.get("group_importance", {})
    story.append(_table([
        ["Semantic layer", "Spatial layer", "Temporal layer"],
        [f"{groups.get('semantic', 0):.4f}", f"{groups.get('spatial', 0):.4f}", f"{groups.get('temporal', 0):.4f}"],
    ], widths=[56 * mm] * 3))
    feature_rows = [["No.", "Feature", "Importance"]]
    for idx, feature in enumerate(metrics.get("top_features", [])[:20], 1):
        feature_rows.append([idx, safe_text(feature.get("feature")), f"{feature.get('importance', 0):.6f}"])
    story.append(Spacer(1, 3 * mm))
    story.append(_table(feature_rows, widths=[15 * mm, 120 * mm, 35 * mm]))

    if history_record:
        story.extend([PageBreak(), Paragraph("6. Previous and new model comparison", styles["Section"])])
        comparison = [["Metric", "Previous", "New", "Difference"]]
        names = {
            "accuracy": "Accuracy", "precision_weighted": "Precision",
            "recall_weighted": "Recall", "f1_weighted": "F1-score",
            "roc_auc_macro_ovr": "Macro ROC-AUC",
        }
        for key, label in names.items():
            item = history_record.get("changes", {}).get(key, {})
            comparison.append([
                label, f"{item.get('old', 0):.4f}", f"{item.get('new', 0):.4f}",
                f"{item.get('delta', 0):+.4f}",
            ])
        story.append(_table(comparison, widths=[55 * mm, 38 * mm, 38 * mm, 38 * mm]))

    story.extend([
        Spacer(1, 5 * mm),
        Paragraph(
            "Scientific note: metrics obtained from a small labelled sample must be confirmed "
            "using a larger independent test set, stratified cross-validation and spatial/temporal holdout.",
            styles["BodySmall"],
        ),
    ])
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def build_system_results_pdf(qs, priority_stats: dict, risk_stats: dict) -> bytes:
    styles = _styles()
    smart_stats = build_smart_dashboard(qs)
    output = BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=landscape(A4), rightMargin=13 * mm, leftMargin=13 * mm,
        topMargin=13 * mm, bottomMargin=15 * mm, title="GeoAI system results",
    )
    total = qs.count()
    agg = qs.aggregate(
        avg_priority=Avg("priority_index"), max_priority=Max("priority_index"),
        min_priority=Min("priority_index"), avg_confidence=Avg("classifier_confidence"),
    )
    levels = dict(qs.values("priority_level").annotate(c=Count("id")).values_list("priority_level", "c"))
    story = [
        Paragraph("GeoAI SMART-ONLINE SYSTEM RESULTS REPORT", styles["ReportTitle"]),
        Paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}", styles["BodySmall"]),
        Spacer(1, 4 * mm),
        Paragraph("1. General indicators", styles["Section"]),
        _table([
            ["Complaints", "Avg Pi", "Max Pi", "Min Pi", "Avg confidence", "High / Medium / Low"],
            [
                total, f"{(agg['avg_priority'] or 0):.4f}", f"{(agg['max_priority'] or 0):.4f}",
                f"{(agg['min_priority'] or 0):.4f}", f"{(agg['avg_confidence'] or 0):.4f}",
                f"{levels.get('high', 0)} / {levels.get('medium', 0)} / {levels.get('low', 0)}",
            ],
        ], widths=[36 * mm, 36 * mm, 36 * mm, 36 * mm, 42 * mm, 55 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("2. GeoRisk: DBSCAN + priority-weighted KDE", styles["Section"]),
        _table([
            ["Clusters", "Noise points", "High risk", "Medium risk", "Low risk", "Max Hk", "Avg Hk"],
            [
                risk_stats.get("cluster_count", 0), risk_stats.get("noise_count", 0),
                risk_stats.get("high_count", 0), risk_stats.get("medium_count", 0), risk_stats.get("low_count", 0),
                f"{risk_stats.get('max_risk', 0):.4f}", f"{risk_stats.get('avg_risk', 0):.4f}",
            ],
        ], widths=[36 * mm] * 7),
        Spacer(1, 3 * mm),
    ]
    cluster_rows = [["Cluster", "Points", "Avg WKDE", "Avg Pi", "Hk", "Risk"]]
    for cluster in risk_stats.get("clusters", []):
        cluster_rows.append([
            f"K{cluster['label']}", cluster["count"], f"{cluster['avg_kde']:.4f}",
            f"{cluster['avg_priority']:.4f}", f"{cluster['risk_index']:.4f}", safe_text(cluster["risk_level"]),
        ])
    story.append(_table(cluster_rows, widths=[32 * mm, 32 * mm, 42 * mm, 42 * mm, 42 * mm, 40 * mm]))

    story.extend([Spacer(1, 4 * mm), Paragraph("3. SMART-ONLINE monitoring", styles["Section"])])
    story.append(_table([
        ["Last 24h", "Urgent", "Unresolved", "Assigned", "Assignment rate", "High-risk zones"],
        [
            smart_stats.get("last_24h", 0), smart_stats.get("urgent", 0), smart_stats.get("unresolved", 0),
            smart_stats.get("assigned", 0), f"{smart_stats.get('assignment_rate', 0):.1f}%",
            smart_stats.get("high_risk_clusters", 0),
        ],
    ], widths=[42 * mm] * 6))

    story.extend([Spacer(1, 4 * mm), Paragraph("4. TOP automatic management recommendations", styles["Section"])])
    recommendation_rows = [["Rank", "Cluster", "Hk", "Risk", "Complaints", "Category", "Responsible organization", "Recommendation / deadline", "Resource"]]
    for item in smart_stats.get("recommendations", [])[:15]:
        recommendation_rows.append([
            item.get("rank"), safe_text(item.get("cluster")), f"{item.get('risk_index', 0):.3f}",
            safe_text(item.get("risk_level")), item.get("complaint_count"), safe_text(item.get("dominant_category")),
            safe_text(item.get("responsible_organization")),
            Paragraph(safe_text(f"{item.get('action', '')}; {item.get('response_hours', 0)} hours"), styles["BodySmall"]),
            f"{float(item.get('resource_share', 0)) * 100:.1f}%",
        ])
    story.append(_table(recommendation_rows, widths=[14 * mm, 20 * mm, 20 * mm, 22 * mm, 24 * mm, 28 * mm, 52 * mm, 77 * mm, 22 * mm], font_size=6.6))

    story.extend([PageBreak(), Paragraph("5. TOP priority complaints", styles["Section"])])
    top_rows = [["ID", "Complaint", "Category", "Conf", "rho", "f", "q", "W(C)", "n", "Pi", "Level"]]
    for item in qs.select_related("report").order_by("-priority_index")[:25]:
        top_rows.append([
            safe_text(item.report_id), Paragraph(safe_text(item.report.description[:90]), styles["BodySmall"]),
            safe_text(item.predicted_category), f"{item.classifier_confidence:.3f}", f"{item.spatial_density:.3f}",
            f"{item.recurrence_frequency:.3f}", f"{item.temporal_relevance:.3f}", f"{item.severity_weight:.3f}",
            f"{item.neighbor_influence:.3f}", f"{item.priority_index:.3f}", safe_text(item.priority_level),
        ])
    story.append(_table(top_rows, widths=[23 * mm, 82 * mm, 27 * mm, 19 * mm, 19 * mm, 18 * mm, 18 * mm, 20 * mm, 18 * mm, 19 * mm, 24 * mm], font_size=6.2))
    story.extend([
        Spacer(1, 5 * mm),
        Paragraph(
            "Conclusion: the platform dynamically links complaint classification, priority scoring, spatial hotspot detection, "
            "integral risk assessment and decision-support recommendations.", styles["BodySmall"],
        ),
    ])
    doc.build(story)
    return output.getvalue()
