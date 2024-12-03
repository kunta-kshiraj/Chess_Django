import chess
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import DeletedGame, Game, JournalEntry
from .forms import JournalForm 
from django.views.decorators.http import require_POST

from chess_app.forms import ChessForm, JoinForm, LoginForm, MoveForm
from .models import ChessGame, Challenge, Game
from .utils import board_to_dict, apply_move_to_board
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)



# Handle sending challenges to users
@csrf_exempt
@login_required
def send_challenge(request, user_id):
    """Handle sending a challenge to another user."""
    if request.method == "POST":
        try:
            logger.info(f"User {request.user.id} is sending a challenge to User {user_id}")
            challenged_user = User.objects.get(id=user_id)

            # Check for existing games or challenges
            if Game.objects.filter(
                Q(player1=request.user, player2=challenged_user) |
                Q(player1=challenged_user, player2=request.user),
                status='ongoing'
            ).exists():
                logger.error("An ongoing game already exists.")
                return JsonResponse({'status': 'error', 'error': "An ongoing game already exists."})

            if Challenge.objects.filter(
                Q(challenger=request.user, challenged=challenged_user) |
                Q(challenger=challenged_user, challenged=request.user),
                status='pending'
            ).exists():
                logger.error("A pending challenge already exists.")
                return JsonResponse({'status': 'error', 'error': "A pending challenge already exists."})

            # Create the challenge and send a WebSocket notification
            Challenge.objects.create(challenger=request.user, challenged=challenged_user, status='pending')
            logger.info(f"Challenge created between User {request.user.id} and User {user_id}")

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{challenged_user.id}",
                {
                    "type": "send_challenge_notification",
                    "data": {
                        "challenger_id": request.user.id,
                        "challenger_username": request.user.username,
                    },
                }
            )
            return JsonResponse({'status': 'success'})

        except User.DoesNotExist:
            logger.error(f"User {user_id} does not exist.")
            return JsonResponse({'status': 'error', 'error': "User does not exist."})

@login_required(login_url='/login/')
@csrf_exempt
def handle_challenge(request, user_id, action):
    """Handle accepting or rejecting a challenge."""
    if request.method == "POST":
        try:
            challenge = Challenge.objects.get(
                challenger_id=user_id,
                challenged=request.user,
                status='pending'
            )

            if action == 'accept':
                challenge.status = 'accepted'
                challenge.save()

                # Create the game
                player_board = ChessGame.objects.create(
                    user=request.user,
                    fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
                )
                game = Game.objects.create(
                    player1=challenge.challenger,
                    player2=challenge.challenged,
                    board=player_board,
                    current_turn=challenge.challenger
                )
                logger.info(f"Game {game.id} created between User {challenge.challenger.id} and User {challenge.challenged.id}")

                # Notify both users via WebSocket
                channel_layer = get_channel_layer()
                for user in [challenge.challenger, challenge.challenged]:
                    async_to_sync(channel_layer.group_send)(
                        f"user_{user.id}",
                        {
                            "type": "send_challenge_notification",
                            "data": {
                                "redirect": True,
                                "game_id": game.id,
                            },
                        }
                    )
                return JsonResponse({'status': 'success', 'game_id': game.id})

            elif action == 'reject':
                challenge.status = 'declined'
                challenge.save()

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{challenge.challenger.id}",
                    {
                        'type': 'send_challenge_notification',
                        'data': {
                            'type': 'challenge_rejected',
                            'challenged_id': request.user.id,
                            'challenged_username': request.user.username,
                        },
                    }
                )
                logger.info(f"Challenge between User {user_id} and User {request.user.id} was rejected.")
                return JsonResponse({'status': 'success'})

        except Challenge.DoesNotExist:
            logger.error(f"Challenge not found between User {user_id} and User {request.user.id}.")
            return JsonResponse({'status': 'error', 'error': "Challenge not found."})


