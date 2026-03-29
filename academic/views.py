from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import only_director 
from .models import Nivel, Grado, Gestion, Paralelo

@login_required
@only_director
def estructura_academica(request):

    gestiones = Gestion.objects.all().order_by('-año')
    
    niveles = Nivel.objects.all()
    grados = Grado.objects.all().select_related('nivel')
    paralelos = Paralelo.objects.all().select_related('grado__nivel')

    context = {
        'gestiones': gestiones,
        'niveles': niveles,
        'grados': grados,
        'paralelos': paralelos,
    }
    
    return render(request, 'Structure/structure_academic.html', context)

@login_required
@only_director
def toggle_gestion(request, pk):

    gestion = get_object_or_404(Gestion, pk=pk)
    
   
    if not gestion.estado:
        Gestion.objects.update(estado=False)
        gestion.estado = True
        messages.success(request, f"¡La Gestión {gestion.año} ahora es la gestión activa!")
    else:
        gestion.estado = False
        messages.warning(request, f"Se ha cerrado la Gestión {gestion.año}.")
        
    gestion.save()
    return redirect('estructura_academica')