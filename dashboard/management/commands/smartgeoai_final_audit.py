from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.template.loader import get_template
from django.urls import get_resolver, reverse, NoReverseMatch


class Command(BaseCommand):
    help = "SmartGeoAI v1.0 FINAL uchun read-only audit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            dest="json_path",
            default="data/final_audit/smartgeoai_final_audit.json",
            help="JSON natija fayli",
        )

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        results = {
            "summary": {},
            "checks": [],
        }

        def add(group, name, ok, detail="", severity="info"):
            results["checks"].append({
                "group": group,
                "name": name,
                "ok": bool(ok),
                "detail": str(detail),
                "severity": severity,
            })

        # 1. Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                value = cursor.fetchone()[0]
            add("database", "DB connection", value == 1, "SELECT 1 OK", "critical")
        except Exception as e:
            add("database", "DB connection", False, repr(e), "critical")

        # 2. Required tables
        expected_tables = [
            "reports_report",
            "organizations_organization",
            "organizations_organizationpredictionfeedback",
        ]
        try:
            tables = set(connection.introspection.table_names())
            for table in expected_tables:
                add(
                    "database",
                    f"Table: {table}",
                    table in tables,
                    "mavjud" if table in tables else "TOPILMADI",
                    "critical" if table.endswith("organizationpredictionfeedback") else "error",
                )
        except Exception as e:
            add("database", "Table introspection", False, repr(e), "critical")

        # 3. Named URLs
        url_names = [
            ("dashboard:home", "Main entry"),
            ("dashboard:login", "Login"),
            ("dashboard:public_portal", "Public portal"),
            ("dashboard:platform_center", "Platform center"),
            ("dashboard:gsor_center", "GSOR center"),
            ("dashboard:geoai_lab", "GeoAI Lab"),
            ("dashboard:expert_validation_queue", "Expert validation"),
            ("geoai:analytics", "GeoAI analytics"),
            ("geoai:system_evaluation", "System evaluation"),
        ]
        for name, label in url_names:
            try:
                url = reverse(name)
                add("urls", label, True, url, "error")
            except NoReverseMatch as e:
                add("urls", label, False, f"{name}: {e}", "error")
            except Exception as e:
                add("urls", label, False, repr(e), "error")

        # 4. Templates
        templates = [
            "base.html",
            "public/portal.html",
            "superadmin/dashboard.html",
            "superadmin/platform_center.html",
            "superadmin/gsor_center.html",
            "superadmin/geoai_lab.html",
        ]
        for tpl in templates:
            try:
                get_template(tpl)
                add("templates", tpl, True, "load OK", "error")
            except Exception as e:
                add("templates", tpl, False, repr(e), "error")

        # 5. Static files
        static_files = [
            "static/css/smartgeoai-portal.css",
            "static/js/smartgeoai-public-map.js",
            "static/js/smartgeoai-public-analytics.js",
            "static/js/smartgeoai-research-transparency.js",
            "static/img/smartgeoai-portal-banner.png",
        ]
        for rel in static_files:
            p = base / rel
            add(
                "static",
                rel,
                p.exists(),
                f"{p} | {p.stat().st_size} bytes" if p.exists() else f"{p} topilmadi",
                "warning",
            )

        # 6. Data / model artifacts
        artifacts = [
            "data/gsor/gsor_evaluation.json",
            "data/gsor/gsor_predictions.csv",
            "data/problem_datasets/verified_routing_dataset.csv",
        ]
        for rel in artifacts:
            p = base / rel
            detail = "topilmadi"
            if p.exists():
                detail = f"{p.stat().st_size} bytes"
                if p.suffix.lower() == ".json":
                    try:
                        obj = json.loads(p.read_text(encoding="utf-8"))
                        detail += f" | keys={list(obj.keys())[:8]}"
                    except Exception as e:
                        detail += f" | JSON error={e}"
            add("artifacts", rel, p.exists(), detail, "warning")

        # 7. Django settings
        debug = bool(getattr(settings, "DEBUG", False))
        add(
            "settings",
            "DEBUG",
            not debug,
            f"DEBUG={debug}",
            "warning",
        )

        allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
        add(
            "settings",
            "ALLOWED_HOSTS",
            bool(allowed_hosts),
            ", ".join(allowed_hosts) if allowed_hosts else "bo'sh",
            "warning",
        )

        bot_url = getattr(settings, "SMARTGEOAI_TELEGRAM_BOT_URL", "")
        add(
            "settings",
            "Telegram bot URL",
            bool(str(bot_url).strip()),
            bot_url or "sozlanmagan",
            "warning",
        )

        # 8. Route duplicates (by route string, rough but useful)
        try:
            resolver = get_resolver()
            flat = []

            def walk(patterns, prefix=""):
                for p in patterns:
                    route = prefix + str(p.pattern)
                    if hasattr(p, "url_patterns"):
                        walk(p.url_patterns, route)
                    else:
                        flat.append((route, getattr(p, "name", None)))

            walk(resolver.url_patterns)

            seen = {}
            duplicates = []
            for route, name in flat:
                if route in seen:
                    duplicates.append((route, seen[route], name))
                else:
                    seen[route] = name

            add(
                "urls",
                "Duplicate routes",
                len(duplicates) == 0,
                duplicates[:20] if duplicates else "yo'q",
                "warning",
            )
        except Exception as e:
            add("urls", "Duplicate routes", False, repr(e), "warning")

        # Summary
        failed = [x for x in results["checks"] if not x["ok"]]
        critical = [x for x in failed if x["severity"] == "critical"]
        errors = [x for x in failed if x["severity"] == "error"]
        warnings = [x for x in failed if x["severity"] == "warning"]

        results["summary"] = {
            "checks_total": len(results["checks"]),
            "passed": len(results["checks"]) - len(failed),
            "failed": len(failed),
            "critical": len(critical),
            "errors": len(errors),
            "warnings": len(warnings),
            "release_ready": len(critical) == 0 and len(errors) == 0,
        }

        output = base / options["json_path"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("SMARTGEOAI FINAL AUDIT"))
        self.stdout.write("-" * 60)

        for item in results["checks"]:
            if item["ok"]:
                mark = self.style.SUCCESS("PASS")
            else:
                mark = self.style.ERROR("FAIL")
            self.stdout.write(
                f"[{mark}] {item['group']}: {item['name']} -> {item['detail']}"
            )

        self.stdout.write("-" * 60)
        s = results["summary"]
        self.stdout.write(f"Jami check: {s['checks_total']}")
        self.stdout.write(self.style.SUCCESS(f"PASS: {s['passed']}"))
        self.stdout.write(self.style.ERROR(f"FAIL: {s['failed']}"))
        self.stdout.write(f"Critical: {s['critical']}")
        self.stdout.write(f"Errors: {s['errors']}")
        self.stdout.write(f"Warnings: {s['warnings']}")

        if s["release_ready"]:
            self.stdout.write(self.style.SUCCESS("STATUS: RELEASE CANDIDATE"))
        else:
            self.stdout.write(self.style.ERROR("STATUS: TUZATISHLAR KERAK"))

        self.stdout.write(f"JSON: {output}")
