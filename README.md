# Pokémon Hangman Game

A Game Boy-inspired Pokémon Hangman web application built with Flask. Test your Pokémon knowledge by guessing the names of the original 151 Pokémon!

![Pokémon Hangman Screenshot](preview.png)

## Features

- **Retro Game Boy Design**: Featuring pixel fonts and a classic Game Boy color scheme
- **Multiple Difficulty Levels**:
  - **Easy**: 10 attempts - Perfect for beginners
  - **Medium**: 6 attempts - Balanced challenge
  - **Hard**: 3 attempts - For Pokémon fans
  - **Extreme**: 1 attempt - True Pokémon masters only!
- **Official Pokémon Images**: Powered by the PokéAPI
- **Progress Tracking**: See how many of the original 151 Pokémon you've encountered
- **Win/Loss Statistics**: Track your performance at each difficulty level
- **Responsive Design**: Playable on desktop and mobile devices

## How to Play

1. Select your difficulty level
2. Guess letters one at a time to reveal the hidden Pokémon name
3. Try to guess the name before running out of attempts
4. Press Enter or click "Next Round" to continue to the next Pokémon
5. Aim to see all 151 original Pokémon!

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. Clone the repository
2. Create a virtual environment
3. Activate the virtual environment
- On Windows:
  ```
  venv\Scripts\activate
  ```
- On macOS/Linux:
  ```
  source venv/bin/activate
  ```

4. Install dependencies:
pip install -r requirements.txt

5. Run the application:
Write python main.py in the Terminal

6. Open a browser and navigate to:
http://127.0.0.1:5000/


## Project Structure

- `main.py` - Flask application and game logic
- `templates/` - HTML templates for the web interface
- `static/` - CSS styles, JavaScript, images, and Pokémon data
- `static/pokemon_images/` - Cached Pokémon images from PokéAPI

## Technical Details

- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Backend**: Flask (Python)
- **APIs Used**: PokéAPI for Pokémon data and images
- **Image Caching**: Pokémon images are cached locally to reduce API calls

## Credits

- Pokémon data from [PokéAPI](https://pokeapi.co/)
- Pixel font: [Press Start 2P](https://fonts.google.com/specimen/Press+Start+2P)
- Game Boy color palette inspired by the original Nintendo Game Boy

## License

This project is created for educational purposes. Pokémon is a registered trademark of Nintendo, The Pokémon Company, and Game Freak.