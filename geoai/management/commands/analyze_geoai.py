from django.core.management.base import BaseCommand
from reports.models import Report
from geoai.models import ComplaintAnalysis
from geoai.services import ReportPoint, analyze_points


class Command(BaseCommand):
    help = "Murojaatlarni klassifikatsiya qiladi va GeoPriority indeksini hisoblaydi."

    def add_arguments(self, parser):
        parser.add_argument("--radius", type=float, default=0.5, help="Qo‘shnichilik radiusi, km")
        parser.add_argument("--days", type=int, default=30, help="Takrorlanish vaqt oynasi, kun")

    def handle(self, *args, **options):
        reports = list(
            Report.objects.exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .order_by("created_at")
        )
        points = [
            ReportPoint(
                report_id=r.id,
                text=r.description or r.title or "",
                lat=float(r.latitude),
                lon=float(r.longitude),
                created_at=r.created_at,
                stored_category=r.category_ai,
            )
            for r in reports
        ]
        results = analyze_points(points, radius_km=options["radius"], frequency_days=options["days"])
        report_map = {r.id: r for r in reports}
        for row in results:
            report = report_map[row["report_id"]]
            report.category_ai = row["category"]
            report.save(update_fields=["category_ai"])
            ComplaintAnalysis.objects.update_or_create(
                report=report,
                defaults={
                    "predicted_category": row["category"],
                    "classifier_confidence": row["confidence"],
                    "spatial_density": row["density"],
                    "recurrence_frequency": row["frequency"],
                    "temporal_relevance": row["recency"],
                    "severity_weight": row["severity"],
                    "neighbor_influence": row["neighbor"],
                    "priority_index": row["priority"],
                    "priority_level": row["priority_level"],
                },
            )
        self.stdout.write(self.style.SUCCESS(f"{len(results)} ta murojaat GeoAI tahlilidan o‘tkazildi."))
