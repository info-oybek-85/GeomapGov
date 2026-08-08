from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("organizations", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="organization",
            name="organization_icon",
            field=models.ImageField(blank=True, null=True, upload_to="organization_icons/"),
        ),
    ]
