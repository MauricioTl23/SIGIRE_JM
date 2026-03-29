import random
import string
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.conf import settings  
from django.shortcuts import get_object_or_404
from .forms import RegistroPersonalForm
from .models import User
from .decorators import only_director, only_administrative
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .forms import CustomPasswordChangeForm

# 1. Vista Pública
def home(request):
    return render(request, 'Registration/home.html') 

# 2. Vista de Login
def login_view(request):
    return render(request, 'Registration/login.html')

# 3. Dashboard Unificado (RF1)
@login_required
@only_administrative
def dashboard(request):
    return render(request, 'Registration/dashboard.html')

# 4. Listado de Personal (RF1 - Solo Director)
@login_required
@only_director
def list_personal(request):

    personal = User.objects.filter(is_active=True)
    
    return render(request, 'Registration/list_personal.html', {
        'personal': personal
    })

# 5. Registro de Personal (RF1 - Solo Director)
@login_required
@only_director
def registrar_personal(request):
    if request.method == 'POST':
        form = RegistroPersonalForm(request.POST)
        if form.is_valid():
            nuevo_usuario = form.save(commit=False)

            nombre_raw = nuevo_usuario.first_name.split()[0] if nuevo_usuario.first_name else "User"
            nombre = nombre_raw.capitalize() 
            
            apellidos = nuevo_usuario.last_name.split() if nuevo_usuario.last_name else ["X"]
            iniciales = "".join([a[0].upper() for a in apellidos])
            
            def generar_propuesta():
                digitos = "".join(random.choices(string.digits, k=3))
                return f"{nombre}{iniciales}{digitos}"

            username_final = generar_propuesta()
            
            while User.objects.filter(username=username_final).exists():
                username_final = generar_propuesta()
            
            nuevo_usuario.username = username_final
            
            # --- GENERACIÓN DE PASSWORD TEMPORAL ---
            password_temporal = get_random_string(length=10)
            nuevo_usuario.set_password(password_temporal)
            
            # Guardamos el usuario
            nuevo_usuario.save()
            
            # --- ENVÍO DE CREDENCIALES ---
            asunto = 'Bienvenido al Sistema - UE Jesús María'
            mensaje = (
                f"Hola {nuevo_usuario.first_name},\n\n"
                f"Tu cuenta administrativa ha sido creada.\n"
                f"Usuario: {username_final}\n"
                f"Contraseña temporal: {password_temporal}\n\n"
                f"Por seguridad, cambia tu contraseña al ingresar por primera vez."
            )
            
            try:
                # Usamos settings.DEFAULT_FROM_EMAIL para que use tu Gmail personal configurado
                send_mail(
                    asunto, 
                    mensaje, 
                    settings.DEFAULT_FROM_EMAIL, 
                    [nuevo_usuario.email],
                    fail_silently=False,
                )
                messages.success(request, f"Personal registrado. Credenciales enviadas a {nuevo_usuario.email}")
            except Exception as e:
                
                print(f"DEBUG: Error al enviar correo: {e}")
                messages.warning(request, f"Usuario creado ({username_final}), pero falló el envío del correo. Revise la consola.")

            return redirect('list_personal')
    else:
        form = RegistroPersonalForm()
    return render(request, 'Registration/form_personal.html', {'form': form})


@login_required
@only_director
def editar_personal(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        
        form = RegistroPersonalForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos de {usuario.get_full_name()} actualizados.")
            return redirect('list_personal')
    else:
        form = RegistroPersonalForm(instance=usuario)
    return render(request, 'Registration/form_personal.html', {
        'form': form, 
        'edit_mode': True,
        'usuario': usuario
    })

@login_required
@only_director
def eliminar_personal(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    # Evitar que el director se borre a sí mismo
    if usuario == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta.")
    else:
        # Borrado lógico: lo desactivamos en lugar de borrarlo de la BD
        usuario.is_active = False
        usuario.save()
        messages.warning(request, f"El usuario {usuario.username} ha sido desactivado.")
    
    return redirect('list_personal')

class UserPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'Registration/change_password.html'
    success_url = reverse_lazy('dashboard') # A donde va después de cambiarla

    def form_valid(self, form):
        messages.success(self.request, "¡Tu contraseña ha sido actualizada con éxito!")
        return super().form_valid(form)