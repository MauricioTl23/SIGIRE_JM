from django.contrib import admin
from django.urls import path, include
from accounts import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('', views.home, name='home'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('personal/', views.list_personal, name='list_personal'),

    path('personal/nuevo/', views.registrar_personal, name='registrar_personal'),
    
    path('personal/editar/<str:pk>/', views.editar_personal, name='editar_personal'),
    
    path('personal/eliminar/<str:pk>/', views.eliminar_personal, name='eliminar_personal'),

]