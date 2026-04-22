from financeiro.constants import DEFAULT_THEME, THEME_CHOICES
from perfis.services import get_active_profile, get_cleanup_notice, list_profiles


def app_context(request):
    active_profile = None
    available_profiles = []
    cleanup_notice = None
    active_theme = DEFAULT_THEME

    if request.user.is_authenticated:
        available_profiles = list(list_profiles())
        active_profile = get_active_profile(request)
        if active_profile:
            cleanup_notice = get_cleanup_notice(active_profile)
            active_theme = active_profile.tema

    return {
        "app_name": "Casal Organizado",
        "available_profiles": available_profiles,
        "active_profile": active_profile,
        "cleanup_notice": cleanup_notice,
        "active_theme": active_theme,
        "theme_options": THEME_CHOICES,
    }
