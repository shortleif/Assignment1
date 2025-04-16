"""
Pokémon Hangman Game - Flask Application

This module implements a Pokémon-themed Hangman game using Flask.
Players can guess Pokémon names with different difficulty levels.
"""

from flask import Flask, render_template, request, redirect, url_for, session
import random, os, requests
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.urandom(24)


def load_pokemon_names():
    """
    Load Pokémon names from a file.
    
    Returns:
        list: A list of Pokémon names. Returns a default list if file not found.
    """
    try:
        with open("static/pokemon.txt", "r") as f:
            pokemon_list = [line.strip() for line in f.readlines()]
        return pokemon_list
    except FileNotFoundError:
        return ["Pikachu", "Charmander", "Bulbasaur", "Squirtle"]


def get_pokemon_image(pokemon_name):
    """
    Get a Pokémon image from the PokéAPI or from local cache.
    
    Args:
        pokemon_name (str): The name of the Pokémon to fetch
        
    Returns:
        str: URL path to the Pokémon image or None if not found
    """
    try:
        formatted_name = pokemon_name.lower().strip()
        
        # Create cache directory if it doesn't exist
        cache_dir = Path("static/pokemon_images")
        cache_dir.mkdir(exist_ok=True)
        
        # Check if we have a cached image
        cache_file = cache_dir / f"{formatted_name}.png"
        
        if cache_file.exists():
            return f"/static/pokemon_images/{formatted_name}.png"
        
        # Special case for Nidoran
        api_formatted_name = formatted_name
        if formatted_name == "nidoran":
            # Randomly choose male or female
            gender = random.choice(["m", "f"])
            api_formatted_name = f"nidoran-{gender}"
            # We still save it as nidoran.png
        
        response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{api_formatted_name}")
        
        if response.status_code == 200:
            data = response.json()
            image_url = data['sprites']['other']['official-artwork']['front_default']
            
            img_response = requests.get(image_url, stream=True)
            if img_response.status_code == 200:
                with open(cache_file, 'wb') as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)
                
                return f"/static/pokemon_images/{formatted_name}.png"
            else:
                return image_url
        else:
            return None
    except Exception as e:
        print(f"Error fetching Pokémon image: {e}")
        return None


@app.route("/")
def home():
    """Render the home page."""
    return render_template("index.html")


@app.route("/hangman", methods=["GET", "POST"])
def hangman():
    """
    Main hangman game route that handles:
    - Starting a new game with selected difficulty
    - Processing letter guesses
    - Tracking game progress and statistics
    
    Returns:
        Rendered template for the appropriate game state
    """
    # Initialize session variables if they don't exist
    if "encountered_pokemon" not in session:
        session["encountered_pokemon"] = []  # Track all Pokémon that have been shown
    if "games_won" not in session:
        session["games_won"] = 0
    if "games_lost" not in session:
        session["games_lost"] = 0
    if "caught_pokemon" not in session:
        session["caught_pokemon"] = []  # Track successfully guessed Pokémon
    
    # Determine game difficulty and number of attempts
    difficulty = request.args.get('difficulty')
    if difficulty:
        # Check if a previously selected difficulty exists
        previous_difficulty = session.get("difficulty")
        if previous_difficulty and previous_difficulty != difficulty:
            # Reset stats when changing difficulty
            session["games_won"] = 0
            session["games_lost"] = 0
            session["encountered_pokemon"] = []
            # Keep caught_pokemon for collection purposes
        
        # Set the new difficultyq
        if difficulty == 'easy':
            attempts = 10
        elif difficulty == 'medium':
            attempts = 6
        elif difficulty == 'hard':
            attempts = 3
        elif difficulty == 'extreme':
            attempts = 1
        else:
            attempts = 6  # Default to medium
        
        session["difficulty"] = difficulty
    else:
        # Use existing difficulty or default to medium
        difficulty = session.get("difficulty", "medium")
        if difficulty == 'easy':
            attempts = 10
        elif difficulty == 'hard':
            attempts = 3
        elif difficulty == 'extreme':
            attempts = 1
        else:
            attempts = 6  # Medium
    
    # Handle game initialization with difficulty
    if request.method == "GET" and 'difficulty' in request.args:
        return _start_new_game(difficulty, attempts)
    
    # Show difficulty selection screen
    elif request.method == "GET":
        return render_template("difficulty.html", 
                              title="Pokémon Hangman",
                              games_won=session.get("games_won", 0),
                              games_lost=session.get("games_lost", 0))
    
    # Process the player's guess
    elif request.method == "POST":
        return _process_guess(difficulty, attempts)


