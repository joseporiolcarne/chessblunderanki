import argparse
import chess
import chess.pgn
import chess.engine
import os
import sys
from typing import List, Tuple
import genanki
import random

def read_pgn_file(file_path: str) -> List[chess.pgn.Game]:
    """
    Reads a PGN file and returns a list of chess.pgn.Game objects.
    """
    games = []
    with open(file_path, 'r') as file:
        while True:
            game = chess.pgn.read_game(file)
            if game is None:
                break
            games.append(game)
    return games

def extract_pgn_metadata(game: chess.pgn.Game) -> dict:
    """
    Extracts metadata from a PGN game header.
    """
    headers = game.headers
    return {
        "Event": headers.get("Event", ""),
        "Site": headers.get("Site", ""),
        "Date": headers.get("Date", ""),
        "White": headers.get("White", ""),
        "Black": headers.get("Black", ""),
        "Result": headers.get("Result", ""),
        "UTCDate": headers.get("UTCDate", ""),
        "UTCTime": headers.get("UTCTime", ""),
        "WhiteElo": headers.get("WhiteElo", ""),
        "BlackElo": headers.get("BlackElo", ""),
        "WhiteRatingDiff": headers.get("WhiteRatingDiff", ""),
        "BlackRatingDiff": headers.get("BlackRatingDiff", ""),
        "Variant": headers.get("Variant", ""),
        "TimeControl": headers.get("TimeControl", ""),
        "ECO": headers.get("ECO", ""),
        "Termination": headers.get("Termination", "")
    }

