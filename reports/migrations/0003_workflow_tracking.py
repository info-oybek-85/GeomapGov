from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reports", "0002_alter_report_latitude_alter_report_longitude")]

    operations = [
        migrations.AddField(model_name="report", name="accepted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="report", name="assigned_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="report", name="work_started_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="report", name="work_completed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="report", name="citizen_confirmed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="report", name="deadline_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="report", name="completion_note", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="report", name="citizen_confirmation_note", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="reportassignment", name="started_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="reportassignment", name="completed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="reportassignment", name="deadline_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="reportassignment", name="completion_note", field=models.TextField(blank=True, default="")),
        migrations.AlterField(
            model_name="report",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"), ("sent", "Sent to organization"), ("read", "Read by organization"),
                    ("accepted", "Accepted by organization"), ("assigned", "Assigned to staff"),
                    ("in_progress", "In progress"), ("pending_confirmation", "Pending citizen confirmation"),
                    ("resolved", "Resolved"), ("reopened", "Reopened"), ("rejected", "Rejected"),
                    ("redirected", "Redirected"),
                ],
                default="new", max_length=24,
            ),
        ),
    ]
