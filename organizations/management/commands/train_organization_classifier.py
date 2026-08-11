import json
from collections import Counter
from pathlib import Path

import joblib
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from organizations.models import OrganizationPredictionFeedback


class Command(BaseCommand):
    help = "Tasdiqlangan feedbacklardan text -> organization ML modelini qayta o‘qitadi."

    def add_arguments(self, parser):
        parser.add_argument("--min-samples", type=int, default=30)
        parser.add_argument("--min-per-class", type=int, default=3)
        parser.add_argument("--test-size", type=float, default=0.2)

    def handle(self, *args, **options):
        qs = (
            OrganizationPredictionFeedback.objects
            .exclude(selected_organization__isnull=True)
            .exclude(text="")
            .select_related("selected_organization")
            .order_by("created_at")
        )
        samples = [(item.text.strip(), str(item.selected_organization_id)) for item in qs if item.text.strip()]
        if len(samples) < options["min_samples"]:
            raise CommandError(
                f"Dataset yetarli emas: {len(samples)} ta. Kamida {options['min_samples']} ta kerak."
            )

        counts = Counter(label for _, label in samples)
        allowed = {label for label, count in counts.items() if count >= options["min_per_class"]}
        samples = [(text, label) for text, label in samples if label in allowed]
        counts = Counter(label for _, label in samples)
        if len(counts) < 2:
            raise CommandError("Kamida 2 ta tashkilot sinfi bo‘lishi kerak.")

        x = [text for text, _ in samples]
        y = [label for _, label in samples]
        min_class_count = min(counts.values())
        can_test = len(samples) >= 20 and min_class_count >= 2

        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.98,
                sublinear_tf=True,
            )),
            ("classifier", LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=42,
            )),
        ])

        metrics = {"accuracy": None, "macro_f1": None, "classification_report": None}
        if can_test:
            x_train, x_test, y_train, y_test = train_test_split(
                x, y,
                test_size=options["test_size"],
                random_state=42,
                stratify=y,
            )
            pipeline.fit(x_train, y_train)
            prediction = pipeline.predict(x_test)
            metrics = {
                "accuracy": round(float(accuracy_score(y_test, prediction)), 6),
                "macro_f1": round(float(f1_score(y_test, prediction, average="macro")), 6),
                "classification_report": classification_report(
                    y_test, prediction, output_dict=True, zero_division=0
                ),
            }

        # Yakuniy model barcha mavjud namunada o‘qitiladi.
        pipeline.fit(x, y)

        ml_dir = Path(settings.BASE_DIR) / "ml"
        ml_dir.mkdir(parents=True, exist_ok=True)
        model_path = ml_dir / "organization_classifier.pkl"
        meta_path = ml_dir / "organization_classifier_meta.json"
        joblib.dump(pipeline, model_path)

        organization_names = {
            str(item.selected_organization_id): item.selected_organization.name
            for item in qs if item.selected_organization_id
        }
        metadata = {
            "trained_at": timezone.now().isoformat(),
            "samples": len(samples),
            "classes": len(counts),
            "class_counts": dict(counts),
            "organization_names": organization_names,
            **metrics,
        }
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Model saqlandi: {model_path}"))
        self.stdout.write(f"Namunalar: {len(samples)} | Sinflar: {len(counts)}")
        if metrics["accuracy"] is not None:
            self.stdout.write(f"Accuracy: {metrics['accuracy']} | Macro F1: {metrics['macro_f1']}")
        else:
            self.stdout.write("Test metrikasi hisoblanmadi: dataset hali kichik.")
