"""
URL configuration for chess_game project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from chess_app import views as view1_app
from journal import views as journal_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('',view1_app.home,name="home"),
    path('home/',view1_app.home),
    path('rules/',view1_app.rules),
    path('history/',view1_app.history),
    path('about/',view1_app.about),
    path('join/', view1_app.join),
    path('login/', view1_app.user_login),
    path('logout/', view1_app.user_logout),
    path('journal/', journal_views.journal),
    path('journal/add/', journal_views.add),
    path('journal/edit/<int:id>/', journal_views.edit),
    path('play/<int:game_id>/', view1_app.play_game, name='play_game'),
    # path('game_res/<int:game_id>/', view1_app.game_result, name='game_result'),
    path('game_result/<int:game_id>/', view1_app.game_result, name='game_res'),
    path('game/result/<int:game_id>/', view1_app.game_result, name='game_result'),
    path('edit-journal/<int:game_id>/', view1_app.edit_journal, name='edit_journal'),
    path('delete_game/<int:game_id>/', view1_app.delete_game, name='delete_game'),

    # path('poll_available_users/', view1_app.poll_available_users, name='poll_available_users'),
    # path('poll_game_status/<int:game_id>/', view1_app.poll_game_status, name='poll_game_status'),
    path('check_for_game/', view1_app.check_for_game, name='check_for_game'),

    path('send_challenge/<int:user_id>/', view1_app.send_challenge, name='send_challenge'),
    path('handle_challenge/<int:user_id>/<str:action>/', view1_app.handle_challenge, name='handle_challenge'),
]