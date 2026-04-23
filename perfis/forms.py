from django import forms
from django.contrib.auth.forms import AuthenticationForm

from perfis.models import RendaExtra


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Login",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
            }
        ),
    )


class ProfileImageForm(forms.Form):
    image = forms.ImageField(label="Imagem de perfil")

    def clean_image(self):
        image = self.cleaned_data["image"]
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("A imagem precisa ter no maximo 5 MB.")
        return image


class SalaryUpdateForm(forms.Form):
    def __init__(self, *args, profile, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.salary_items = list(profile.parcelas_salariais.all())
        for item in self.salary_items:
            self.fields[f"valor_{item.id}"] = forms.DecimalField(
                label=f"Recebimento dia {item.dia_recebimento}",
                max_digits=10,
                decimal_places=2,
                min_value=0,
                initial=item.valor,
                widget=forms.NumberInput(
                    attrs={
                        "step": "0.01",
                        "min": "0",
                    }
                ),
            )

    def save(self):
        for item in self.salary_items:
            item.valor = self.cleaned_data[f"valor_{item.id}"]
            item.save(update_fields=["valor"])


class RendaExtraForm(forms.ModelForm):
    class Meta:
        model = RendaExtra
        fields = ("descricao", "valor", "data")
        widgets = {
            "descricao": forms.TextInput(attrs={"placeholder": "Freelance, venda, bonus..."}),
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "data": forms.DateInput(attrs={"type": "date"}),
        }
