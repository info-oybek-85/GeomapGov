from __future__ import annotations

import csv
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from organizations.gsor_engine import rank_organizations, routing_decision

def _split_orgs(value: str):
    if not value:
        return []
    for sep in (";", "|"):
        value = value.replace(sep, ",")
    return [x.strip() for x in value.split(",") if x.strip()]

class Command(BaseCommand):
    help = "GSOR datasetida Top-1/Top-3 va MRR ni baholaydi."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--output", type=str, default="data/gsor/gsor_evaluation.json")
        parser.add_argument("--predictions", type=str, default="data/gsor/gsor_predictions.csv")

    def handle(self, *args, **options):
        src = Path(options["csv_path"])
        if not src.exists():
            raise CommandError(f"Fayl topilmadi: {src}")

        rows = []
        with src.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                text = (row.get("text") or row.get("description") or "").strip()
                if not text:
                    continue
                true_org = (row.get("primary_organization") or row.get("final_organization") or "").strip()
                alternatives = _split_orgs(row.get("alternative_organizations") or row.get("supporting_organizations") or "")
                rows.append((row, text, true_org, alternatives))

        if not rows:
            raise CommandError("Baholash uchun matnli yozuv topilmadi.")

        top1_ok = top3_ok = labeled = 0
        reciprocal_sum = 0.0
        prediction_rows = []

        for raw, text, true_org, alternatives in rows:
            preds = rank_organizations(text, top_k=3)
            pred_orgs = [p.organization for p in preds]
            accepted_truths = [x for x in [true_org, *alternatives] if x]
            rank = None
            if accepted_truths:
                labeled += 1
                for idx, org in enumerate(pred_orgs, start=1):
                    if org in accepted_truths:
                        rank = idx
                        break
                if rank == 1:
                    top1_ok += 1
                if rank is not None and rank <= 3:
                    top3_ok += 1
                    reciprocal_sum += 1.0 / rank

            prediction_rows.append({
                "record_id": raw.get("record_id") or raw.get("id") or "",
                "text": text,
                "true_primary_organization": true_org,
                "alternative_organizations": "; ".join(alternatives),
                "top1": pred_orgs[0] if pred_orgs else "",
                "top1_score": preds[0].score if preds else 0,
                "top2": pred_orgs[1] if len(preds) > 1 else "",
                "top2_score": preds[1].score if len(preds) > 1 else 0,
                "top3": pred_orgs[2] if len(preds) > 2 else "",
                "top3_score": preds[2].score if len(preds) > 2 else 0,
                "matched_terms": "; ".join(preds[0].matched_terms if preds else []),
                "decision": routing_decision(preds),
                "rank_of_truth": rank or "",
            })

        metrics = {
            "records_total": len(rows),
            "records_with_reference_label": labeled,
            "top1_accuracy": round(top1_ok / labeled, 6) if labeled else None,
            "top3_accuracy": round(top3_ok / labeled, 6) if labeled else None,
            "mrr": round(reciprocal_sum / labeled, 6) if labeled else None,
            "note": "GSOR v1 lexical-semantic baseline; Geo va Historical scorerlar keyingi bosqichda ulanadi.",
        }

        out = Path(options["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

        pred = Path(options["predictions"])
        pred.parent.mkdir(parents=True, exist_ok=True)
        with pred.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(prediction_rows[0].keys()))
            writer.writeheader()
            writer.writerows(prediction_rows)

        self.stdout.write(self.style.SUCCESS("GSOR baholash yakunlandi."))
        self.stdout.write(f"Jami yozuv: {len(rows)}")
        self.stdout.write(f"Reference label: {labeled}")
        if labeled:
            self.stdout.write(f"Top-1 Accuracy: {metrics['top1_accuracy']:.3f}")
            self.stdout.write(f"Top-3 Accuracy: {metrics['top3_accuracy']:.3f}")
            self.stdout.write(f"MRR: {metrics['mrr']:.3f}")
        self.stdout.write(f"Metrikalar: {out}")
        self.stdout.write(f"Predictionlar: {pred}")
