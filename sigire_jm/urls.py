from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views
from academic import views as academic_views
from students import views as students_views
from enrollment import views as enrollment_views
from accounts.views import UserPasswordChangeView
from django.contrib.auth.views import LoginView, LogoutView
from accounts.forms import SecureAuthenticationForm

urlpatterns = [
    path('admin/', admin.site.urls),

    path(
        'login/',
        LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=SecureAuthenticationForm,
            redirect_authenticated_user=True
        ),
        name='login'
    ),

    path('logout/', LogoutView.as_view(), name='logout'),

    path('', accounts_views.home, name='home'),
    path('dashboard/', accounts_views.dashboard, name='dashboard'),

    path('personal/', accounts_views.list_personal, name='list_personal'),

    path('personal/nuevo/', accounts_views.registrar_personal, name='registrar_personal'),

    path('personal/editar/<str:pk>/', accounts_views.editar_personal, name='editar_personal'),

    path('personal/eliminar/<str:pk>/', accounts_views.eliminar_personal, name='eliminar_personal'),
    
    path('personal/reactivar/<str:pk>/', accounts_views.reactivar_personal, name='reactivar_personal'),

    path('personal/eliminar-definitivo/<str:pk>/', accounts_views.eliminar_personal_fisico, name='eliminar_personal_fisico'),

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
    
    path('tutores/editar/<str:pk>/', students_views.editar_tutor, name='editar_tutor'),
    
    path('tutores/eliminar/<str:pk>/', students_views.eliminar_tutor, name='eliminar_tutor'),

    path('crear-estudiante/', students_views.crear_estudiante, name='crear_estudiante'),
    
    path('estudiantes/', students_views.list_estudiantes, name='list_estudiantes'),
    
    path('desactivar/<str:pk>/', students_views.desactivar_estudiante, name='desactivar_estudiante'),
    
    path('reactivar/<str:pk>/', students_views.reactivar_estudiante, name='reactivar_estudiante'),
    
    path('eliminar-definitivo/<str:pk>/', students_views.eliminar_estudiante_fisico, name='eliminar_estudiante_fisico'),

    path('editar/<str:pk>/', students_views.editar_estudiante, name='editar_estudiante'),

    path('inscripciones/registrar/', enrollment_views.registrar_inscripcion_view, name='registrar_inscripcion_view'),

    path('inscripciones/lista/', enrollment_views.list_inscripciones, name='list_inscripciones'),
    
    path('requisitos/crear/', enrollment_views.crear_requisito, name='crear_requisito'),

    path('requisitos/eliminar/<int:pk>/', enrollment_views.eliminar_requisito, name='eliminar_requisito'),

    path('requisitos/editar/<int:pk>/', enrollment_views.editar_requisito, name='editar_requisito'),
    
    path('inscripciones/<int:pk>/detalle/', enrollment_views.detalle_inscripcion, name='detalle_inscripcion'),

    path('inscripciones/<int:pk>/documentos/', enrollment_views.completar_documentos, name='completar_documentos'),
    
    path('inscripciones/<int:pk>/imprimir/', enrollment_views.imprimir_inscripcion, name='imprimir_inscripcion'),

    path('reportes/', accounts_views.reportes, name='reportes'),

    path('reportes/curso/<int:paralelo_id>/estudiantes/', accounts_views.curso_estudiantes, name='curso_estudiantes'),

]
