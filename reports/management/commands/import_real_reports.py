from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from reports.models import Report


class Command(BaseCommand):
    help = (
        "Eski SQLite bazadagi reports_report yozuvlarini "
        "joriy lokal bazaga xavfsiz import qiladi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            required=True,
            help="Eski SQLite bazaning yo‘li, masalan: old_db.sqlite3",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Joriy reports_report yozuvlarini o‘chirib, manbadagilar bilan almashtiradi.",
        )

    def handle(self, *args, **options):
        source_path = Path(options["source"]).resolve()
        replace = options["replace"]

        destination_path = Path(settings.DATABASES["default"]["NAME"]).resolve()

        if not source_path.exists():
            raise CommandError(
                f"Manba baza topilmadi: {source_path}"
            )

        if source_path == destination_path:
            raise CommandError(
                "Manba va joriy baza bir xil fayl bo‘lishi mumkin emas."
            )

        if not replace:
            raise CommandError(
                "Mavjud murojaatlarni almashtirish uchun --replace parametrini kiriting."
            )

        source_conn = sqlite3.connect(str(source_path))
        source_conn.row_factory = sqlite3.Row

        try:
            source_cursor = source_conn.cursor()

            table_exists = source_cursor.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'reports_report'
                """
            ).fetchone()

            if not table_exists:
                raise CommandError(
                    "Manba bazada reports_report jadvali topilmadi."
                )

            source_count = source_cursor.execute(
                "SELECT COUNT(*) FROM reports_report"
            ).fetchone()[0]

            if source_count == 0:
                raise CommandError(
                    "Manba bazadagi reports_report jadvali bo‘sh."
                )

            source_columns = {
                row["name"]
                for row in source_cursor.execute(
                    "PRAGMA table_info(reports_report)"
                ).fetchall()
            }

            local_columns = [
                field.column
                for field in Report._meta.local_fields
            ]

            missing_columns = [
                column
                for column in local_columns
                if column not in source_columns
            ]

            if missing_columns:
                raise CommandError(
                    "Manba bazada quyidagi zarur ustunlar yo‘q: "
                    + ", ".join(missing_columns)
                )

            # Foreign key qiymatlarini importdan oldin tekshirish
            source_organization_ids = {
                row[0]
                for row in source_cursor.execute(
                    """
                    SELECT DISTINCT organization_id
                    FROM reports_report
                    WHERE organization_id IS NOT NULL
                    """
                ).fetchall()
            }

            source_user_ids = {
                row[0]
                for row in source_cursor.execute(
                    """
                    SELECT DISTINCT user_id
                    FROM reports_report
                    WHERE user_id IS NOT NULL
                    """
                ).fetchall()
            }

            with connection.cursor() as cursor:
                local_organization_ids = {
                    row[0]
                    for row in cursor.execute(
                        "SELECT id FROM organizations_organization"
                    ).fetchall()
                }

                local_user_ids = {
                    row[0]
                    for row in cursor.execute(
                        "SELECT id FROM users_user"
                    ).fetchall()
                }

            missing_organizations = (
                source_organization_ids - local_organization_ids
            )
            missing_users = source_user_ids - local_user_ids

            if missing_organizations:
                raise CommandError(
                    "Lokal bazada quyidagi organization_id mavjud emas: "
                    + ", ".join(map(str, sorted(missing_organizations)))
                )

            if missing_users:
                raise CommandError(
                    "Lokal bazada quyidagi user_id mavjud emas: "
                    + ", ".join(map(str, sorted(missing_users)))
                )

            backup_dir = destination_path.parent / "db_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = (
                backup_dir
                / f"db_before_real_import_{timestamp}.sqlite3"
            )

            shutil.copy2(destination_path, backup_path)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Backup yaratildi: {backup_path}"
                )
            )

            column_sql = ", ".join(
                f'"{column}"' for column in local_columns
            )

            source_rows = source_cursor.execute(
                f"""
                SELECT {column_sql}
                FROM reports_report
                ORDER BY id
                """
            ).fetchall()

            placeholders = ", ".join(
                ["%s"] * len(local_columns)
            )

            insert_sql = (
                f'INSERT INTO "reports_report" ({column_sql}) '
                f"VALUES ({placeholders})"
            )

            values = [
                tuple(row[column] for column in local_columns)
                for row in source_rows
            ]

            old_count = Report.objects.count()

            with transaction.atomic():
                # ORM orqali o‘chirish bog‘liq GeoAI yozuvlarini ham
                # xavfsiz cascade qilishga yordam beradi.
                Report.objects.all().delete()

                with connection.cursor() as cursor:
                    cursor.executemany(insert_sql, values)

            new_count = Report.objects.count()

            if new_count != source_count:
                raise CommandError(
                    f"Import soni mos emas: "
                    f"manba={source_count}, lokal={new_count}. "
                    f"Backup: {backup_path}"
                )

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS("Import muvaffaqiyatli tugadi.")
            )
            self.stdout.write(f"Oldingi murojaatlar: {old_count}")
            self.stdout.write(f"Import qilingan: {new_count}")
            self.stdout.write(f"Manba: {source_path}")
            self.stdout.write(f"Backup: {backup_path}")

        finally:
            source_conn.close()