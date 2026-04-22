from functools import wraps

from django.shortcuts import redirect

from perfis.services import get_active_profile


def active_profile_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not get_active_profile(request):
            return redirect("select_profile")

        return view_func(request, *args, **kwargs)

    return wrapped_view
