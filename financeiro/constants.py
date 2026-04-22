from decimal import Decimal


APP_NAME = "Casal Organizado"
DEFAULT_THEME = "ocean"

DUE_DAY_CHOICES = (
    (5, "Dia 5"),
    (20, "Dia 20"),
    (30, "Dia 30"),
)

THEME_CHOICES = (
    ("ocean", "Ocean"),
    ("black", "Black"),
)

INSTALLMENT_FILTER_STATUS_CHOICES = (
    ("pendente", "Pendentes"),
    ("pago", "Pagas"),
    ("todos", "Todas"),
)

DEFAULT_PROFILES = (
    {
        "slug": "samuel-menezes",
        "nome": "Samuel Menezes",
        "ordem": 1,
        "dias_salario": (5, 20, 30),
    },
    {
        "slug": "grazi-xavier",
        "nome": "Grazi Xavier",
        "ordem": 2,
        "dias_salario": (5, 20),
    },
)

DEFAULT_SALARY_VALUE = Decimal("0.00")

DEFAULT_CATEGORIES = (
    ("Alimentacao", "#0f9bd7", "utensils"),
    ("Transporte", "#2563eb", "car"),
    ("Lazer", "#14b8a6", "gamepad-2"),
    ("Assinatura", "#38bdf8", "badge-dollar-sign"),
    ("Saude", "#22c55e", "heart-pulse"),
    ("Educacao", "#0ea5e9", "graduation-cap"),
    ("Casa", "#1d4ed8", "house"),
    ("Outros", "#94a3b8", "wallet"),
)

CATEGORY_PALETTE = [
    "#0f9bd7",
    "#2563eb",
    "#14b8a6",
    "#38bdf8",
    "#22c55e",
    "#0ea5e9",
    "#1d4ed8",
    "#94a3b8",
]

