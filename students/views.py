from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Tutor
from .forms import TutorForm

@login_required
def registrar_tutor(request):
    if request.method == 'POST':
        form = TutorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tutor registrado correctamente.")
            return redirect('list_tutores')
    else:
        form = TutorForm()
    
    return render(request, 'Tutor/form_tutor.html', {'form': form})

@login_required
def list_tutores(request):
    tutores = Tutor.objects.all().order_by('apellidos')
    return render(request, 'Tutor/list_tutores.html', {'tutores': tutores})