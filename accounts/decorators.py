from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def only_director(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificamos si el usuario es Director
        if request.user.is_authenticated and request.user.rol == 'director':
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Acceso denegado. Esta sección es exclusiva para la Dirección.")
            return redirect('dashboard')
    return _wrapped_view

def only_administrative(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verifica si es Director o Secretaria
        if request.user.is_authenticated and request.user.rol in ['director', 'secretaria']:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')
    return _wrapped_view