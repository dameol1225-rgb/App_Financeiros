from decimal import Decimal

from django.db import models
from django.utils import timezone

from financeiro.constants import DEFAULT_THEME, DUE_DAY_CHOICES, THEME_CHOICES


class Perfil(models.Model):
    nome = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    ordem = models.PositiveSmallIntegerField(default=0)
    tema = models.CharField(max_length=20, choices=THEME_CHOICES, default=DEFAULT_THEME)

    class Meta:
        ordering = ("ordem", "nome")

    def __str__(self):
        return self.nome

    @property
    def salario_total_mensal(self):
        return sum((item.valor for item in self.parcelas_salariais.all()), start=Decimal("0.00"))


class SalarioParcela(models.Model):
    perfil = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        related_name="parcelas_salariais",
    )
    dia_recebimento = models.PositiveSmallIntegerField(choices=DUE_DAY_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ("dia_recebimento",)
        unique_together = ("perfil", "dia_recebimento")

    def __str__(self):
        return f"{self.perfil.nome} - dia {self.dia_recebimento}"


class RendaExtra(models.Model):
    perfil = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        related_name="rendas_extras",
    )
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField(default=timezone.localdate)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-data", "-criado_em")

    def __str__(self):
        return f"{self.perfil.nome} - {self.descricao}"
