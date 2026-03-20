from django.shortcuts import redirect


def tylko_pacjentka(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_staff:
            return redirect('panel_lekarza')
        return view_func(request, *args, **kwargs)
    return wrapper


def tylko_lekarz(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper