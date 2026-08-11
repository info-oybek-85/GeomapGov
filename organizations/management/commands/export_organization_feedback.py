import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from organizations.models import OrganizationPredictionFeedback


class Command(BaseCommand):
    help = "Tashkilot tavsiyasi feedbacklarini ML dataset CSV fayliga eksport qiladi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="data/organization_feedback.csv",
            help="CSV fayl yo‘li (default: data/organization_feedback.csv)",
        )
        parser.add_argument(
            "--accepted-only",
            action="store_true",
            help="Faqat AI tavsiyasi qabul qilingan yozuvlarni eksport qiladi.",
        )

    def handle(self, *args, **options):
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)

        qs = OrganizationPredictionFeedback.objects.select_related(
            "predicted_organization", "selected_organization", "report", "user"
        ).exclude(selected_organization__isnull=True).order_by("created_at")
        if options["accepted_only"]:
            qs = qs.filter(accepted=True)

        rows = list(qs)
        with output.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "feedback_id", "text", "organization_id", "organization_name",
                    "predicted_organization_id", "predicted_organization_name",
                    "confidence", "accepted", "matched_keywords", "created_at",
                ],
            )
            writer.writeheader()
            for item in rows:
                selected = item.selected_organization
                predicted = item.predicted_organization
                writer.writerow({
                    "feedback_id": item.pk,
                    "text": item.text,
                    "organization_id": selected.pk if selected else "",
                    "organization_name": selected.name if selected else "",
                    "predicted_organization_id": predicted.pk if predicted else "",
                    "predicted_organization_name": predicted.name if predicted else "",
                    "confidence": item.confidence,
                    "accepted": int(item.accepted),
                    "matched_keywords": "|".join(item.matched_keywords or []),
                    "created_at": item.created_at.isoformat(),
                })

        self.stdout.write(self.style.SUCCESS(f"{len(rows)} ta yozuv eksport qilindi: {output}"))