@never_cache
@csrf_exempt
@login_required(login_url='/login/')
def home(request):
    try:
        # Check for ongoing games
        ongoing_game = Game.objects.filter(
            (Q(player1=request.user) | Q(player2=request.user)) & Q(status='ongoing')
        ).first()
        if ongoing_game:
            return redirect('play_game', game_id=ongoing_game.id)

    except Game.DoesNotExist:
        pass

    active_users = User.objects.filter(is_active=True).exclude(id=request.user.id)

    # Fetch pending challenges where the current user is being challenged
    received_challenges = Challenge.objects.filter(challenged=request.user, status='pending')

    # Fetch pending challenges sent by the current user
    sent_challenges = Challenge.objects.filter(challenger=request.user, status='pending')

    # Lists for template logic
    challengers_list = list(received_challenges.values_list('challenger_id', flat=True))
    challenged_user_ids = list(sent_challenges.values_list('challenged_id', flat=True))

    # Fetch completed games
    completed_games = Game.objects.filter(
        (Q(player1=request.user) | Q(player2=request.user)) & Q(status='finished')
    ).exclude(
        id__in=DeletedGame.objects.filter(user=request.user).values_list('game_id', flat=True)
    ).order_by('-updated_at')

    # Prefetch journal entries for the current user
    completed_games = completed_games.prefetch_related(
        Prefetch(
            'journalentry_set',
            queryset=JournalEntry.objects.filter(user=request.user),
            to_attr='user_journal_entries'
        )
    )

    return render(request, 'chess_app/home.html', {
        "active_users": active_users,
        "challengers_list": challengers_list,
        "challenged_user_ids": challenged_user_ids,
        "received_challenges": received_challenges,
        "completed_games": completed_games,
        "current_user_id": request.user.id,
    })
    
@csrf_exempt
@login_required(login_url='/login/')
def play_game(request, game_id):
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return HttpResponse("Game not found", status=404)

    if game.status == 'finished':
        return redirect('game_result', game_id=game.id)

    if request.user not in [game.player1, game.player2]:
        return HttpResponse("You are not a player in this game", status=403)

    is_white = request.user == game.player1
    current_player = game.current_turn
    player_color = "White" if is_white else "Black"
    opponent = game.player2 if request.user == game.player1 else game.player1

    return render(request, 'chess_app/game.html', {
        'game': game,
        'current_player': current_player,
        'is_current_turn': request.user == current_player,
        'player_color': player_color,
        'opponent': opponent,
    })



@csrf_exempt
@login_required(login_url='/login/')
def game_result(request, game_id):
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return HttpResponse("Game not found", status=404)

    # Determine the result message based on who the winner is
    if game.winner == request.user:
        message = "You won!"
    else:
        message = "You lost!"

    return render(request, 'chess_app/game_res.html', {
        'message': message,
        'game': game
    })

def newGame(request):
    board = ChessGame.objects.get(user=request.user)
    
    # Reset the board to the initial state
    board.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
    board.save()

    # Reset the turn to player 1 (white)
    game = Game.objects.filter(board=board).first()
    if game:
        game.current_turn = game.player1
        game.save()
    
    return redirect('home')

import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required(login_url='/login/')
@require_POST
def delete_game(request, game_id):
    logger.info(f"Delete game view called for game_id: {game_id} by user: {request.user.username}")
    try:
        # Ensure the user is either player1 or player2 for the game being deleted
        game = Game.objects.get(Q(player1=request.user) | Q(player2=request.user), id=game_id)
        
        # Check if the game has already been marked as deleted for this user
        deleted_game = DeletedGame.objects.filter(user=request.user, game=game).first()
        
        if not deleted_game:
            # Mark the game as deleted for the current user by creating a new DeletedGame entry
            DeletedGame.objects.create(user=request.user, game=game)
            messages.success(request, "Game deleted from your history successfully.")
        else:
            messages.warning(request, "This game has already been deleted from your history.")
        
        return redirect('home')

    except Game.DoesNotExist:
        return HttpResponse("Game not found", status=404)




@csrf_exempt
# Join view for new users
@csrf_exempt
def join(request):
    if request.method == "POST":
        join_form = JoinForm(request.POST)
        if join_form.is_valid():
            user = join_form.save(commit=False)
            user.set_password(join_form.cleaned_data['password'])  # Ensure password is hashed
            user.save()
            messages.success(request, "Registration successful!")
            login(request, user)  # Log the user in after registration

            # Broadcast the new user to all connected users
            channel_layer = get_channel_layer()
            try:
                async_to_sync(channel_layer.group_send)(
                    "all_users",
                    {
                        "type": "send_challenge_notification",
                        "data": {
                            "type": "new_user",
                            "user_id": user.id,
                            "username": user.username,
                        },
                    }
                )
                logger.info(f"Broadcasted new_user message for user {user.id}")
            except Exception as e:
                logger.error(f"Error broadcasting new_user message: {e}")

            return redirect("/")
        else:
            messages.error(request, "There were errors in the form.")
    else:
        join_form = JoinForm()

    return render(request, 'chess_app/join.html', {"join_form": join_form})


@csrf_exempt
# User login
def user_login(request):
    if request.method == 'POST':
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data["username"]
            password = login_form.cleaned_data["password"]
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.username}!")
                    return redirect("/")
                else:
                    messages.warning(request, "Your account is not active.")
            else:
                messages.error(request, "Invalid login credentials.")
    else:
        login_form = LoginForm()

    return render(request, 'chess_app/login.html', {"login_form": login_form})

