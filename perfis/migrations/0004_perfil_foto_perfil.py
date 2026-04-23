from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("perfis", "0003_perfil_mostrar_funcoes_extras"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="foto_perfil",
            field=models.TextField(blank=True, default=""),
        ),
    ]
