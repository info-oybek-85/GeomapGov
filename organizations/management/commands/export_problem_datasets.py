from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.management.base import BaseCommand

from reports.models import Report

try:
    from organizations.models import OrganizationPredictionFeedback
except ImportError:  # V2 feedback patch hali o‘rnatilmagan bo‘lsa ham ishlaydi.
    OrganizationPredictionFeedback = None


DATASET_COLUMNS = [
    "record_id",
    "text",
    "primary_problem",
    "secondary_problems",
    "primary_organization",
    "supporting_organizations",
    "priority",
    "latitude",
    "longitude",
    "district",
    "source_type",
    "expert_verified",
    "split",
    "notes",
]

# Pilot bosqich uchun boshqariladigan lug‘at. Keyinchalik admin panel orqali
# tahrirlanadigan modelga ko‘chirish mumkin.
PROBLEM_RULES = {
    "ELEC_TRANSFORMER": {
        "family": "electricity",
        "priority": "Kritik",
        "keywords": ["transformator", "podstansiya", "transformator yondi", "transformator portladi"],
    },
    "ELEC_WIRE": {
        "family": "electricity",
        "priority": "Kritik",
        "keywords": ["sim uzildi", "sim uzilgan", "ochiq sim", "elektr simi", "uchqun", "kabel uzildi"],
    },
    "ELEC_POLE": {
        "family": "electricity",
        "priority": "Yuqori",
        "keywords": ["elektr ustuni", "ustun qiyshaygan", "ustun yiqilgan", "simyog‘och", "simyogoch"],
    },
    "ELEC_STREET_LIGHT": {
        "family": "electricity",
        "priority": "O‘rta",
        "keywords": ["ko‘cha yoritgichi", "kocha yoritgichi", "fonar", "ko‘cha qorong‘i", "kocha qorongi"],
    },
    "ELEC_VOLTAGE": {
        "family": "electricity",
        "priority": "Yuqori",
        "keywords": ["kuchlanish", "tok past", "tok yuqori", "miltillaydi", "bir faza", "faza yo‘q"],
    },
    "ELEC_OUTAGE": {
        "family": "electricity",
        "priority": "Yuqori",
        "keywords": ["svet yo‘q", "svet yoq", "tok yo‘q", "tok yoq", "elektr yo‘q", "chiroq yonmayapti", "elektr uzildi"],
    },
    "ECO_TREE_FALL": {
        "family": "ecology",
        "priority": "Yuqori",
        "keywords": ["daraxt qulagan", "daraxt yiqilgan", "shox sinib", "daraxt shoxi", "daraxt simga"],
    },
    "ECO_ILLEGAL_DUMP": {
        "family": "ecology",
        "priority": "Yuqori",
        "keywords": ["noqonuniy chiqindi", "chiqindi tashlamoqda", "axlat tashlamoqda", "chiqindi poligoni"],
    },
    "ECO_AIR": {
        "family": "ecology",
        "priority": "Yuqori",
        "keywords": ["qora tutun", "tutun", "badbo‘y hid", "badboy hid", "havo iflos", "plastik yoq"],
    },
    "ECO_WATER_POLLUTION": {
        "family": "ecology",
        "priority": "Kritik",
        "keywords": ["oqova suv", "suv iflos", "ariqqa chiqindi", "suv qoray", "kanalga chiqindi"],
    },
    "ECO_WASTE": {
        "family": "ecology",
        "priority": "O‘rta",
        "keywords": ["chiqindi", "axlat", "konteyner to‘lgan", "konteyner tolgan", "olib ketilmayapti"],
    },
    "LAND_CLEANING": {
        "family": "ecology",
        "priority": "Past",
        "keywords": ["ko‘cha supurilmagan", "kocha supurilmagan", "hudud iflos", "tozalanmagan"],
    },
    "LAND_GREEN": {
        "family": "ecology",
        "priority": "Past",
        "keywords": ["ko‘kalamzor", "kokalamzor", "daraxt ekish", "gulzor", "yashil hudud", "daraxt qurigan"],
    },
}

