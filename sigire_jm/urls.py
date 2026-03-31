from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views
from academic import views as academic_views
from students import views as students_views
from accounts.views import UserPasswordChangeView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('accounts/', include('django.contrib.auth.urls')),

    path('', accounts_views.home, name='home'),

    path('dashboard/', accounts_views.dashboard, name='dashboard'),

    path('personal/', accounts_views.list_personal, name='list_personal'),

    path('personal/nuevo/', accounts_views.registrar_personal, name='registrar_personal'),

    path('personal/editar/<str:pk>/', accounts_views.editar_personal, name='editar_personal'),

    path('personal/eliminar/<str:pk>/', accounts_views.eliminar_personal, name='eliminar_personal'),
    
    path('password-change/', UserPasswordChangeView.as_view(), name='password_change'),

    path('estructura/', academic_views.estructura_academica, name='estructura_academica'),

    path('gestion/toggle/<int:pk>/', academic_views.toggle_gestion, name='toggle_gestion'),
    
    path('gestion/nueva/', academic_views.crear_gestion, name='crear_gestion'),
    
    path('estructura/nivel-grado/nuevo/', academic_views.crear_nivel_grado, name='crear_nivel_grado'),
    
    path('nivel/editar/<int:pk>/', academic_views.editar_nivel, name='editar_nivel'),
    
    path('nivel/eliminar/<int:pk>/', academic_views.eliminar_nivel, name='eliminar_nivel'),
    
    path('grado/editar/<int:pk>/', academic_views.editar_grado, name='editar_grado'),
    
    path('grado/eliminar/<int:pk>/', academic_views.eliminar_grado, name='eliminar_grado'),
    
    path('paralelo/nuevo/', academic_views.crear_paralelo, name='crear_paralelo'),
    
    path('paralelo/eliminar/<int:pk>/', academic_views.eliminar_paralelo, name='eliminar_paralelo'),

    path('tutor/nuevo/', students_views.registrar_tutor, name='registrar_tutor'),

    path('tutores/', students_views.list_tutores, name='list_tutores'),
    
]