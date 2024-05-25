import unittest
import chess
import chess.pgn
import chess.engine
from io import StringIO
from typing import List, Tuple
from chess_blunder_anki import read_pgn_file, extract_pgn_metadata, analyze_game, get_centipawn_score, get_score_str

class TestChessblunderAnki(unittest.TestCase):

    def setUp(self):
        self.engine_path = "/usr/games/stockfish"  # Adjust if necessary
        self.pgn_data = """[Event "Example"]
[Site "Example"]
[Date "2024.01.27"]
[Round "1"]
[White "PlayerA"]
[Black "PlayerB"]
[Result "1-0"]
[WhiteTitle "GM"]
[BlackTitle "GM"]
[WhiteElo "2000"]
[BlackElo "2100"]
[ECO "A00"]
[Opening "Opening"]
[WhiteFideId "11111111"]
[BlackFideId "22222222"]
[EventDate "2024.01.13"]

1. Nc3 Nf6 2. d4 d5 3. Bf4 c5 4. e3 cxd4 5. exd4 a6 6. Nf3 Bg4 7. h3 Bxf3 8.
Qxf3 Nc6 9. O-O-O e6 10. g4 Bd6 11. Be3 Qa5 12. Kb1 Nb4 13. Bc1 Rc8 14. a3 Nc6
15. g5 Nd7 16. h4 Qb6 17. Bh3 Nxd4 18. Qe3 Be5 19. f4 Rxc3 20. Qxc3 Nb5 21. Qf3
Bd4 22. Ka2 g6 23. h5 Nc5 24. Bf1 Ne4 25. Bxb5+ axb5 26. hxg6 fxg6 27. Rhe1 Rf8
28. Qd3 1-0
        """

        self.pgn_game = chess.pgn.read_game(StringIO(self.pgn_data))

    def test_read_pgn_file(self):
        with open('test.pgn', 'w') as f:
            f.write(self.pgn_data)
        games = read_pgn_file('test.pgn')
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0].headers["Event"], "Example")

    def test_extract_pgn_metadata(self):
        metadata = extract_pgn_metadata(self.pgn_game)        
        self.assertEqual(metadata["White"], "PlayerA")
        self.assertEqual(metadata["Black"], "PlayerB")
        self.assertEqual(metadata["WhiteElo"], "2000")
        self.assertEqual(metadata["BlackElo"], "2100")

    def test_analyze_game(self):
        blunders = analyze_game(self.pgn_game, self.engine_path, "white", blunder_threshold=200, engine_time=0.1)
        self.assertIsInstance(blunders, List)
        self.assertTrue(all(isinstance(blunder, Tuple) for blunder in blunders))

    def test_get_centipawn_score(self):
        board = chess.Board()
        score = chess.engine.PovScore(chess.engine.Cp(34), chess.WHITE)
        centipawn_score = get_centipawn_score(score, board)
        self.assertEqual(centipawn_score, 34)
        

    def test_get_score_str(self):
        board = chess.Board()
        score = chess.engine.PovScore(chess.engine.Cp(34), chess.WHITE)
        score_str = get_score_str(score, board)
        self.assertEqual(score_str, "0.34")

        score = chess.engine.PovScore(chess.engine.Mate(3), chess.WHITE)
        score_str = get_score_str(score, board)
        self.assertEqual(score_str, "Mate in 3 for White")
      

if __name__ == '__main__':
    unittest.main()