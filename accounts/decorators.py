from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def staff_required(view_func):
    """
    Like Django's login_required, but also requires request.user.is_staff.
    If the person is logged in but isn't staff, they get a clear flash
    message and are sent to the customer menu — not bounced back to the
    login page they're already past (which would just loop).
    """
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "You don't have access to that page.")
            return redirect("menu:list")
        return view_func(request, *args, **kwargs)
    return wrapped
