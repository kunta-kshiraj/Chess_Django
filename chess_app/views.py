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

# Handle sending challenges to users
@csrf_exempt
@login_required(login_url='/login/')
def send_challenge(request, user_id):
    if request.method == "POST":
        challenged_user = User.objects.get(id=user_id)
        
        # Check if there is an ongoing game between the users
        existing_game = Game.objects.filter(
            (Q(player1=request.user, player2=challenged_user) | Q(player1=challenged_user, player2=request.user)),
            status='ongoing'  # Only look for ongoing games
        ).first()

        if existing_game:
            return JsonResponse({'status': 'error', 'error': "An ongoing game already exists between you and this user."})

        # Check if a pending challenge already exists between these users
        existing_challenge = Challenge.objects.filter(
            (Q(challenger=request.user, challenged=challenged_user) | Q(challenger=challenged_user, challenged=request.user)),
            status='pending'
        ).first()

        if existing_challenge:
            return JsonResponse({'status': 'error', 'error': "A pending challenge already exists between you and this user."})
        # If no ongoing game and no pending challenge, create a new challenge
        Challenge.objects.create(challenger=request.user, challenged=challenged_user)
        return JsonResponse({'status': 'success'})

        


@never_cache
@csrf_exempt
@login_required(login_url='/login/')
def home(request):
    # Check if there is any ongoing game
    try:
        # Check if the user is part of any ongoing game
        ongoing_game = Game.objects.filter(
            (Q(player1=request.user) | Q(player2=request.user)) & Q(winner__isnull=True)
        ).first()

        # If there's an ongoing game, redirect to the game view
        if ongoing_game:
            return redirect('play_game', game_id=ongoing_game.id)

    except Game.DoesNotExist:
        pass

    active_users = User.objects.filter(is_active=True).exclude(id=request.user.id)
    form = ChessForm()

    # Fetch pending challenges where the current user is being challenged
    received_challenges = Challenge.objects.filter(challenged=request.user, status='pending')

    sent_challenges = Challenge.objects.filter(challenger=request.user, status='pending')


    challengers_list = list(received_challenges.values_list('challenger_id', flat=True))
    challenged_user_ids = list(sent_challenges.values_list('challenged_id', flat=True))


    if request.method == 'POST':
        if 'challenge' in request.POST:
            opponent_id = request.POST.get('challenge')
            opponent = User.objects.get(id=opponent_id)

            # Check if a pending or ongoing challenge already exists between the two users
            existing_challenge = Challenge.objects.filter(
                challenger=request.user, challenged=opponent, status='pending'
            ).first()

            if existing_challenge:
                return HttpResponse("A pending challenge already exists between you and this user.", status=400)


            # Create a new challenge if no pending or ongoing challenge exists
            Challenge.objects.create(challenger=request.user, challenged=opponent, status='pending')
            messages.success(request, f"Challenge sent to {opponent.username}!")
            return redirect('home')

        elif 'accept' in request.POST or 'reject' in request.POST:
            challenge_id = request.POST.get('accept') or request.POST.get('reject')
            try:
                challenge = Challenge.objects.get(id=challenge_id)
            except Challenge.DoesNotExist:
                return HttpResponse("Challenge not found", status=404)
            if 'accept' in request.POST:
                if challenge.status == 'pending':
                    challenge.status = 'accepted'
                    challenge.save()

                    # Check if a game already exists between the players and if it is finished
                    # existing_game = Game.objects.filter(
                    #     Q(player1=challenge.challenger, player2=challenge.challenged) |
                    #     Q(player1=challenge.challenged, player2=challenge.challenger)
                    # ).exclude(status='finished').first()

                    # if existing_game:
                    #     messages.error(request, "An ongoing game already exists between you and this user.")
                    #     return redirect('home')

                    # Create a new chess game when the challenge is accepted
                    player_board = ChessGame.objects.create(
                        user=challenge.challenged,
                        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
                    )
                    game = Game.objects.create(
                        player1=challenge.challenger,
                        player2=challenge.challenged,
                        board=player_board,
                        current_turn=challenge.challenger,
                        # status='ongoing'  # Mark the game as ongoing
                    )
                    messages.success(request, "Game started!")
                    return redirect('play_game', game_id=game.id)

            elif 'reject' in request.POST:
                if challenge.status == 'pending':
                    challenge.status = 'declined'
                    challenge.save()
                    messages.info(request, "Challenge rejected.")
            return redirect('home')


    # Fetch completed games where the user is either player1 or player2
    # completed_games = Game.objects.filter(
    #     (Q(player1=request.user) | Q(player2=request.user)) & Q(status='finished')
    # ).order_by('-updated_at')

    # # Prefetch journal entries for the current user
    # completed_games = completed_games.prefetch_related(
    #     Prefetch(
    #         'journalentry_set',
    #         queryset=JournalEntry.objects.filter(user=request.user),
    #         to_attr='user_journal_entries'
    #     )
    # )

    # Fetch completed games where the user is either player1 or player2 and has not marked the game as deleted
    completed_games = Game.objects.filter(
        (Q(player1=request.user) | Q(player2=request.user)) & Q(status='finished')
    ).exclude(id__in=DeletedGame.objects.filter(user=request.user).values_list('game_id', flat=True)).order_by('-updated_at')

    # Prefetch journal entries for the current user
    completed_games = completed_games.prefetch_related(
        Prefetch(
            'journalentry_set',
            queryset=JournalEntry.objects.filter(user=request.user),
            to_attr='user_journal_entries'
        )
    )


    page_data = {
        "chess_form": form,
        "active_users": active_users,
        "challengers_list": challengers_list,
        "received_challenges": received_challenges,
        "challenged_user_ids": challenged_user_ids,  # Pass pending challenge user IDs
        "completed_games": completed_games,  # Pass the completed games to the template
    }

    return render(request, 'chess_app/home.html', page_data)