@csrf_exempt
# User logout
@never_cache
def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('/')

@csrf_exempt
# Static views
def about(request):
    return render(request, 'chess_app/about.html')

@csrf_exempt
def rules(request):
    return render(request, 'chess_app/rules.html')

@csrf_exempt
def history(request):
    return render(request, 'chess_app/history.html')

@csrf_exempt
@login_required(login_url='/login/')
def edit_journal(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    # Check if the user is a player in this game
    if request.user not in [game.player1, game.player2]:
        return HttpResponse("You are not authorized to edit this journal entry.", status=403)

    # Get or create the journal entry for the current user and game
    journal_entry, created = JournalEntry.objects.get_or_create(game=game, user=request.user)

    if request.method == 'POST':
        form = JournalForm(request.POST, instance=journal_entry)
        if form.is_valid():
            journal = form.save(commit=False)
            journal.user = request.user
            journal.game = game
            journal.save()
            messages.success(request, "Journal updated successfully.")
            return redirect('home')
    else:
        form = JournalForm(instance=journal_entry)

    return render(request, 'chess_app/journal.html', {'form': form, 'game': game})



@csrf_exempt
@login_required
# def poll_available_users(request):
#     active_users = User.objects.filter(is_active=True).exclude(id=request.user.id)
#     users_data = []

#     for user in active_users:
#         # Check if there is a pending challenge between the logged-in user and this user
#         if Challenge.objects.filter(challenger=request.user, challenged=user, status='pending').exists():
#             has_challenge = 'sent'
#         elif Challenge.objects.filter(challenger=user, challenged=request.user, status='pending').exists():
#             has_challenge = 'received'
#         else:
#             has_challenge = None

#         users_data.append({
#             "id": user.id,
#             "username": user.username,
#             "has_challenge": has_challenge
#         })

#     return JsonResponse({'active_users': users_data})

# @csrf_exempt
# @login_required
# def poll_game_status(request, game_id):
#     try:
#         game = Game.objects.get(id=game_id)
#     except Game.DoesNotExist:
#         return JsonResponse({'error': 'Game not found'}, status=404)

#     # Return the game state as a JSON response
#     return JsonResponse({
#         'status': game.status,
#         'board': board_to_dict(game.board.fen),  # Update the board
#         'current_turn': game.current_turn.username,
#         'your_turn': (game.current_turn == request.user),
#         'game_id': game.id
#     })

@csrf_exempt
@login_required
def check_for_game(request):
    try:
        # Check if the user is part of any ongoing game
        game = Game.objects.filter(
            (Q(player1=request.user) | Q(player2=request.user)) & Q(status='ongoing')
        ).first()

        if game:
            return JsonResponse({'game_started': True, 'game_id': game.id})
        else:
            return JsonResponse({'game_started': False})
    except Game.DoesNotExist:
        return JsonResponse({'game_started': False})



# @login_required(login_url='/login/')
# @csrf_exempt
# @csrf_exempt
# @login_required
# def handle_challenge(request, user_id, action):
#     """Handle accepting or rejecting a challenge."""
#     if request.method == "POST":
#         try:
#             challenge = Challenge.objects.get(
#                 challenger_id=user_id, 
#                 challenged=request.user, 
#                 status='pending'
#             )

#             if action == 'accept':
#                 challenge.status = 'accepted'
#                 challenge.save()

#                 # Create the game
#                 player_board = ChessGame.objects.create(
#                     user=request.user,
#                     fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
#                 )
#                 game = Game.objects.create(
#                     player1=challenge.challenger,
#                     player2=challenge.challenged,
#                     board=player_board,
#                     current_turn=challenge.challenger
#                 )
#                 logger.info(f"Game {game.id} created between User {challenge.challenger.id} and User {challenge.challenged.id}")

#                 # Notify both users via WebSocket
#                 channel_layer = get_channel_layer()
#                 for user in [challenge.challenger, challenge.challenged]:
#                     async_to_sync(channel_layer.group_send)(
#                         f"user_{user.id}",
#                         {
#                             "type": "send_challenge_notification",
#                             "data": {
#                                 "redirect": True,
#                                 "game_id": game.id,
#                             },
#                         }
#                     )
#                 return JsonResponse({'status': 'success', 'game_id': game.id})

#             elif action == 'reject':
#                 challenge.status = 'declined'
#                 challenge.save()
#                 logger.info(f"Challenge between User {user_id} and User {request.user.id} was rejected.")
#                 return JsonResponse({'status': 'success'})

#         except Challenge.DoesNotExist:
#             logger.error(f"Challenge not found between User {user_id} and User {request.user.id}.")
#             return JsonResponse({'status': 'error', 'error': "Challenge not found."})