from django.urls import path

from . import views

urlpatterns = [
    path('csrf/', views.csrf, name='auth-csrf'),
    path('login/', views.login_view, name='auth-login'),
    path('logout/', views.logout_view, name='auth-logout'),
    path('me/', views.me, name='auth-me'),
    path('switchable-users/', views.switchable_users_view, name='auth-switchable-users'),
    path('switch-user/', views.switch_user_view, name='auth-switch-user'),
    path('switch-back/', views.switch_back_view, name='auth-switch-back'),
]
