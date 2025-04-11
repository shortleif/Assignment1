from flask import Flask, render_template, request, redirect, url_for, session
import random, os

app = Flask(__name__)
app.secret_key = os.urandom(24)


# Load the list of Pokémon names
def load_pokemon_names():
    try:
        with open("static/pokemon.txt", "r") as f:
            pokemon_list = [line.strip() for line in f.readlines()]
        return pokemon_list
    except FileNotFoundError:
        # If the file is not found produce a list for testing
        return ["Pikachu", "Charmander", "Bulbasaur", "Squirtle"]


# Home
@app.route("/")
def home():
    return render_template("index.html")


# Hangman
@app.route("/hangman", methods=["GET", "POST"])
def hangman():
    if request.method == "GET":
        # Start the game
        pokemon_list = load_pokemon_names()
        pokemon = random.choice(pokemon_list)

        # Initialize session variables
        session["word"] = pokemon
        session["guessed_letters"] = []
        session["attempts_left"] = 8
        session["display_word"] = ["_" if char.isalpha() else char for char in pokemon]
        
        return render_template("hangman.html",
                               word=" ".join(session["display_word"]),
                               attempts_left=session["attempts_left"],
                               guessed_letters="",
                               message="Guess a Pokémon!")
    
    elif request.method == "POST":
        # Process the guess
        guess = request.form["guess"].lower()
        word = session.get("word", "").lower()
        guessed_letters = session.get("guessed_letters", [])
        attempts_left = session.get("attempts_left", 6)
        display_word = session.get("display_word", [])

        message = ""

        # Check if guess is a valid single letter
        if not guess.isalpha() or len(guess) != 1:
            message = "Please enter a single letter."
        # Check if not guessed before
        elif guess in guessed_letters:
            message = f"You already guessed {guess}."
        else:
            # Add letter to list of guessed letters
            guessed_letters.append(guess)

            # Check if the guess is correct
            if guess in word:
                for i, letter in enumerate(word):
                    if letter == guess:
                        display_word[i] = letter
                message = f"Correct! {guess} is in the name of the Pokémon."
            # If the guess is incorrect
            else:
                attempts_left -= 1
                message = f"Incorrect! {guess} is not in the name of the Pokémon. You have {attempts_left} attempts left."

        # Update session variable data
        session["guessed_letters"] = guessed_letters
        session["attempts_left"] = attempts_left
        session["display_word"] = display_word

        # Check if the game is over
        if "_" not in display_word:
            message = f"Congratulations! You guessed the Pokémon: {word}."
        elif attempts_left <= 0:
            message = f"Game over! The Pokémon was: {word}."
        
        return render_template("hangman.html", 
                              word=" ".join(display_word),
                              attempts_left=attempts_left,
                              guessed_letters=", ".join(guessed_letters),
                              message=message)


# Memory
@app.route("/memory")
def memory():
    return render_template("memory.html")


if __name__ == "__main__":
    app.run(debug=True)
