from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("perfis", "0002_perfil_tema"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="mostrar_funcoes_extras",
            field=models.BooleanField(default=True),
        ),
    ]
