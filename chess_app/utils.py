import chess

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
    board = chess.Board(fen)
    board_dict = []
    for rank in reversed(range(1, 9)): 
        row = {}
        for file in range(8):  
            square_name = chess.square_name(chess.square(file, rank - 1)) 
            piece = board.piece_at(chess.square(file, rank - 1))
            if piece:
                
                row[square_name] = piece_to_html.get(piece.symbol(), piece.symbol())
            else:
                row[square_name] = "&nbsp;"  
        board_dict.append(row)
    
    return board_dict

def apply_move_to_board(fen, src, dst):
    board = chess.Board(fen)
    move = chess.Move.from_uci(f"{src}{dst}")
    if move in board.legal_moves:
        board.push(move)
        return board.fen()  # Return the updated FEN string
    raise ValueError("Invalid move")