def _start_new_game(difficulty, attempts):
    """
    Start a new hangman game with the specified difficulty.
    
    Args:
        difficulty (str): The difficulty level ('easy', 'medium', 'hard', or 'extreme')
        attempts (int): Number of attempts allowed based on difficulty
        
    Returns:
        Rendered template for a new game
    """
    # Check if there's an active game that hasn't been completed
    if (session.get("game_active", False) and 
        session.get("word") and 
        "_" in session.get("display_word", []) and 
        session.get("attempts_left", 0) > 0 and
        session.get("difficulty") == difficulty):
        
        # Continue with the existing game instead of starting a new one
        template_vars = _get_template_vars(difficulty)
        template_vars["game_active"] = True
        return render_template("hangman.html", **template_vars)
    
    # Otherwise start a new game
    pokemon_list = load_pokemon_names()
    
    # Filter out all previously encountered Pokémon
    available_pokemon = [p for p in pokemon_list if p not in session["encountered_pokemon"]]
    
    # If all Pokémon have been encountered, show completion screen
    if not available_pokemon:
        return render_template("completion.html", 
                              title="Pokémon Hangman - Complete!",
                              caught_pokemon=len(session.get("caught_pokemon", [])),
                              total_pokemon=len(pokemon_list),
                              games_won=session.get("games_won", 0),
                              games_lost=session.get("games_lost", 0))
    
    # Select a new Pokémon from the available ones
    pokemon = random.choice(available_pokemon)
    
    # Get the Pokémon image
    pokemon_image = get_pokemon_image(pokemon)
    
    # Add to encountered Pokémon list
    encountered_pokemon = session["encountered_pokemon"]
    encountered_pokemon.append(pokemon)
    session["encountered_pokemon"] = encountered_pokemon

    # Initialize game session variables
    session["word"] = pokemon
    session["guessed_letters"] = []
    session["attempts_left"] = attempts
    session["display_word"] = ["_" if char.isalpha() else char for char in pokemon]
    session["pokemon_image"] = pokemon_image
    session["game_active"] = True
    
    # Get template variables using helper function
    template_vars = _get_template_vars(difficulty)
    template_vars["game_active"] = True
    
    return render_template("hangman.html", **template_vars)


