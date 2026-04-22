from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("perfis", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="tema",
            field=models.CharField(
                choices=[("ocean", "Ocean"), ("black", "Black")],
                default="ocean",
                max_length=20,
            ),
        ),
    ]
