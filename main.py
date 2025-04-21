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
    Load the list of Pokémon names from the pokemon.txt file.
    
    Returns:
        list: A list of Pokémon names. If file is not found it returns a small default list as a fallback.
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
    - The PokéAPI does not require credentials and is free to use.

    Each Pokémon is saved as a PNG file in the static directory for future use to reduce API calls.
    Subsequent requests use the cached image file instead of fetching it again.

    Note that the Pokémon Nidoran has the same name for two genders and
    are generally named as Nidoran (male) and Nidoran (female).
    This is incompatible with Hangman functionality.
    This function handles that by randomly choosing one of the a genders.
    The evolved version of both genders are still available as normal.

    There is also a built in fix for fetching Mr. Mime, which is named as "Mime" in the Pokémon list.
    
    Args:
        pokemon_name (str): The name of the Pokémon to fetch
        
    Returns:
        str or None: URL path to the Pokémon image if successful, None if:
            - API request fails
            - Image download fails
            - File operations fail
            - Invalid Pokemon name provided
            
    Raises:
        Exception: Prints error message if any operation fails
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
        
        # Handle special cases for API formatting
        api_formatted_name = formatted_name
        if formatted_name == "nidoran":
            # Randomly select M/F on first run
            gender = random.choice(["m", "f"])
            api_formatted_name = f"nidoran-{gender}"
        elif formatted_name == "mime":
            api_formatted_name = "mr-mime"
        
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
    """Main hangman game route."""
    
    """
    Main hangman game route that handles all game states and difficulty management.

    Session Variables:
    - encountered_pokemon: List of all Pokémon shown to player in the game round
    - caught_pokemon: Number of successfully guessed Pokémon at the end of the game
    - rounds_won: Number of successful guesses
    - rounds_lost: Number of failed attempts
    - difficulty: Current game difficulty level
    
    Handles the different difficulty levels and sets the number of attempts, defaults to medium.

    Methods:
    - GET without difficulty: Shows difficulty selection screen
    - GET with difficulty: Starts new game or continues existing game
    - POST: Processes each guess letter for active game, triggers win/loss conditions, updates session variables

    Returns:
        Rendered template for the appropriate game state
    """
    # Initialize session variables
    _init_session()
    
    # Set attempts based on difficulty
    difficulty = request.args.get('difficulty', session.get("difficulty", "medium"))
    if difficulty == 'easy':
        attempts = 10
    elif difficulty == 'hard':
        attempts = 3
    elif difficulty == 'extreme':
        attempts = 1
    else:
        attempts = 6
    
    # Handle game initialization with difficulty
    if request.method == "GET" and 'difficulty' in request.args:
        return _start_new_game(difficulty, attempts)
    
    # Show difficulty selection screen
    elif request.method == "GET":
        template_vars = {
            "title": "Pokémon Hangman",
            "rounds_won": session.get("rounds_won", 0),
            "rounds_lost": session.get("rounds_lost", 0),
            "game_active": session.get("game_active", False),
            "current_progress": "".join(session.get("display_word", [])) if session.get("game_active") else ""
        }
        return render_template("difficulty.html", **template_vars)
    
    # Process the guess
    elif request.method == "POST":
        return _process_guess(difficulty, attempts)


