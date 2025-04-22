from flask import Blueprint, render_template, request, redirect, url_for, session
import random, os, requests
from pathlib import Path

# Define the blueprint
hangman_bp = Blueprint('hangman', __name__, template_folder='templates', static_folder='static')

# --- Helper Functions (Moved from main.py) ---

def load_pokemon_names():
    """
    Load the list of Pokémon names from the pokemon.txt file.

    Returns:
        list: A list of Pokémon names. If file is not found it returns a small default list as a fallback.
    """
    try:
        # Assuming static folder is accessible relative to where the app runs
        # Or adjust path if needed based on your project structure
        static_dir = Path(__file__).parent / 'static'
        with open(static_dir / "pokemon.txt", "r") as f:
            pokemon_list = [line.strip() for line in f.readlines()]
        return pokemon_list
    except FileNotFoundError:
        print("Warning: static/pokemon.txt not found. Using default list.")
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
        # Use Path relative to this file's location
        static_dir = Path(__file__).parent / 'static'
        cache_dir = static_dir / "pokemon_images"
        cache_dir.mkdir(parents=True, exist_ok=True) # Use parents=True

        # Check if we have a cached image
        cache_file = cache_dir / f"{formatted_name}.png"

        # Construct URL path relative to static folder
        static_image_path = f"/static/pokemon_images/{formatted_name}.png"

        if cache_file.exists():
            return static_image_path

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

            if not image_url: # Handle cases where the image URL might be null
                 print(f"Warning: No official artwork URL found for {api_formatted_name}")
                 return None # Or return a placeholder image URL

            img_response = requests.get(image_url, stream=True)
            if img_response.status_code == 200:
                with open(cache_file, 'wb') as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)

                return static_image_path
            else:
                 print(f"Warning: Failed to download image for {api_formatted_name}. Status: {img_response.status_code}")
                 # Optionally return the direct API URL as fallback, but caching failed
                 # return image_url
                 return None # Indicate failure
        else:
            print(f"Warning: Failed to fetch Pokémon data for {api_formatted_name}. Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching Pokémon image for {pokemon_name}: {e}")
        return None


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
    available_pokemon = [p for p in pokemon_list if p not in session.get("encountered_pokemon", [])] # Use .get for safety

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
        # Ensure encountered_pokemon exists before appending
        "encountered_pokemon": session.get("encountered_pokemon", []) + [pokemon]
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
    guess = request.form.get("guess", "").lower() # Use .get for safety
    pokemon = session.get("pokemon", "").lower()
    guessed_letters = session.get("guessed_letters", [])
    attempts_left = session.get("attempts_left", attempts)
    display_word = list(session.get("display_word", [])) # Ensure it's a list

    # Check if game is active before processing guess
    if not session.get("game_active", False):
         # Redirect or show an error if trying to guess when game isn't active
         return redirect(url_for('.hangman')) # Redirect to start/difficulty selection

    message = ""
    alert_type = "info" # Default alert type
    round_complete = False

    # Validate the guess
    if not guess.isalpha() or len(guess) != 1:
        message = "Please enter a single letter, a-z."
        alert_type = "info"
    elif guess in guessed_letters:
        message = f"You already guessed '{guess.upper()}'."
        alert_type = "warning"
    else:
        # Process valid guess
        guessed_letters.append(guess)
        session["guessed_letters"] = guessed_letters # Update session immediately

        if guess in pokemon:
            # Handle correct guess
            correct_guess = False
            for i, letter in enumerate(pokemon):
                if letter == guess:
                    # Capitalize first letter if it matches
                    if i == 0:
                        display_word[i] = letter.upper()
                    else:
                        display_word[i] = letter
                    correct_guess = True # Mark that the guess was correct

            if correct_guess: # Only update display_word if guess was correct
                 session["display_word"] = display_word # Update session

            message = f"Correct! '{guess.upper()}' is in the name. You have {attempts_left} attempts left."
            alert_type = "success"
        else:
            # Handle incorrect guess
            attempts_left -= 1
            session["attempts_left"] = attempts_left # Update session
            message = f"Incorrect! '{guess.upper()}' is not in the name. You have {attempts_left} attempts left."
            alert_type = "danger"

    # Update session variables that change regardless of guess validity (like message)
    session["message"] = message
    session["alert_type"] = alert_type

    # Check win condition (must happen AFTER display_word is potentially updated)
    if "_" not in session.get("display_word", []): # Check updated session value
        capitalized_word = session.get("pokemon", "").capitalize()
        message = f"Congratulations! You guessed the Pokémon: {capitalized_word}."
        session["message"] = message # Update message for win
        session["alert_type"] = "success"
        session["rounds_won"] = session.get("rounds_won", 0) + 1
        round_complete = True
        session["game_active"] = False  # Mark game as inactive

        # Add to caught Pokémon collection if not already caught
        caught_list = session.get("caught_pokemon", [])
        if capitalized_word not in caught_list:
            caught_list.append(capitalized_word)
            session["caught_pokemon"] = caught_list # Update session

        # Render immediately on win
        return render_template("hangman.html",
                              **_get_template_vars(difficulty, round_complete=True, custom_word=capitalized_word))

    # Check lose condition (must happen AFTER attempts_left is updated)
    elif session.get("attempts_left", attempts) <= 0:
        capitalized_word = session.get("pokemon", "").capitalize()
        message = f"Game over! The Pokémon was: {capitalized_word}."
        session["message"] = message # Update message for loss
        session["alert_type"] = "danger"
        session["rounds_lost"] = session.get("rounds_lost", 0) + 1
        round_complete = True
        session["game_active"] = False  # Mark game as inactive

        # Render immediately on loss
        return render_template("hangman.html",
                              **_get_template_vars(difficulty, round_complete=True, custom_word=capitalized_word))

    # If game continues, render current state
    return render_template("hangman.html",
                          **_get_template_vars(difficulty, round_complete=round_complete))