def analyze_game(game: chess.pgn.Game, engine_path: str, player_filter: str, blunder_threshold: int = 200, engine_time: int = 0.1) -> List[Tuple[int, float]]:
    """
    Analyzes a game to find blunders using a chess engine.
    Returns a list of tuples containing the move index and the score difference.
    Filters blunders based on player perspective or specific player name.
    """
    board = game.board()
    blunders = []
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        for i, move in enumerate(game.mainline_moves()):
            
            moving_side = "White" if board.turn == chess.WHITE else "Black"
            num_move = (i // 2) + 1
            
            print(f"Board state before move {num_move}:")
            print(board)            
            print(f"Analyzing move {move.uci()} at index {i} for {moving_side}")
            
            # Analyze the current position to get the score of the best move
            info = engine.analyse(board, chess.engine.Limit(time=engine_time))
            best_move = info["pv"][0] if "pv" in info else None           
            best_move_score = get_centipawn_score(info['score'], board)

            
            if best_move is None or best_move_score is None:
                board.push(move)
                continue

            # Make the player's move
            board.push(move)
            
            # Analyze the new position to get the score after the player's move
            info_after_move = engine.analyse(board, chess.engine.Limit(time=engine_time))
            # player_move_score = info_after_move['score'].relative.score(mate_score=10000) if info_after_move['score'] else None
            player_move_score = get_centipawn_score(info_after_move['score'], board)
           
            print(f"Best move score: {get_score_str(info['score'], board)} Player move score: {get_score_str(info_after_move['score'], board)}")
                                                          
            if player_move_score is None:
                continue
            
            # Calculate the score difference based on who is to move
            # After the player's move, board.turn will be the opposite of the player who made the move
            score_difference = player_move_score - best_move_score  if board.turn == chess.BLACK else best_move_score - player_move_score

            print(f"Score difference in centipawns: {score_difference}")
            
            # Determine if it's a blunder
            if score_difference <= -1*blunder_threshold:
                
                print(f"Blunder detected at move {(i // 2) + 1} with score difference {score_difference}")

                # Filter based on maximum score
                if player_move_score < -2500:
                    print(f"Score too low {player_move_score}, skipping blunder")
                    continue

                if player_move_score > 2500 :
                    print(f"Score too high {player_move_score}, skipping blunder")
                    continue
                

                if player_filter.lower() == "white" and board.turn == chess.BLACK:                    
                    blunders.append((i, score_difference))
                elif player_filter.lower() == "black" and board.turn == chess.WHITE:                    
                    blunders.append((i, score_difference))
                elif player_filter.lower() == "white/black":
                    blunders.append((i, score_difference))
                elif player_filter.lower() == "winner" and ((score_difference < 0 and game.headers["Result"] == "0-1") or (score_difference > 0 and game.headers["Result"] == "1-0")):
                    blunders.append((i, score_difference))
                elif player_filter.lower() == "loser" and ((score_difference > 0 and game.headers["Result"] == "0-1") or (score_difference < 0 and game.headers["Result"] == "1-0")):
                    blunders.append((i, score_difference))
                elif player_filter.lower() == game.headers["White"].lower() or player_filter.lower() == game.headers["Black"].lower():
                    blunders.append((i, score_difference))
                    
    return blunders


def get_next_best_moves(board: chess.Board, engine: chess.engine.SimpleEngine, depth: int = 20, num_moves: int = 5) -> str:
    """
    Analyzes the given board state with the provided engine and returns the next best moves in PGN notation.
    Ensure only legal moves are converted to SAN.
    """
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    top_moves = info.get("pv", [])[:num_moves]  # Get the principal variation moves

    moves_san = []
    move_number = board.fullmove_number  # Get the current move number

    for move in top_moves:
        if move in board.legal_moves:
            moves_san.append(f"{move_number}. {board.san(move)}")
            board.push(move)
            move_number += 1
        else:
            print(f"Warning: Engine recommended an illegal move: {move.uci()} for the board state:\n{board.fen()}")
    
    return ' '.join(moves_san)


def generate_anki_cards(blunders: List[Tuple[int, float]], game: chess.pgn.Game, engine_path: str, deck: genanki.Deck):
    """
    Generates Anki cards based on the identified blunders in a game and adds them to an Anki deck.
    """
    metadata = extract_pgn_metadata(game)
    mainline_moves = list(game.mainline_moves())
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        for i, _ in blunders:
            new_board = game.board()
            for m in mainline_moves[:i]:
                new_board.push(m)        

            position_pgn = game.board().variation_san(mainline_moves[:i])
            continuation_pgn = game.board().variation_san(mainline_moves)
            continuation_pgn = continuation_pgn[len(position_pgn):].strip()
            next_best_moves = get_next_best_moves(new_board, engine)

            puzzleid = f"{metadata['Date']} - {metadata['White']} vs {metadata['Black']} "

            note_id = random.randrange(1 << 30, 1 << 31)
          
            note = genanki.Note(
                model=genanki.Model(
                    note_id,
                    'Chess Blunder Model',
                    fields=[
                        {'name': 'PuzzleID'},
                        {'name': 'PGN'},
                        {'name': 'PGNContinuation'},
                        {'name': 'Moves'},
                        {'name': 'White'},
                        {'name': 'Black'},
                        {'name': 'Result'},
                        {'name': 'Date'},
                        {'name': 'Site'},
                        {'name': 'Event'},
                        {'name': 'WhiteElo'},
                        {'name': 'BlackElo'},
                        {'name': 'WhiteRatingDiff'},
                        {'name': 'BlackRatingDiff'},
                        {'name': 'Variant'},
                        {'name': 'TimeControl'},
                        {'name': 'ECO'},
                        {'name': 'Termination'},
                        
                    ],
                    templates=[
                        {
                            'name': 'Chess Blunder Card',
                            'qfmt': """<h1>{{PuzzleID}}</h1>

<div class="ifra" style="height: 100vw; padding-bottom: 50px; overflow: hidden">
<iframe id="iframe" src="https://lichess.org/analysis" allowtransparency="true" frameborder="0" scrolling="no" style="position: relative; top: -60px"></iframe>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
<script>
function createURL() {
    const pgn = '{{PGN}}'.toString(); // Replace {{PGN}} with your PGN string

 const chess = new Chess(); // Create a new chess instance
    chess.load_pgn(pgn); // Load the PGN into the chess instance
    const fen = chess.fen(); // Get the FEN string for the current position
	const fenurl = fen.replaceAll(' ', '%20');
    const lichessurl = "https://lichess.org/analysis/";
    document.getElementById("iframe").src = lichessurl.concat(fenurl);
}

createURL()
</script>""",
                            'afmt': """<h1>{{PuzzleID}} - Best next moves {{Moves}}</h1>
<h2>Game continuation...  {{PGNContinuation}}</h2>                            

<div class="ifr" style="height: 1800px; overflow: hidden">
<iframe id="iframe" src="https://lichess.org/analysis" allowtransparency="true" frameborder="0" scrolling="no" style="position: relative; top: -60px"></iframe>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
<script>
function createURL() {
    const pgn = '{{PGN}}'.toString(); // Full game PGN including moves
		const chess = new Chess(); // Create a new chess instance
    chess.load_pgn(pgn); // Load the PGN into the chess instance
    const fen = chess.fen(); // Get the FEN string for the current position
    const fenurl = fen.replaceAll(' ', '%20');
    const lichessurl = "https://lichess.org/analysis/";
    document.getElementById("iframe").src = lichessurl.concat(fenurl);
}

createURL()
</script>"""
                        }
                    ],
                    css="""
                    .card {
                        margin: 0px;
                        font-size: 32px;
                        font-size: 8.1vw;
                        text-align: center;
                        color: black;
                    }
                    .ifr iframe {
                        width: 100%;
                        max-width: 600px;
                        height: 1800px;
                    }
                    .ifra iframe {
                        width: 100%;
                        max-width: 600px;
                        max-height: 725px;
                        height: 1800px;
                    }
                    h1 {
                        font-size: 14px;
                    }
                    h2 {
                        font-size: 10px;
                    }"""
                ),
                fields=[puzzleid, position_pgn, continuation_pgn, next_best_moves, metadata["White"], metadata["Black"], metadata["Result"], metadata["Date"], metadata["Site"], metadata["Event"], metadata["WhiteElo"], metadata["BlackElo"], metadata["WhiteRatingDiff"], metadata["BlackRatingDiff"], metadata["Variant"], metadata["TimeControl"], metadata["ECO"], metadata["Termination"]]
            )
            deck.add_note(note)

def get_centipawn_score(score, board) -> float:
    """
    Converts the engine's score to centipawn format.
    """
    if score.is_mate():
        mate_in = score.relative.score(mate_score=10000)
        if mate_in > 0:
            return 10000 - (mate_in * 100)  
        else:
            return -10000 + (mate_in * 100)  
    else:
        cp_score = score.relative.score(mate_score=10000)
        return cp_score if board.turn else -cp_score  # Centi pawn score



def get_score_str(score, board):
    """
    Converts the engine's score to a human-readable format. Lichess format is used.
    """
    if score.is_mate():
        if score.relative.mate() > 0:
            mating_side = "White" if board.turn else "Black"
        else:
            mating_side = "Black" if board.turn else "White"
        return "Mate in " + str(abs(score.relative.mate())) + " for " + mating_side
    else:
        return str(score.white().score() / 100.0)
           

def main():
    parser = argparse.ArgumentParser(description='Analyze chess games and generate Anki cards for blunders.')
    parser.add_argument('--engine', type=str, default='/usr/games/stockfish', help='Path to the chess engine executable')
    parser.add_argument('--pgn', type=str, default='sample.pgn', help='Path to the PGN file containing the games')
    parser.add_argument('--player', type=str, default='white/black', help='Player filter (white, black, winner, loser, or specific player name)')
    parser.add_argument('--output', type=str, help='Output file name for the Anki deck')
    parser.add_argument('--blunder_threshold', type=int, default=200, help='Threshold for a move to be considered a blunder. Default is 200 centipawns.')
    parser.add_argument('--engine-time', type=int, default=0.2, help='Time in seconds for the engine to analyze each move. Default is 0.2 seconds.')
    parser.add_argument('--deck-name', type=str, default='Chess Blunders', help='Name of the Anki deck')

    args = parser.parse_args()
    
    engine_path = args.engine
    pgn_file_path = args.pgn
    player_filter = args.player
    blunder_threshold = args.blunder_threshold
    engine_time = args.engine_time
    deck_name = args.deck_name


    # Validate input
    if not os.path.exists(engine_path):
        print("Error: Engine path does not exist.")
        sys.exit(1)

    if blunder_threshold < 0:
        print("Error: Blunder threshold cannot be negative.")
        sys.exit(1)

    if not os.path.exists(pgn_file_path):
        print("Error: PGN file does not exist.")
        sys.exit(1)   


    # Generate a random deck ID
    deck_id = random.randrange(1 << 30, 1 << 31)
    
    output_file = args.output if args.output else f'anki_deck_{deck_id}.apkg'

    games = read_pgn_file(pgn_file_path)

    # Setup Anki deck
    deck = genanki.Deck(
        deck_id,
        deck_name
    )

    for game in games:
        blunders = analyze_game(game, engine_path, player_filter, blunder_threshold, engine_time)
        generate_anki_cards(blunders, game, engine_path, deck)

    genanki.Package(deck).write_to_file(output_file)
    print(f"Anki deck saved to {output_file}")

if __name__ == "__main__":
    main()