ELECTRIC_ORG_WORDS = ("elektr", "energet", "hududiy elektr", "het")
ECO_ORG_WORDS = ("ekolog", "obodon", "chiqindi", "tozalik")


def normalize_text(value: str) -> str:
    value = (value or "").lower().replace("’", "'").replace("‘", "'")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def detect_problem_labels(text: str) -> list[str]:
    normalized = normalize_text(text)
    scores: list[tuple[str, int]] = []
    for code, rule in PROBLEM_RULES.items():
        score = sum(1 for keyword in rule["keywords"] if normalize_text(keyword) in normalized)
        if score:
            scores.append((code, score))
    scores.sort(key=lambda item: (-item[1], item[0]))
    return [code for code, _ in scores]


def deterministic_split(report_id: str) -> str:
    # Har eksportda bir xil yozuv bir xil splitda qoladi: 80/10/10.
    bucket = int(hashlib.sha1(report_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "test"


def org_family(name: str) -> str | None:
    normalized = normalize_text(name)
    if any(word in normalized for word in ELECTRIC_ORG_WORDS):
        return "electricity"
    if any(word in normalized for word in ECO_ORG_WORDS):
        return "ecology"
    return None


def report_text(report: Report) -> str:
    title = getattr(report, "title", "") or ""
    description = getattr(report, "description", "") or ""
    return f"{title}. {description}".strip(". ")


def organization_name(report: Report, feedback) -> str:
    selected = getattr(feedback, "selected_organization", None) if feedback else None
    if selected:
        return selected.name
    organization = getattr(report, "organization", None)
    return organization.name if organization else ""


def feedback_for_reports(report_ids: Iterable[str]) -> dict[str, object]:
    if OrganizationPredictionFeedback is None:
        return {}
    result = {}
    rows = (
        OrganizationPredictionFeedback.objects.filter(report_id__in=report_ids)
        .select_related("selected_organization", "predicted_organization")
        .order_by("report_id", "-created_at")
    )
    for row in rows:
        key = str(row.report_id)
        result.setdefault(key, row)
    return result


def row_for_report(report: Report, feedback) -> tuple[str, list[str], list[str]]:
    text = report_text(report)
    labels = detect_problem_labels(text)
    org_name = organization_name(report, feedback)
    family = org_family(org_name)

    # Tashkilot ma’lum, lekin matnda aniq sub-label topilmasa, umumiy label.
    if not labels and family == "electricity":
        labels = ["ELEC_OUTAGE"]
    elif not labels and family == "ecology":
        labels = ["ECO_WASTE"]

    primary = labels[0] if labels else ""
    secondary = labels[1:]

    priorities = [PROBLEM_RULES[label]["priority"] for label in labels if label in PROBLEM_RULES]
    order = {"Kritik": 4, "Yuqori": 3, "O‘rta": 2, "Past": 1}
    priority = max(priorities, key=lambda value: order[value]) if priorities else ""

    detected_families = {
        PROBLEM_RULES[label]["family"] for label in labels if label in PROBLEM_RULES
    }
    dataset_family = family or (next(iter(detected_families)) if len(detected_families) == 1 else None)

    accepted = bool(getattr(feedback, "accepted", False)) if feedback else False
    selected_org = getattr(feedback, "selected_organization", None) if feedback else None
    expert_verified = "Ha" if accepted and selected_org else "Yo‘q"

    notes = []
    if feedback:
        notes.append("label_source=feedback")
        notes.append(f"ai_accepted={'yes' if accepted else 'no'}")
        confidence = getattr(feedback, "confidence", None)
        if confidence is not None:
            notes.append(f"confidence={float(confidence):.4f}")
    elif org_name:
        notes.append("label_source=report_organization")
    else:
        notes.append("label_source=keyword_only")

    if labels:
        notes.append("detected=" + ";".join(labels))

    row = [
        str(report.id),
        text,
        primary,
        "; ".join(secondary),
        org_name,
        "",  # Hamkor tashkilot ekspert tekshiruvda to‘ldiriladi.
        priority,
        str(report.latitude) if report.latitude is not None else "",
        str(report.longitude) if report.longitude is not None else "",
        "",  # District modeli loyihada mavjud bo‘lsa keyin ulanadi.
        "real",
        expert_verified,
        deterministic_split(str(report.id)),
        "; ".join(notes),
    ]
    return dataset_family or "unlabeled", labels, row


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(DATASET_COLUMNS)
        writer.writerows(rows)


class Command(BaseCommand):
    help = (
        "SmartGeoAI real murojaatlarini Elektr, Ekologiya, murakkab va "
        "yorliqlanmagan CSV datasetlariga eksport qiladi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=str(Path(settings.BASE_DIR) / "data" / "problem_datasets"),
            help="CSV fayllar yoziladigan papka.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Sinov uchun maksimal murojaat soni. 0 = cheklanmagan.",
        )
        parser.add_argument(
            "--only-verified",
            action="store_true",
            help="Faqat fuqaro AI tavsiyasini qabul qilgan feedback yozuvlarini eksport qiladi.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]).resolve()
        qs = Report.objects.select_related("organization", "user").order_by("created_at", "id")
        if options["limit"]:
            qs = qs[: options["limit"]]

        reports = list(qs)
        feedback_map = feedback_for_reports([str(report.id) for report in reports])

        datasets = {
            "electricity": [],
            "ecology": [],
            "complex": [],
            "unlabeled": [],
            "all": [],
        }
        label_counts = Counter()

        for report in reports:
            feedback = feedback_map.get(str(report.id))
            if options["only_verified"] and not (
                feedback and getattr(feedback, "accepted", False)
            ):
                continue

            family, labels, row = row_for_report(report, feedback)
            datasets["all"].append(row)
            label_counts.update(labels)

            families = {
                PROBLEM_RULES[label]["family"] for label in labels if label in PROBLEM_RULES
            }
            if len(labels) > 1 or len(families) > 1:
                datasets["complex"].append(row)
            elif family == "electricity":
                datasets["electricity"].append(row)
            elif family == "ecology":
                datasets["ecology"].append(row)
            else:
                datasets["unlabeled"].append(row)

        files = {
            "electricity": output_dir / "electricity_real.csv",
            "ecology": output_dir / "ecology_real.csv",
            "complex": output_dir / "complex_cases_real.csv",
            "unlabeled": output_dir / "unlabeled_for_expert.csv",
            "all": output_dir / "all_real_reports.csv",
        }
        for key, path in files.items():
            write_csv(path, datasets[key])

        stats = {
            "total_reports": len(datasets["all"]),
            "electricity": len(datasets["electricity"]),
            "ecology": len(datasets["ecology"]),
            "complex": len(datasets["complex"]),
            "unlabeled": len(datasets["unlabeled"]),
            "expert_verified": sum(1 for row in datasets["all"] if row[11] == "Ha"),
            "labels": dict(label_counts.most_common()),
            "files": {key: str(path) for key, path in files.items()},
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "dataset_stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self.stdout.write(self.style.SUCCESS("Dataset eksporti yakunlandi."))
        self.stdout.write(f"Jami: {stats['total_reports']}")
        self.stdout.write(f"Elektr: {stats['electricity']}")
        self.stdout.write(f"Ekologiya: {stats['ecology']}")
        self.stdout.write(f"Murakkab: {stats['complex']}")
        self.stdout.write(f"Ekspert tekshiruvi kutilmoqda: {stats['unlabeled']}")
        self.stdout.write(f"Papka: {output_dir}")
