from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from financeiro.constants import DUE_DAY_CHOICES
from perfis.models import Perfil


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    cor = models.CharField(max_length=20, default="#ff9f43")
    icone = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Gasto(models.Model):
    class Status(models.TextChoices):
        ATIVO = "ativo", "Ativo"
        QUITADO = "quitado", "Quitado"

    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name="gastos")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="gastos")
    nome = models.CharField(max_length=200)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade_parcelas = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(48)]
    )
    dia_vencimento = models.PositiveSmallIntegerField(choices=DUE_DAY_CHOICES)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ATIVO,
    )
    data_inicio = models.DateField(default=timezone.localdate)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("status", "dia_vencimento", "nome")

    def __str__(self):
        return f"{self.nome} - {self.perfil.nome}"

    @property
    def parcelas_restantes(self):
        return self.parcelas.filter(status=Parcela.Status.PENDENTE).count()

    @property
    def parcelas_pagas(self):
        return self.parcelas.filter(status=Parcela.Status.PAGO).count()


class Parcela(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PAGO = "pago", "Pago"

    gasto = models.ForeignKey(Gasto, on_delete=models.CASCADE, related_name="parcelas")
    numero = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    class Meta:
        ordering = ("numero",)
        unique_together = ("gasto", "numero")

    def __str__(self):
        return f"{self.gasto.nome} - parcela {self.numero}"