def _process_guess(difficulty, attempts):
    """
    Process the player's letter guess and update game state.
    
    Args:
        difficulty (str): Current game difficulty
        attempts (int): Maximum attempts for the current difficulty
        
    Returns:
        Rendered template with updated game state
    """
    guess = request.form["guess"].lower()
    word = session.get("word", "").lower()
    guessed_letters = session.get("guessed_letters", [])
    attempts_left = session.get("attempts_left", attempts)
    display_word = session.get("display_word", [])

    message = ""
    game_complete = False

    # Validate the guess
    if not guess.isalpha() or len(guess) != 1:
        message = "Please enter a single letter."
    elif guess in guessed_letters:
        message = f"You already guessed {guess}."
    else:
        # Process valid guess
        guessed_letters.append(guess)

        if guess in word:
            # Handle correct guess
            for i, letter in enumerate(word):
                if letter == guess:
                    # Capitalize first letter
                    if i == 0:
                        display_word[i] = letter.upper()
                    else:
                        display_word[i] = letter
            message = f"Correct! {guess} is in the name of the Pokémon."
        else:
            # Handle incorrect guess
            attempts_left -= 1
            message = f"Incorrect! {guess.upper()} is not in the name of the Pokémon. You have {attempts_left} attempts left."

    # Update session variables
    session["guessed_letters"] = guessed_letters
    session["attempts_left"] = attempts_left
    session["display_word"] = display_word

    # Check if player won
    if "_" not in display_word:
        capitalized_word = word.capitalize()
        message = f"Congratulations! You guessed the Pokémon: {capitalized_word}."
        session["games_won"] = session.get("games_won", 0) + 1
        game_complete = True
        session["game_active"] = False  # Mark game as inactive
        session["message"] = message
        
        # Add to caught Pokémon collection if not already caught
        if word.capitalize() not in session["caught_pokemon"]:
            session["caught_pokemon"].append(word.capitalize())

        return render_template("hangman.html",
                              **_get_template_vars(difficulty, game_complete=True, custom_word=word.capitalize()))
    
    # Check if player lost
    elif attempts_left <= 0:
        capitalized_word = word.capitalize()
        message = f"Game over! The Pokémon was: {capitalized_word}."
        session["games_lost"] = session.get("games_lost", 0) + 1
        game_complete = True
        session["game_active"] = False  # Mark game as inactive
        session["message"] = message
    
    # Return current game state
    session["message"] = message
    return render_template("hangman.html",
                          **_get_template_vars(difficulty, game_complete=game_complete))


def _get_template_vars(difficulty, game_complete=False, custom_word=None):
    """
    Get common template variables for rendering.
    
    Args:
        difficulty (str): Current difficulty level
        game_complete (bool): Whether the current game is complete
        custom_word (str): Optional custom word to display instead of session display_word
        
    Returns:
        dict: Common template variables for rendering
    """
    # Base variables always needed
    template_vars = {
        "title": "Pokémon Hangman",
        "games_won": session.get("games_won", 0),
        "games_lost": session.get("games_lost", 0),
        "difficulty": difficulty,
        "progress": len(session.get("encountered_pokemon", [])),
        "pokemon_image": session.get("pokemon_image"),
        "image_hidden": not game_complete,
        "game_complete": game_complete
    }
    
    # Word display handling
    if custom_word:
        template_vars["word"] = custom_word
    else:
        display_word = session.get("display_word", [])
        template_vars["word"] = " ".join(display_word)
    
    # Add guessed letters if they exist
    guessed_letters = session.get("guessed_letters", [])
    if guessed_letters:
        template_vars["guessed_letters"] = ", ".join(guessed_letters)
    else:
        template_vars["guessed_letters"] = ""
    
    # Add attempts left
    template_vars["attempts_left"] = session.get("attempts_left", 0)
    
    # Add message if it exists in session
    if "message" in session:
        template_vars["message"] = session["message"]
    
    return template_vars


@app.route("/reset")
def reset():
    """
    Reset all game stats and progress.
    Clears all game data including wins, losses, and encountered Pokémon.
    
    Returns:
        Redirect to the difficulty selection screen
    """
    session.clear()
    return redirect(url_for('hangman'))


@app.route("/change_difficulty")
def change_difficulty():
    """
    Change difficulty without resetting progress.
    Only clears the current game state but keeps win/loss stats and encountered Pokémon.
    
    Returns:
        Redirect to the difficulty selection screen
    """
    # Keep most session values but clear the active game
    current_difficulty = session.get("difficulty", "medium")
    session["game_active"] = False
    
    # Clear just the current game state
    if "word" in session:
        session.pop("word")
    if "display_word" in session:
        session.pop("display_word")
    if "guessed_letters" in session:
        session.pop("guessed_letters")
    if "attempts_left" in session:
        session.pop("attempts_left")
    
    return redirect(url_for('hangman'))


if __name__ == "__main__":
    app.run(debug=True)
