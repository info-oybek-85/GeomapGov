from django.core.management.base import BaseCommand

from geoai.models import ComplaintAnalysis
from geoai.risk_services import analyze_risk


class Command(BaseCommand):
    help = "DBSCAN + priority-weighted KDE orqali klasterlar va integral xavf indeksini hisoblaydi."

    def add_arguments(self, parser):
        parser.add_argument("--eps", type=float, default=35.0, help="DBSCAN epsilon, km")
        parser.add_argument("--min-samples", type=int, default=3, help="DBSCAN MinPts")
        parser.add_argument("--bandwidth", type=float, default=45.0, help="WKDE bandwidth, km")

    def handle(self, *args, **options):
        qs = ComplaintAnalysis.objects.select_related("report").exclude(
            report__latitude__isnull=True
        ).exclude(report__longitude__isnull=True)
        summaries, noise = analyze_risk(
            qs,
            eps_km=options["eps"],
            min_samples=options["min_samples"],
            bandwidth_km=options["bandwidth"],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Risk tahlili yakunlandi: {len(summaries)} klaster, {noise} shovqin nuqta."
        ))
        for item in summaries[:10]:
            self.stdout.write(
                f"K{item.label}: n={item.count}, H={item.risk_index:.3f}, {item.risk_level}"
            )