# Image class determination
def _get_image_class(difficulty, round_complete):
    """Get the appropriate image class based on difficulty and game state."""
    if round_complete or difficulty == "easy":
        return "pokemon-image-visible"
    elif difficulty == "medium":
        return "pokemon-image-blurred"
    # Default to hidden for hard/extreme or if state is unclear
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
            - pokemon: The word to display (either progress or the full word)
            - guessed_letters: String of guessed letters
            - attempts_left: Remaining attempts
            - message: Status message for the player
            - alert_type: Bootstrap alert type for the message
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
        "game_active": session.get("game_active", False),
        # Ensure defaults for potentially missing session keys
        "guessed_letters": ", ".join(session.get("guessed_letters", [])),
        "attempts_left": session.get("attempts_left", "?"), # Provide default if not set
        "message": session.get("message", ""),
        "alert_type": session.get("alert_type", "info")
    }

    if custom_word:
        template_vars["pokemon"] = custom_word
    elif "display_word" in session:
        template_vars["pokemon"] = " ".join(session["display_word"])
    else:
         template_vars["pokemon"] = "" # Default if no word set

    # Clear the message from session after retrieving it so it doesn't persist
    session.pop("message", None)
    session.pop("alert_type", None)

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
    # Keep track of total wins/losses across resets if desired
    # total_wins = session.get("total_wins", 0) + session.get("rounds_won", 0)
    # total_losses = session.get("total_losses", 0) + session.get("rounds_lost", 0)
    session.clear()

    if preserve_difficulty and current_difficulty:
        session["difficulty"] = current_difficulty
    elif new_difficulty:
        session["difficulty"] = new_difficulty

    # Restore total wins/losses if tracking them
    # session["total_wins"] = total_wins
    # session["total_losses"] = total_losses

    _init_session()  # Initialize default values for a new game/round


# --- Routes ---

@hangman_bp.route("/")
def home():
    """Render the home page (which might be the difficulty selection)."""
    # Redirect to hangman route which handles difficulty selection
    return redirect(url_for('.hangman'))


@hangman_bp.route("/hangman", methods=["GET", "POST"])
def hangman():
    """Main hangman game route."""
    _init_session() # Ensure session vars exist

    # Determine difficulty: POST uses session, GET uses args or session fallback
    if request.method == "POST":
        difficulty = session.get("difficulty", "medium")
    else: # GET request
        difficulty = request.args.get('difficulty', session.get("difficulty", "medium"))

    # Set attempts based on difficulty
    if difficulty == 'easy':
        attempts = 10
    elif difficulty == 'hard':
        attempts = 3
    elif difficulty == 'extreme':
        attempts = 1
    else: # Medium or default
        difficulty = "medium" # Ensure difficulty is explicitly set if default
        attempts = 6

    # Store determined difficulty in session if it changed or wasn't set
    if 'difficulty' not in session or session['difficulty'] != difficulty:
        session['difficulty'] = difficulty

    # Handle game initialization with difficulty (GET with difficulty arg)
    if request.method == "GET" and 'difficulty' in request.args:
         # Clear previous game state when explicitly selecting difficulty
        _reset_session(new_difficulty=difficulty)
        return _start_new_game(difficulty, attempts)

    # Process the guess (POST)
    elif request.method == "POST":
        return _process_guess(difficulty, attempts)

    # Show difficulty selection or ongoing game state (GET without difficulty arg)
    elif request.method == "GET":
        if session.get("game_active", False):
            # Continue existing game
            template_vars = _get_template_vars(difficulty)
            return render_template("hangman.html", **template_vars)
        else:
            # Show difficulty selection screen
            template_vars = {
                "title": "Pokémon Hangman",
                "rounds_won": session.get("rounds_won", 0),
                "rounds_lost": session.get("rounds_lost", 0),
                # Add any other stats you want to show on difficulty screen
            }
            return render_template("difficulty.html", **template_vars)


@hangman_bp.route("/change_difficulty")
def change_difficulty():
    """Reset session completely and show difficulty selection."""
    _reset_session() # Full reset
    # Redirect to the main hangman route which will show difficulty selection
    return redirect(url_for('.hangman'))


@hangman_bp.route("/restart")
def restart():
    """Restart the game with the same difficulty."""
    # Preserve difficulty, reset other game state
    _reset_session(preserve_difficulty=True)
    # Redirect to the main hangman route to start a new game with the preserved difficulty
    # It will call _start_new_game because game_active is now False
    return redirect(url_for('.hangman'))
