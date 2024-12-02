# utils.py
import chess
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Mapping of chess pieces to their corresponding HTML Unicode symbols
piece_to_html = {
    'K': '&#9812;',  # White King
    'Q': '&#9813;',  # White Queen
    'R': '&#9814;',  # White Rook
    'B': '&#9815;',  # White Bishop
    'N': '&#9816;',  # White Knight
    'P': '&#9817;',  # White Pawn
    'k': '&#9818;',  # Black King
    'q': '&#9819;',  # Black Queen
    'r': '&#9820;',  # Black Rook
    'b': '&#9821;',  # Black Bishop
    'n': '&#9822;',  # Black Knight
    'p': '&#9823;',  # Black Pawn
}

def board_to_dict(fen):
    """
    Converts a FEN string into a list of dictionaries representing each row of the chessboard.
    Each cell contains the HTML Unicode symbol for the piece or a non-breaking space if empty.
    """
    board = chess.Board(fen)
    board_dict = []
    for rank in reversed(range(1, 9)):
        row = {}
        for file in range(8):
            square_index = chess.square(file, rank - 1)
            square_name = chess.square_name(square_index)
            piece = board.piece_at(square_index)
            if piece:
                row[square_name] = piece_to_html.get(piece.symbol(), piece.symbol())
            else:
                row[square_name] = "&nbsp;"
        board_dict.append(row)
    return board_dict

def apply_move_to_board(fen, move):
    """
    Applies a move to the board represented by the FEN string.
    Returns the updated FEN string after the move is applied.
    Raises ValueError if the move is invalid.
    """
    try:
        board = chess.Board(fen)
        chess_move = chess.Move.from_uci(move)
        if chess_move in board.legal_moves:
            board.push(chess_move)
            return board.fen()
        else:
            raise ValueError("Invalid move.")
    except Exception as e:
        logger.exception("Exception in apply_move_to_board: %s", e)
        raise ValueError("Invalid move.")