def _start_new_game(difficulty, attempts):
    """
    Start a new hangman game with the specified difficulty.
    
    Args:
        difficulty (str): The difficulty level ('easy', 'medium', 'hard', or 'extreme')
        attempts (int): Number of attempts allowed based on difficulty
        
    Returns:
        Response: Either:
            - hangman.html template with new game state
            - completion.html template if all Pokemon encountered
            
    Session Updates:
        - pokemon: Current Pokemon to guess
        - pokemon_image: URL to Pokemon image
        - guessed_letters: List of guessed letters
        - attempts_left: Remaining attempts
        - display_word: Current game progress
        - game_active: Game status
        - difficulty: Current difficulty
        - encountered_pokemon: Updated list of shown Pokemon
    """
    pokemon_list = load_pokemon_names()
    
    # Filter out previously encountered Pokémon
    available_pokemon = [p for p in pokemon_list if p not in session["encountered_pokemon"]]
    
    # Show completion screen if all Pokémon encountered
    if not available_pokemon:
        return render_template("completion.html", 
                            title="Pokémon Hangman - Complete!",
                            caught_pokemon=len(session.get("caught_pokemon", [])),
                            total_pokemon=len(pokemon_list),
                            rounds_won=session.get("rounds_won", 0),
                            rounds_lost=session.get("rounds_lost", 0))
    
    # Select and get image for new Pokémon
    pokemon = random.choice(available_pokemon)
    pokemon_image = get_pokemon_image(pokemon)
    
    # Update session state
    session.update({
        "pokemon": pokemon,
        "pokemon_image": pokemon_image,
        "guessed_letters": [],
        "attempts_left": attempts,
        "display_word": ["_" if char.isalpha() else char for char in pokemon],
        "game_active": True,
        "difficulty": difficulty,
        "encountered_pokemon": session["encountered_pokemon"] + [pokemon]
    })
    
    # Get template variables and render new game
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

    # Fetch session information
    guess = request.form["guess"].lower()
    pokemon = session.get("pokemon", "").lower()
    guessed_letters = session.get("guessed_letters", [])
    attempts_left = session.get("attempts_left", attempts)
    display_word = session.get("display_word", [])

    message = ""
    round_complete = False

    # Validate the guess
    if not guess.isalpha() or len(guess) != 1:
        message = "Please enter a single letter, a-z."
        alert_type = "info"
    elif guess in guessed_letters:
        message = f"You already guessed {guess}."
        alert_type = "warning"
    else:
        # Process valid guess
        guessed_letters.append(guess)

        if guess in pokemon:
            # Handle correct guess
            for i, letter in enumerate(pokemon):
                if letter == guess:
                    # Capitalize first letter
                    if i == 0:
                        display_word[i] = letter.upper()
                    else:
                        display_word[i] = letter
            message = f"Correct! {guess} is in the name of the Pokémon. You have {attempts_left} attempts left."
            alert_type = "success"
        else:
            # Handle incorrect guess
            attempts_left -= 1
            message = f"Incorrect! {guess.upper()} is not in the name of the Pokémon. You have {attempts_left} attempts left."
            alert_type = "danger"

    # Update session variables
    session["guessed_letters"] = guessed_letters
    session["attempts_left"] = attempts_left
    session["display_word"] = display_word
    session["alert_type"] = alert_type  # Add alert type to session

    # Check if player won
    if "_" not in display_word:
        capitalized_word = pokemon.capitalize()
        message = f"Congratulations! You guessed the Pokémon: {capitalized_word}."
        session["rounds_won"] = session.get("rounds_won", 0) + 1
        round_complete = True
        session["game_active"] = False  # Mark game as inactive
        session["message"] = message
        
        # Add to caught Pokémon collection if not already caught
        if pokemon.capitalize() not in session["caught_pokemon"]:
            session["caught_pokemon"].append(pokemon.capitalize())

        return render_template("hangman.html",
                              **_get_template_vars(difficulty, round_complete=True, custom_word=pokemon.capitalize()))
    
    # Check if player lost
    elif attempts_left <= 0:
        capitalized_word = pokemon.capitalize()
        message = f"Game over! The Pokémon was: {capitalized_word}."
        session["rounds_lost"] = session.get("rounds_lost", 0) + 1
        round_complete = True
        session["game_active"] = False  # Mark game as inactive
        session["message"] = message
    
    # Return current game state
    session["message"] = message
    return render_template("hangman.html",
                          **_get_template_vars(difficulty, round_complete=round_complete))