@csrf_exempt
@login_required(login_url='/login/')
def play_game(request, game_id):
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return HttpResponse("Game not found", status=404)

    # If the game is finished, redirect both players
    if game.status == 'finished':
        return redirect('game_result', game_id=game.id)

    # Check if the current user is one of the players
    if request.user not in [game.player1, game.player2]:
        return HttpResponse("You are not a player in this game", status=403)

    # Load the current board state
    chess_board = chess.Board(game.board.fen)

    # Determine if it's the current player's turn
    is_white = request.user == game.player1
    current_player = game.current_turn

    # Identify the player and the opponent
    player_color = "White" if is_white else "Black"
    opponent = game.player2 if request.user == game.player1 else game.player1
    opponent_color = "Black" if is_white else "White"

    if chess_board.is_checkmate():
        game.status = 'finished'
        game.winner = opponent if current_player == request.user else request.user
        game.save()
        return redirect('game_result', game_id=game.id)

    elif chess_board.is_stalemate():
        game.status = 'finished'
        game.winner = None  # No winner in a stalemate
        game.save()
        return redirect('game_result', game_id=game.id)

    if request.method == 'POST':
        if 'resign' in request.POST:
            # If the player resigns, set the opponent as the winner
            game.winner = game.player2 if request.user == game.player1 else game.player1
            game.status = 'finished'  # Mark the game as finished
            game.save()

            # Redirect both players to the result page
            return redirect('game_result', game_id=game.id)

        elif 'move' in request.POST:
            form = ChessForm(request.POST)
            if form.is_valid():
                move_position = form.cleaned_data.get('move_position')

                if not move_position or len(move_position) != 4:
                    form.add_error(None, "Move must consist of exactly 4 characters (e.g., 'e2e4').")
                else:
                    start_position = move_position[:2]  # Extract 'e2'
                    end_position = move_position[2:]    # Extract 'e4'
                    try:
                        move = chess.Move.from_uci(start_position + end_position)

                        # Ensure the move is legal and it's the player's turn
                        if move in chess_board.legal_moves:
                            # Check if the user is moving their own pieces
                            moving_piece = chess_board.piece_at(chess.SQUARE_NAMES.index(start_position))
                            if moving_piece is None:
                                form.add_error(None, "No piece at the start position.")
                            elif (moving_piece.color == chess.WHITE and not is_white) or (moving_piece.color == chess.BLACK and is_white):
                                form.add_error(None, "You can only move your own pieces.")
                            else:
                                # Apply the move
                                chess_board.push(move)
                                game.board.fen = chess_board.fen()  # Update the FEN after the move
                                game.board.save()
                                
                                game.move_count+=1
                                game.save()

                                # Switch the turn to the next player
                                game.current_turn = game.player1 if game.current_turn == game.player2 else game.player2
                                game.save()

                                return redirect('play_game', game_id=game.id)
                        else:
                            form.add_error(None, "Illegal move: The move is not allowed.")
                    except ValueError:
                        form.add_error(None, "Invalid move format. Use correct notation like 'e2e4'.")

    else:
        form = ChessForm()

    # Convert the board to a dictionary for rendering
    board_dict = board_to_dict(game.board.fen)

    return render(request, 'chess_app/game.html', {
        'chessboard': board_dict,
        'game': game,
        'form': form,
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
def join(request):
    if request.method == "POST":
        join_form = JoinForm(request.POST)
        if join_form.is_valid():
            user = join_form.save()
            user.set_password(user.password)
            user.save()
            messages.success(request, "Registration successful!")
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
def poll_available_users(request):
    active_users = User.objects.filter(is_active=True).exclude(id=request.user.id)
    users_data = []

    for user in active_users:
        # Check if there is a pending challenge between the logged-in user and this user
        if Challenge.objects.filter(challenger=request.user, challenged=user, status='pending').exists():
            has_challenge = 'sent'
        elif Challenge.objects.filter(challenger=user, challenged=request.user, status='pending').exists():
            has_challenge = 'received'
        else:
            has_challenge = None

        users_data.append({
            "id": user.id,
            "username": user.username,
            "has_challenge": has_challenge
        })

    return JsonResponse({'active_users': users_data})

@csrf_exempt
@login_required
def poll_game_status(request, game_id):
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)

    # Return the game state as a JSON response
    return JsonResponse({
        'status': game.status,
        'board': board_to_dict(game.board.fen),  # Update the board
        'current_turn': game.current_turn.username,
        'your_turn': (game.current_turn == request.user),
        'game_id': game.id
    })

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


@login_required(login_url='/login/')
@csrf_exempt
def handle_challenge(request, user_id, action):
    if request.method == "POST":
        try:
            if action not in ['accept', 'reject']:
                return JsonResponse({'status': 'error', 'error': 'Invalid action'}, status=400)

            challenge = Challenge.objects.get(challenger_id=user_id, challenged=request.user, status='pending')
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
                    current_turn=challenge.challenger,
                )
                return JsonResponse({'status': 'success', 'game_id': game.id})

            elif action == 'reject':
                challenge.status = 'declined'
                challenge.save()
                return JsonResponse({'status': 'success'})

        except Challenge.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': 'Challenge not found'}, status=404)