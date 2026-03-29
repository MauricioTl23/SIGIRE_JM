from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views
from academic import views as academic_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('accounts/', include('django.contrib.auth.urls')),

    path('', accounts_views.home, name='home'),

    path('dashboard/', accounts_views.dashboard, name='dashboard'),

    path('personal/', accounts_views.list_personal, name='list_personal'),

    path('personal/nuevo/', accounts_views.registrar_personal, name='registrar_personal'),

    path('personal/editar/<str:pk>/', accounts_views.editar_personal, name='editar_personal'),

    path('personal/eliminar/<str:pk>/', accounts_views.eliminar_personal, name='eliminar_personal'),

    path('estructura/', academic_views.estructura_academica, name='estructura_academica'),

    path('gestion/toggle/<int:pk>/', academic_views.toggle_gestion, name='toggle_gestion'),
]