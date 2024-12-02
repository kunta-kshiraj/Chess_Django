from django.db import models
from django.contrib.auth.models import User
import uuid
import chess
# from .models import Game  # Assuming Game is in the same models file

class ChessGame(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    fen = models.TextField(default=chess.Board().fen())  # Correct: Assigning the FEN string
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    def reset_game(self):
        """
        Resets the game to the starting position (initial FEN).
        """
        self.fen = chess.Board().fen()  # Reset to the starting position
        self.save()

    def make_move(self, move):
        """
        Make a move on the board. The move should be in UCI format.
        E.g., 'e2e4' represents moving the pawn from e2 to e4.
        """
        board = chess.Board(self.fen)
        try:
            chess_move = chess.Move.from_uci(move)
            if chess_move in board.legal_moves:
                board.push(chess_move)  # Apply the move
                self.fen = board.fen()  # Update the FEN after the move
                self.save()
                return True
        except ValueError:
            # Handle invalid UCI move
            return False
        return False


class Challenge(models.Model):
    challenger = models.ForeignKey(User, related_name='sent_challenges', on_delete=models.CASCADE)
    challenged = models.ForeignKey(User, related_name='received_challenges', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('finished', 'Finished')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # class Meta:
    #     unique_together = ('challenger', 'challenged', 'status')

    # def __str__(self):
    #     return f"Challenge from {self.challenger.username} to {self.challenged.username}"

    # def is_ongoing_or_pending(self):
    #     """
    #     Check if there is an ongoing game or pending challenge between these users.
    #     """
    #     return Game.objects.filter(
    #         (models.Q(player1=self.challenger) & models.Q(player2=self.challenged)) |
    #         (models.Q(player1=self.challenged) & models.Q(player2=self.challenger)),
    #         status__in=['ongoing', 'pending']
    #     ).exists()


class Game(models.Model):
    player1 = models.ForeignKey(User, related_name='games_as_player1', on_delete=models.CASCADE)
    player2 = models.ForeignKey(User, related_name='games_as_player2', on_delete=models.CASCADE)
    board = models.OneToOneField(ChessGame, on_delete=models.CASCADE)  # Link to the Board model
    current_turn = models.ForeignKey(User, related_name='current_turn', on_delete=models.CASCADE)  # Track whose turn it is
    winner = models.ForeignKey(User, related_name='won_games', null=True, blank=True, on_delete=models.SET_NULL)  # Store the winner if the game is over
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Track the last time a move was made
    
    STATUS_CHOICES = (  # New status for when the game is created but hasn't started
        ('ongoing', 'Ongoing'),
        ('finished', 'Finished'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ongoing')  # Track game status
    move_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Game between {self.player1.username} and {self.player2.username}"


class JournalEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chess_journal_entries')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    datetime = models.DateField(auto_now=True)
    description = models.CharField(max_length=128)
    entry = models.CharField(max_length=65536)

    class Meta:
        unique_together = ('user', 'game')

    def __str__(self):
        return f"Journal entry for {self.game} by {self.user.username}"
    
class DeletedGame(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'game')

    def __str__(self):
        return f"Deleted game for {self.user.username} - Game ID {self.game.id}"


