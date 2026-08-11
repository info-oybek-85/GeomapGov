from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse, NoReverseMatch

try:
    from accounts.models import User
except Exception:
    from django.contrib.auth import get_user_model
    User = get_user_model()


class Command(BaseCommand):
    help = "SmartGeoAI v1.0 FINAL uchun read-only smoke test (v1.1 hotfix)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            dest="json_path",
            default="data/final_audit/smartgeoai_smoke_test.json",
        )

    def handle(self, *args, **options):
        checks = []

        def add(group, name, ok, detail="", severity="error"):
            checks.append({
                "group": group,
                "name": name,
                "ok": bool(ok),
                "detail": str(detail),
                "severity": severity,
            })

        def make_client():
            # Django test Client default host = "testserver".
            # Project ALLOWED_HOSTS intentionally doesn't include it.
            # Use an already allowed local host instead.
            return Client(HTTP_HOST="127.0.0.1")

        def test_get(client, group, name, url_name, expected=(200, 302, 301, 403)):
            try:
                url = reverse(url_name)
            except NoReverseMatch as e:
                add(group, name, False, f"reverse xato: {e}", "critical")
                return

            try:
                response = client.get(url, follow=False)
                ok = response.status_code in expected
                add(
                    group,
                    name,
                    ok,
                    f"{url} -> HTTP {response.status_code}",
                    "critical" if not ok else "info",
                )
            except Exception as e:
                add(group, name, False, repr(e), "critical")

        # ---------------------------------------------------------
        # 1. Anonymous/public
        # ---------------------------------------------------------
        anonymous = make_client()

        public_checks = [
            ("Public portal", "dashboard:public_portal", (200,)),
            ("Main entry", "dashboard:home", (200, 302)),
            ("Login", "dashboard:login", (200,)),
            ("Public map JSON", "dashboard:public_resolved_map_data", (200,)),
            ("Public analytics JSON", "dashboard:public_analytics_data", (200,)),
            ("Public analytics CSV", "dashboard:public_analytics_csv", (200,)),
            ("Research transparency JSON", "dashboard:public_research_data", (200,)),
        ]

        for label, name, expected in public_checks:
            test_get(anonymous, "public", label, name, expected)

        # Protected pages should not expose internal pages anonymously.
        protected = [
            ("Platform Center protection", "dashboard:platform_center"),
            ("GSOR Center protection", "dashboard:gsor_center"),
            ("GeoAI Lab protection", "dashboard:geoai_lab"),
            ("Expert Validation protection", "dashboard:expert_validation_queue"),
            ("GeoAI Analytics protection", "geoai:analytics"),
            ("System Evaluation protection", "geoai:system_evaluation"),
        ]
        for label, name in protected:
            try:
                url = reverse(name)
                r = anonymous.get(url, follow=False)
                ok = r.status_code in (302, 301, 403)
                add(
                    "security",
                    label,
                    ok,
                    f"{url} -> HTTP {r.status_code}",
                    "critical" if not ok else "info",
                )
            except Exception as e:
                add("security", label, False, repr(e), "critical")

        # ---------------------------------------------------------
        # 2. Superadmin
        # ---------------------------------------------------------
        superuser = User.objects.filter(is_superuser=True, is_active=True).first()
        if superuser:
            c = make_client()
            c.force_login(superuser)

            for label, name in [
                ("Admin dashboard", "dashboard:admin_home"),
                ("Platform Center", "dashboard:platform_center"),
                ("GSOR Center", "dashboard:gsor_center"),
                ("GeoAI Lab", "dashboard:geoai_lab"),
                ("Expert Validation", "dashboard:expert_validation_queue"),
                ("GeoAI Analytics", "geoai:analytics"),
                ("System Evaluation", "geoai:system_evaluation"),
                ("Complaints", "dashboard:complaints"),
                ("Organizations", "dashboard:organizations"),
                ("Users", "dashboard:users"),
            ]:
                test_get(c, "superadmin", label, name, (200, 302))
        else:
            add(
                "superadmin",
                "Superuser mavjudligi",
                False,
                "Faol superuser topilmadi",
                "warning",
            )

        # ---------------------------------------------------------
        # 3. Dispatcher
        # ---------------------------------------------------------
        dispatcher = None
        try:
            dispatcher = User.objects.filter(is_active=True, user_type="DISPATCHER").first()
        except Exception:
            pass

        if dispatcher:
            c = make_client()
            c.force_login(dispatcher)
            for label, name in [
                ("Dispatcher dashboard", "dashboard:org-dashboard"),
                ("Dispatcher reports", "dashboard:org_reports"),
                ("Dispatcher users", "dashboard:org_users"),
            ]:
                test_get(c, "dispatcher", label, name, (200, 302, 403))
        else:
            add(
                "dispatcher",
                "Dispatcher test user",
                False,
                "Faol DISPATCHER topilmadi; avtomatik rol testi o'tkazilmadi",
                "warning",
            )

        # ---------------------------------------------------------
        # 4. Worker / executor
        # ---------------------------------------------------------
        worker = None
        try:
            worker = User.objects.filter(is_active=True, user_type="EXECUTOR").first()
        except Exception:
            pass

        if worker:
            c = make_client()
            c.force_login(worker)
            for label, name in [
                ("Worker tasks", "dashboard:worker_tasks"),
                ("Worker resolved", "dashboard:worker_resolved"),
            ]:
                test_get(c, "worker", label, name, (200, 302, 403))
        else:
            add(
                "worker",
                "Worker test user",
                False,
                "Faol EXECUTOR topilmadi; avtomatik rol testi o'tkazilmadi",
                "warning",
            )

        # ---------------------------------------------------------
        # 5. Summary
        # ---------------------------------------------------------
        failed = [x for x in checks if not x["ok"]]
        critical = [x for x in failed if x["severity"] == "critical"]
        errors = [x for x in failed if x["severity"] == "error"]
        warnings = [x for x in failed if x["severity"] == "warning"]

        result = {
            "summary": {
                "checks_total": len(checks),
                "passed": len(checks) - len(failed),
                "failed": len(failed),
                "critical": len(critical),
                "errors": len(errors),
                "warnings": len(warnings),
                "release_ready": len(critical) == 0 and len(errors) == 0,
            },
            "checks": checks,
        }

        out_path = Path(settings.BASE_DIR) / options["json_path"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("SMARTGEOAI FINAL SMOKE TEST v1.1"))
        self.stdout.write("-" * 64)

        for x in checks:
            if x["ok"]:
                mark = self.style.SUCCESS("PASS")
            elif x["severity"] == "warning":
                mark = self.style.WARNING("WARN")
            else:
                mark = self.style.ERROR("FAIL")

            self.stdout.write(
                f"[{mark}] {x['group']}: {x['name']} -> {x['detail']}"
            )

        s = result["summary"]
        self.stdout.write("-" * 64)
        self.stdout.write(f"Jami test: {s['checks_total']}")
        self.stdout.write(self.style.SUCCESS(f"PASS: {s['passed']}"))
        self.stdout.write(f"FAIL/WARN: {s['failed']}")
        self.stdout.write(f"Critical: {s['critical']}")
        self.stdout.write(f"Errors: {s['errors']}")
        self.stdout.write(f"Warnings: {s['warnings']}")

        if s["release_ready"]:
            self.stdout.write(self.style.SUCCESS("STATUS: SMOKE TEST PASSED"))
        else:
            self.stdout.write(self.style.ERROR("STATUS: TUZATISH KERAK"))

        self.stdout.write(f"JSON: {out_path}")