# Initialization function to set up session variables
def _init_session():
    """
    Initialize all required session variables with defaults.
    
    Session Variables:
    - encountered_pokemon (list): Pokemon already shown to player
    - rounds_won (int): Number of successful guesses
    - rounds_lost (int): Number of failed attempts
    - caught_pokemon (list): Successfully guessed Pokemon names
    - game_active (bool): Whether a game is currently in progress
    
    Returns:
        None
    """
    defaults = {
        "encountered_pokemon": [],
        "rounds_won": 0,
        "rounds_lost": 0,
        "caught_pokemon": [],
        "game_active": False
    }
    
    for key, value in defaults.items():
        if key not in session:
            session[key] = value


# Image class determination
def _get_image_class(difficulty, round_complete):
    """Get the appropriate image class based on difficulty and game state."""
    if round_complete or difficulty == "easy":
        return "pokemon-image-visible"
    elif difficulty == "medium":
        return "pokemon-image-blurred"
    return "pokemon-image-hidden"


def _get_template_vars(difficulty, round_complete=False, custom_word=None):
    """
    Get common template variables for rendering.
    
    Args:
        difficulty (str): Current difficulty level ('easy', 'medium', 'hard', 'extreme')
        round_complete (bool, optional): Whether the current round is complete. Defaults to False.
        custom_word (str, optional): Custom word to display instead of display_word. Defaults to None.
    
    Returns:
        dict: Template variables including:
            - title: Page title
            - rounds_won: Number of successful guesses
            - rounds_lost: Number of failed attempts
            - difficulty: Current difficulty level
            - progress: Number of Pokemon encountered
            - pokemon_image: URL to Pokemon image
            - image_class: CSS class for image visibility
            - round_complete: Game round completion status
            - game_active: Whether game is in progress
    """
    template_vars = {
        "title": "Pokémon Hangman",
        "rounds_won": session.get("rounds_won", 0),
        "rounds_lost": session.get("rounds_lost", 0),
        "difficulty": difficulty,
        "progress": len(session.get("encountered_pokemon", [])),
        "pokemon_image": session.get("pokemon_image"),
        "image_class": _get_image_class(difficulty, round_complete),
        "round_complete": round_complete,
        "game_active": session.get("game_active", False)
    }
    
    if custom_word:
        template_vars["pokemon"] = custom_word
    elif "display_word" in session:
        template_vars["pokemon"] = " ".join(session["display_word"])
    
    if "guessed_letters" in session:
        template_vars["guessed_letters"] = ", ".join(session["guessed_letters"])
    
    if "attempts_left" in session:
        template_vars["attempts_left"] = session["attempts_left"]
    
    if "message" in session:
        template_vars["message"] = session["message"]
        template_vars["alert_type"] = session.get("alert_type", "info")
    
    return template_vars


# Reset session state based on user input
def _reset_session(preserve_difficulty=False, new_difficulty=None):
    """
    Reset session state with options to preserve or set new difficulty.
    
    Args:
        preserve_difficulty (bool): Keep current difficulty setting
        new_difficulty (str): Set a specific difficulty level
    """
    current_difficulty = session.get("difficulty", "medium") if preserve_difficulty else None
    session.clear()
    
    if preserve_difficulty and current_difficulty:
        session["difficulty"] = current_difficulty
    elif new_difficulty:
        session["difficulty"] = new_difficulty
    
    _init_session()  # Initialize default values

@app.route("/change_difficulty")
def change_difficulty():
    """Reset and show difficulty selection."""
    _reset_session()
    return render_template("difficulty.html", **_get_template_vars("medium"))

@app.route("/restart")
def restart():
    """Restart while preserving difficulty."""
    _reset_session(preserve_difficulty=True)
    current_difficulty = session.get("difficulty", "medium")
    return redirect(url_for('hangman', difficulty=current_difficulty))


if __name__ == "__main__":
    app.run(debug=True)
