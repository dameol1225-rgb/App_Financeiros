from django.core.management.base import BaseCommand

from perfis.services import ensure_default_setup


class Command(BaseCommand):
    help = "Cria o usuario principal, perfis padrao, categorias e parcelas salariais."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Redefine a senha inicial do usuario compartilhado.",
        )

    def handle(self, *args, **options):
        result = ensure_default_setup(reset_password=options["reset_password"])
        self.stdout.write(
            self.style.SUCCESS(
                "Seed concluido: "
                f"{result['user'].username}, "
                f"{result['profiles'].count()} perfis e "
                f"{result['categories'].count()} categorias."
            )
        )
