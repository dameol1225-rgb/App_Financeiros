from django import forms

from gastos.models import Categoria, Gasto, GastoDebito
from gastos.services import normalize_expense_name


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
        self.fields["nome"].help_text = "Escolha um cartão já salvo no menu abaixo ou digite um novo nome."
        self.saved_name_choices = []

        if profile:
            seen_names = set()
            ordered_names = profile.gastos.order_by("nome").values_list("nome", flat=True)
            for name in ordered_names:
                normalized_name = normalize_expense_name(name)
                if not name or normalized_name in seen_names:
                    continue
                seen_names.add(normalized_name)
                self.saved_name_choices.append(name)

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
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Cartão Nubank"}),
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


class GastoDebitoForm(forms.ModelForm):
    class Meta:
        model = GastoDebito
        fields = (
            "valor",
            "data",
            "observacao",
        )
        widgets = {
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "data": forms.DateInput(attrs={"type": "date"}),
            "observacao": forms.TextInput(
                attrs={"placeholder": "Observação opcional da compra no débito"}
            ),
        }
        labels = {
            "valor": "Valor",
            "data": "Data da compra",
            "observacao": "Observação",
        }

    def clean_valor(self):
        value = self.cleaned_data["valor"]
        if value <= 0:
            raise forms.ValidationError("Informe um valor maior que zero.")
        return value

    def clean_observacao(self):
        value = " ".join(self.cleaned_data.get("observacao", "").split())
        return value
