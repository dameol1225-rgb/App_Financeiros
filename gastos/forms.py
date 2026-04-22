from django import forms

from gastos.models import Gasto


class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = (
            "nome",
            "valor_total",
            "quantidade_parcelas",
            "dia_vencimento",
            "categoria",
            "data_inicio",
        )
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Cartao Nubank"}),
            "valor_total": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "quantidade_parcelas": forms.NumberInput(attrs={"min": "1", "max": "48"}),
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_valor_total(self):
        value = self.cleaned_data["valor_total"]
        if value <= 0:
            raise forms.ValidationError("Informe um valor maior que zero.")
        return value
