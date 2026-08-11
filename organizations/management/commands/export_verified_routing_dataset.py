import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from organizations.models import Organization, OrganizationPredictionFeedback


class Command(BaseCommand):
    help = "Ekspert tasdiqlagan Routing Engine datasetini CSV formatida eksport qiladi."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="data/problem_datasets/verified_routing_dataset.csv")

    def handle(self, *args, **options):
        output = Path(settings.BASE_DIR) / options["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        org_names = {str(o.pk): o.name for o in Organization.objects.all()}
        qs = OrganizationPredictionFeedback.objects.filter(
            expert_status__in=["verified", "corrected"]
        ).select_related("expert_primary_organization", "report", "reviewed_by").order_by("created_at")

        fields = [
            "feedback_id", "report_id", "text", "primary_problem", "secondary_problems",
            "primary_organization", "supporting_organizations", "priority",
            "expert_status", "reviewed_by", "reviewed_at",
        ]
        with output.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for item in qs:
                writer.writerow({
                    "feedback_id": item.pk,
                    "report_id": item.report_id or "",
                    "text": item.text,
                    "primary_problem": item.expert_primary_problem,
                    "secondary_problems": "; ".join(item.expert_secondary_problems or []),
                    "primary_organization": item.expert_primary_organization.name if item.expert_primary_organization else "",
                    "supporting_organizations": "; ".join(org_names.get(str(x), str(x)) for x in (item.expert_supporting_organizations or [])),
                    "priority": item.expert_priority,
                    "expert_status": item.expert_status,
                    "reviewed_by": item.reviewed_by.get_username() if item.reviewed_by else "",
                    "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else "",
                })
        self.stdout.write(self.style.SUCCESS(f"Ekspert dataset eksport qilindi: {output}"))
        self.stdout.write(f"Yozuvlar: {qs.count()}")
