# Database configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///tournament.db'  # SQLite database URI
SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable modification tracking for SQLAlchemy
SECRET_KEY = 'your-random-secret-key'  # Secret key for Flask sessions (change this in production)

# Discord webhook URL (for posting match results to Discord)
DISCORD_WEBHOOK_URL = 'your-discord-webhook-url'  # Replace with your actual Discord webhook URL

# Google Form URL (for tournament sign-ups)
GOOGLE_FORM_URL = 'your-google-form-url'  # Replace with your actual Google Form URL

# User roles
ADMIN_ROLE = 'admin'  # Role for administrators
USER_ROLE = 'user'  # Role for regular users

# Bracket types
SINGLE_ELIMINATION = 'single'  # Single elimination bracket type
DOUBLE_ELIMINATION = 'double'  # Double elimination bracket type

# Game modes
DOMINATION = 'Domination'  # Domination game mode
CONVOY = 'Convoy'  # Convoy game mode
CONVERGENCE = 'Convergence'  # Convergence game mode

# Discord messages (template for match results)
MATCH_RESULT = "🏆 **Match Result** 🏆\nGame Mode: {game_mode}\nWinner: {winner}"

# Team names (optional, can be used for seeding or display)
TEAM_NAMES = [
    "Team Alpha", "Team Bravo", "Team Charlie", "Team Delta",
    "Team Echo", "Team Foxtrot", "Team Gamma", "Team Omega"
]

# Player first and last names (optional, can be used for generating random players)
FIRST_NAMES = ["John", "Jane", "Alice", "Bob", "Charlie", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Brown", "Davis", "Wilson", "Miller", "Lee", "Garcia", "Taylor", "Moore", "Clark"]

# Available characters (optional, can be used for player character selection)
CHARACTERS = [
    "Black Panther", "Doctor Strange", "Groot", "The Punisher", "Hela", "Iron Man",
    "Loki", "Rocket Raccoon", "Mantis", "Peni Parker", "Magneto", "Magik",
    "Spider-Man", "Venom", "Scarlet Witch", "Star-Lord", "Storm", "Luna Snow",
    "Hulk", "Namor", "Adam Warlock", "Jeff the Land Shark", "Thor", "Black Widow",
    "Captain America", "Cloak and Dagger", "Hawkeye", "Iron Fist", "Moon Knight",
    "Psylocke", "Squirrel Girl", "Winter Soldier", "Wolverine", "Mister Fantastic",
    "Invisible Woman"
]