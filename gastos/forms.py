from django import forms

from gastos.models import Categoria, Gasto


class GastoForm(forms.ModelForm):
    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.fields["categoria"].queryset = Categoria.objects.order_by("nome")
        self.fields["nome"].widget.attrs.update(
            {
                "list": "expense-name-options",
                "autocomplete": "off",
            }
        )
        self.fields["nome"].help_text = "Escolha um nome já usado ou digite um novo."
        self.saved_name_choices = []

        if profile:
            names = (
                profile.gastos.order_by("nome")
                .values_list("nome", flat=True)
                .distinct()
            )
            self.saved_name_choices = [name for name in names if name]

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

    def clean_nome(self):
        value = " ".join(self.cleaned_data["nome"].split())
        if not value:
            raise forms.ValidationError("Informe um nome para o gasto.")
        return value
