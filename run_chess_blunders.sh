#!/bin/bash

# Default values
DEFAULT_PLAYER="white/black"
DEFAULT_ENGINE="/usr/games/stockfish"
DEFAULT_OUTPUT="anki_deck.apkg"
DEFAULT_BLUNDER_THRESHOLD=200
DEFAULT_ENGINE_TIME=0.2
DEFAULT_DECK_NAME="Chess Blunders"

# Check if PGN file argument is provided
if [ -z "$1" ]; then
  echo "Error: PGN file argument is mandatory."
  echo "Usage: ./run_chess_blunders.sh <pgn_file> [player] [engine] [output] [blunder_threshold] [engine_time] [deck_name]"
  exit 1
fi

PGN_FILE="$1"
PLAYER="${2:-$DEFAULT_PLAYER}"
ENGINE="${3:-$DEFAULT_ENGINE}"
OUTPUT="${4:-$DEFAULT_OUTPUT}"
BLUNDER_THRESHOLD="${5:-$DEFAULT_BLUNDER_THRESHOLD}"
ENGINE_TIME="${6:-$DEFAULT_ENGINE_TIME}"
DECK_NAME="${7:-$DEFAULT_DECK_NAME}"

# Step 1: Create a virtual environment
if [ ! -d "venv" ]; then
  python -m venv venv
fi

# Step 2: Activate the virtual environment
source venv/bin/activate

# Step 3: Install dependencies
pip install -r requirements.txt

# Step 4: Run the Python script with arguments
python chess_blunder_anki.py --pgn "$PGN_FILE" --player "$PLAYER" --engine "$ENGINE" --output "$OUTPUT" --blunder_threshold "$BLUNDER_THRESHOLD" --engine-time "$ENGINE_TIME" --deck-name "$DECK_NAME"

# Deactivate the virtual environment
deactivate
