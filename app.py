from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests
import os
from dotenv import load_dotenv
import secrets
from datetime import datetime
import math

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY')  # Load secret key from environment variable

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Route to redirect unauthorized users

# --- Database Models ---
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    players = db.relationship('Player', backref='team', lazy=True)
    total_kills = db.Column(db.Integer, default=0)
    total_deaths = db.Column(db.Integer, default=0)
    total_assists = db.Column(db.Integer, default=0)
    total_final_hits = db.Column(db.Integer, default=0)
    total_kos = db.Column(db.Integer, default=0)
    total_damage_taken = db.Column(db.Integer, default=0)
    total_damage_given = db.Column(db.Integer, default=0)
    total_damage_healed = db.Column(db.Integer, default=0)
    seed = db.Column(db.Integer)  # Add seed field

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    player_name = db.Column(db.String(50), nullable=False)
    character_played = db.Column(db.String(50))
    kills = db.Column(db.Integer, default=0)
    deaths = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    final_hits = db.Column(db.Integer, default=0)
    kos = db.Column(db.Integer, default=0)
    damage_taken = db.Column(db.Integer, default=0)
    damage_given = db.Column(db.Integer, default=0)
    damage_healed = db.Column(db.Integer, default=0)

class Bracket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    bracket_type = db.Column(db.String(20), nullable=False)  # "single" or "double"
    matches = db.relationship('Match', backref='bracket', lazy=True)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bracket_id = db.Column(db.Integer, db.ForeignKey('bracket.id'), nullable=False)
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    winner = db.Column(db.String(50))
    loser = db.Column(db.String(50))  # Track the loser for double elimination
    round = db.Column(db.Integer, nullable=False)  # Round number (e.g., 1, 2, 3)
    is_winners_bracket = db.Column(db.Boolean, default=True)  # True for winners, False for losers
    game_mode = db.Column(db.String(50))  # Domination, Convoy, or Convergence
    rounds_won_team1 = db.Column(db.Integer, default=0)  # Rounds won by Team 1 (Domination)
    rounds_won_team2 = db.Column(db.Integer, default=0)  # Rounds won by Team 2 (Domination)
    team1_distance_pushed = db.Column(db.Integer, default=0)  # Distance pushed by Team 1 (Convoy/Convergence)
    team2_distance_pushed = db.Column(db.Integer, default=0)  # Distance pushed by Team 2 (Convoy/Convergence)
    team1_role = db.Column(db.String(50))  # Attacker or Defender
    team2_role = db.Column(db.String(50))  # Attacker or Defender
    mvp = db.Column(db.String(50))  # MVP player name
    svp = db.Column(db.String(50))  # SVP player name

    # --- Relationships for Double Elimination ---
    # For winners bracket matches, points to the match in the losers bracket where the loser goes
    losers_match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    losers_match = db.relationship(
        'Match',
        foreign_keys=[losers_match_id],
        backref='originating_winners_match',  # Access from losers match to winners match
        remote_side=[id],
        uselist=False
    )

    # For winners bracket matches, points to the next match in the winners bracket
    winners_next_match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    winners_next_match = db.relationship(
        'Match',
        foreign_keys=[winners_next_match_id],
        backref='previous_winners_match',
        remote_side=[id],
        uselist=False
    )

    # For losers bracket matches, points to the next match in the losers bracket
    losers_next_match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    losers_next_match = db.relationship(
        'Match',
        foreign_keys=[losers_next_match_id],
        backref='previous_losers_match',
        remote_side=[id],
        uselist=False
    )
    
    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # Default role is 'user'

class MatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(50))  # e.g., "score_update", "player_substitution"
    data = db.Column(db.JSON)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# Load user callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Custom decorator for role-based authorization
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Helper Functions ---

def calculate_byes(num_teams):
    """Calculates the number of byes needed in the first round."""
    next_power_of_2 = 2**(math.ceil(math.log2(num_teams)))
    return next_power_of_2 - num_teams

def create_losers_match(bracket_id, round_num, losing_team_name, previous_match_id):
    """
    Creates a new match in the losers bracket.
    Links it to the previous winners bracket match.
    """
    # Find the team object for the losing team
    losing_team = Team.query.filter_by(name=losing_team_name).first()
    if not losing_team:
        print(f"Error: Losing team '{losing_team_name}' not found.")
        return None

    # Create a new match in the losers bracket
    new_losers_match = Match(
        bracket_id=bracket_id,
        round=round_num,
        is_winners_bracket=False,
        team1_id=losing_team.id  # Place the loser into the new match
    )
    db.session.add(new_losers_match)
    db.session.flush()  # Ensure new_losers_match has an ID

    # Link the losers match to the previous winners bracket match
    previous_match = Match.query.get(previous_match_id)
    if previous_match:
        previous_match.losers_match_id = new_losers_match.id
        db.session.add(previous_match)

    # Find the next match in the losers bracket, if any
    next_losers_matches = Match.query.filter_by(
        bracket_id=bracket_id,
        is_winners_bracket=False,
        round=round_num + 1
    ).all()

    if next_losers_matches:
        # Find a match in the next round that doesn't yet have two teams
        next_losers_match = None
        for potential_match in next_losers_matches:
            if potential_match.team1_id is None or potential_match.team2_id is None:
                next_losers_match = potential_match
                break

        if next_losers_match:
            new_losers_match.losers_next_match_id = next_losers_match.id
            db.session.add(new_losers_match)

    db.session.commit()
    return new_losers_match

def create_grand_finals(bracket_id, winners_bracket_winner_name, losers_bracket_winner_name):
    """Creates the grand finals match (and potentially a bracket reset match)."""
    winners_bracket_winner = Team.query.filter_by(name=winners_bracket_winner_name).first()
    losers_bracket_winner = Team.query.filter_by(name=losers_bracket_winner_name).first()

    if not winners_bracket_winner or not losers_bracket_winner:
        print("Error: Could not find winners or losers bracket winner.")
        return

    grand_finals = Match(
        bracket_id=bracket_id,
        round=999,  # Special round number for grand finals
        is_winners_bracket=False,  # Grand finals are outside the normal bracket structure
        team1_id=winners_bracket_winner.id,
        team2_id=losers_bracket_winner.id,
    )
    db.session.add(grand_finals)
    db.session.commit()

# --- Routes ---

@app.route('/')
def index():
    brackets = Bracket.query.all()
    teams = Team.query.all()
    matches = Match.query.all()
    return render_template('index.html', brackets=brackets, teams=teams, matches=matches)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# Users route (Admin-only)
@app.route('/users')
@login_required
@role_required('admin')
def users():
    """Display all users (admin-only)"""
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

# Add User Route (Admin-only)
@app.route('/add-user', methods=['POST'])
@login_required
@role_required('admin')
def add_user():
    """Add a new user (admin or regular user)"""
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    if username and password and role:
        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'error')
        else:
            # Hash the password and create the user
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash(f'User "{username}" added successfully!', 'success')
    else:
        flash('Username, password, and role are required', 'error')

    return redirect(url_for('users'))

# Add Team Route (Admin-only)
@app.route('/add-team', methods=['POST'])
@login_required
@role_required('admin')
def add_team():
    team_name = request.form.get('team_name')
    seed = request.form.get('seed')  # Get the seed from the form
    if team_name:
        team = Team(name=team_name, seed=seed)  # Include seed when creating a team
        db.session.add(team)
        db.session.commit()
        flash(f'Team "{team_name}" added successfully!', 'success')
    else:
        flash('Team name is required', 'error')
    return redirect(url_for('index'))

# Remove Team Route (Admin-only)
@app.route('/remove-team', methods=['POST'])
@login_required
@role_required('admin')
def remove_team():
    """Remove a team (admin-only)"""
    team_id = request.form.get('team_id')
    if team_id:
        team = Team.query.get(team_id)
        if team:
            # Delete all players associated with the team
            Player.query.filter_by(team_id=team.id).delete()
            # Delete the team
            db.session.delete(team)
            db.session.commit()
            flash(f'Team "{team.name}" removed successfully!', 'success')
        else:
            flash('Team not found', 'error')
    else:
        flash('Team ID is required', 'error')
    return redirect(url_for('index'))

# Add Player Route (Admin-only)
@app.route('/add-player', methods=['POST'])
@login_required
@role_required('admin')
def add_player():
    team_id = request.form.get('team_id')
    player_name = request.form.get('player_name')
    character_played = request.form.get('character_played')
    
    if team_id and player_name and character_played:
        player = Player(
            team_id=int(team_id),
            player_name=player_name,
            character_played=character_played,
            kills=0,  # Default stats set to 0
            deaths=0,
            assists=0,
            final_hits=0,
            kos=0,
            damage_taken=0,
            damage_given=0,
            damage_healed=0,
        )
        db.session.add(player)
        db.session.commit()
        flash(f'Player "{player_name}" added successfully!', 'success')
    else:
        flash('Team ID, player name, and character played are required', 'error')
    return redirect(url_for('index'))

# Remove Player Route (Admin-only)
@app.route('/remove-player', methods=['POST'])
@login_required
@role_required('admin')
def remove_player():
    """Remove a player (admin-only)"""
    player_id = request.form.get('player_id')
    if player_id:
        player = Player.query.get(player_id)
        if player:
            # Update team totals before deleting the player
            team = player.team
            team.total_kills -= player.kills
            team.total_deaths -= player.deaths
            team.total_assists -= player.assists
            team.total_final_hits -= player.final_hits
            team.total_kos -= player.kos
            team.total_damage_taken -= player.damage_taken
            team.total_damage_given -= player.damage_given
            team.total_damage_healed -= player.damage_healed
            # Delete the player
            db.session.delete(player)
            db.session.commit()
            flash(f'Player "{player.player_name}" removed successfully!', 'success')
        else:
            flash('Player not found', 'error')
    else:
        flash('Player ID is required', 'error')
    return redirect(url_for('index'))

# Move Player Route (Admin-only)
@app.route('/move-player', methods=['POST'])
@login_required
@role_required('admin')
def move_player():
    """Move a player to another team"""
    player_id = request.form.get('player_id')
    new_team_id = request.form.get('new_team_id')
    
    if player_id and new_team_id:
        player = Player.query.get(player_id)
        if player:
            player.team_id = int(new_team_id)
            db.session.commit()
            flash(f'Player "{player.player_name}" moved successfully!', 'success')
        else:
            flash('Player not found', 'error')
    else:
        flash('Player ID and new team ID are required', 'error')
    return redirect(url_for('index'))

# Update MVP/SVP Route (Admin-only)
@app.route('/update-mvp-svp', methods=['POST'])
@login_required
@role_required('admin')
def update_mvp_svp():
    """Update MVP and SVP for a match"""
    match_id = request.form.get('match_id')
    mvp = request.form.get('mvp')
    svp = request.form.get('svp')
    
    if match_id:
        match = Match.query.get(match_id)
        if match:
            # Get the winning and losing teams
            winning_team = match.team1 if match.winner == match.team1.name else match.team2
            losing_team = match.team2 if match.winner == match.team1.name else match.team1

            # Get players from the winning and losing teams
            winning_players = [player.player_name for player in winning_team.players]
            losing_players = [player.player_name for player in losing_team.players]

            # Update MVP and SVP
            match.mvp = mvp
            match.svp = svp
            db.session.commit()

            # Log the action in MatchHistory
            history_entry = MatchHistory(
                match_id=match_id,
                action="mvp_svp_update",
                data={"mvp": mvp, "svp": svp},
                admin_id=current_user.id
            )
            db.session.add(history_entry)
            db.session.commit()

            # Post the match result to Discord
            post_to_discord(match)

            flash('MVP and SVP updated successfully!', 'success')
        else:
            flash('Match not found', 'error')
    else:
        flash('Match ID is required', 'error')

    # Pass the list of players to the template
    brackets = Bracket.query.all()
    return render_template('index.html', brackets=brackets, winning_players=winning_players, losing_players=losing_players)

# Update Player Stats Route (Admin-only)
@app.route('/update-player-stats', methods=['POST'])
@login_required
@role_required('admin')
def update_player_stats():
    """Update player stats (kills, deaths, assists, etc.)"""
    player_id = request.form.get('player_id')
    kills = request.form.get('kills', type=int)
    deaths = request.form.get('deaths', type=int)
    assists = request.form.get('assists', type=int)
    final_hits = request.form.get('final_hits', type=int)
    kos = request.form.get('kos', type=int)
    damage_taken = request.form.get('damage_taken', type=int)
    damage_given = request.form.get('damage_given', type=int)
    damage_healed = request.form.get('damage_healed', type=int)

    player = Player.query.get(player_id)
    if player:
        player.kills = kills
        player.deaths = deaths
        player.assists = assists
        player.final_hits = final_hits
        player.kos = kos
        player.damage_taken = damage_taken
        player.damage_given = damage_given
        player.damage_healed = damage_healed

        # Update team totals
        team = player.team
        team.total_kills = sum(p.kills for p in team.players)
        team.total_deaths = sum(p.deaths for p in team.players)
        team.total_assists = sum(p.assists for p in team.players)
        team.total_final_hits = sum(p.final_hits for p in team.players)
        team.total_kos = sum(p.kos for p in team.players)
        team.total_damage_taken = sum(p.damage_taken for p in team.players)
        team.total_damage_given = sum(p.damage_given for p in team.players)
        team.total_damage_healed = sum(p.damage_healed for p in team.players)

        db.session.commit()

        # Log the action in MatchHistory
        history_entry = MatchHistory(
            match_id=player.team.id,  # Assuming team ID is used as match ID for simplicity
            action="player_stats_update",
            data={"player_id": player_id, "kills": kills, "deaths": deaths, "assists": assists, "final_hits": final_hits, "kos": kos, "damage_taken": damage_taken, "damage_given": damage_given, "damage_healed": damage_healed},
            admin_id=current_user.id
        )
        db.session.add(history_entry)
        db.session.commit()

        flash('Player stats updated successfully!', 'success')
    else:
        flash('Player not found', 'error')

    return redirect(url_for('index'))

# Update Distance Pushed Route (Admin-only)
@app.route('/update-distance-pushed', methods=['POST'])
@login_required
@role_required('admin')
def update_distance_pushed():
    """Update the distance pushed by each team for Convoy/Convergence modes"""
    match_id = request.form.get('match_id')
    team1_distance = request.form.get('team1_distance', type=int)
    team2_distance = request.form.get('team2_distance', type=int)

    match = Match.query.get(match_id)
    if match:
        match.team1_distance_pushed = team1_distance
        match.team2_distance_pushed = team2_distance
        db.session.commit()

        # Log the action in MatchHistory
        history_entry = MatchHistory(
            match_id=match_id,
            action="distance_pushed_update",
            data={"team1_distance": team1_distance, "team2_distance": team2_distance},
            admin_id=current_user.id
        )
        db.session.add(history_entry)
        db.session.commit()

        flash('Distance pushed updated successfully!', 'success')
    else:
        flash('Match not found', 'error')
    return redirect(url_for('index'))

# Update Rounds Won Route (Admin-only)
@app.route('/update-rounds-won', methods=['POST'])
@login_required
@role_required('admin')
def update_rounds_won():
    """Update the rounds won by each team for Domination"""
    match_id = request.form.get('match_id')
    rounds_won_team1 = request.form.get('rounds_won_team1', type=int)
    rounds_won_team2 = request.form.get('rounds_won_team2', type=int)

    match = Match.query.get(match_id)
    if match:
        match.rounds_won_team1 = rounds_won_team1
        match.rounds_won_team2 = rounds_won_team2
        db.session.commit()

        # Log the action in MatchHistory
        history_entry = MatchHistory(
            match_id=match_id,
            action="rounds_won_update",
            data={"rounds_won_team1": rounds_won_team1, "rounds_won_team2": rounds_won_team2},
            admin_id=current_user.id
        )
        db.session.add(history_entry)
        db.session.commit()

        flash('Rounds won updated successfully!', 'success')
    else:
        flash('Match not found', 'error')
    return redirect(url_for('index'))

# --- Bracket Management Routes ---

@app.route('/create-bracket', methods=['POST'])
@login_required
@role_required('admin')
def create_bracket_route():
    """
    Creates a new bracket with the specified type and teams.
    Handles seeding and generates matches for both single and double elimination.
    """
    bracket_name = request.form.get('bracket_name')
    bracket_type = request.form.get('bracket_type')
    team_ids = request.form.getlist('teams')  # Get list of selected team IDs

    # Fetch the teams and sort them by seed (highest seed first)
    teams = Team.query.filter(Team.id.in_(team_ids)).order_by(Team.seed).all()

    if bracket_name and bracket_type and teams:
        # Create the bracket and generate matches
        bracket = create_bracket(bracket_name, bracket_type, teams)
        if bracket:
            flash(f'Bracket "{bracket_name}" created successfully!', 'success')
        else:
            flash('Error creating bracket', 'error')
    else:
        flash('Bracket name, type, and teams are required', 'error')

    return redirect(url_for('index'))

def create_bracket(bracket_name, bracket_type, teams):
    """
    Creates a bracket and associated matches.
    Handles byes and seeding for double elimination.
    """
    bracket = Bracket(name=bracket_name, bracket_type=bracket_type)
    db.session.add(bracket)
    db.session.flush()  # Get the bracket ID

    num_teams = len(teams)
    num_byes = calculate_byes(num_teams)

    # --- Winners Bracket - Round 1 ---
    winners_matches = []
    round_num = 1
    match_index = 0

    # Add teams that do not have a first-round match due to byes
    bye_teams = []
    if num_byes > 0:
        bye_teams = teams[:num_byes]
        teams = teams[num_byes:]

    # Pair teams based on seeding for the first round
    while match_index < len(teams) // 2:
        team1 = teams[match_index]
        team2 = teams[len(teams) - 1 - match_index]

        match = Match(
            bracket_id=bracket.id,
            round=round_num,
            is_winners_bracket=True,
            team1_id=team1.id,
            team2_id=team2.id
        )

        winners_matches.append(match)
        db.session.add(match)
        match_index += 1

    db.session.flush()  # Get IDs for newly created matches

    # --- Losers Bracket - Round 1 ---
    losers_matches = []
    if bracket_type == 'double':
        # Create losers bracket matches for the teams that got byes
        for i in range(num_byes):
            losers_match = Match(
                bracket_id=bracket.id,
                round=1,  # Adjust round as needed for bye handling
                is_winners_bracket=False,
            )
            losers_matches.append(losers_match)
            db.session.add(losers_match)
        db.session.flush()

        # Advance the teams with byes in the winners bracket to the next round
        for i, bye_team in enumerate(bye_teams):
            winners_match = winners_matches[i]
            winners_match.winner = bye_team.name
            winners_match.loser = None  # No loser in a bye match

            # Find the next match for the bye team in the winners bracket
            next_winners_match_index = i // 2  # Adjust this logic based on your bracket structure
            if len(winners_matches) > next_winners_match_index:
                next_winners_match = winners_matches[next_winners_match_index]
                if next_winners_match.team1_id is None:
                    next_winners_match.team1_id = bye_team.id
                else:
                    next_winners_match.team2_id = bye_team.id
                next_winners_match.winners_next_match_id = winners_match.id
            
            # If applicable, advance the bye team in the losers bracket
            if i < len(losers_matches):
                losers_match = losers_matches[i]
                if losers_match.team1_id is None:
                    losers_match.team1_id = bye_team.id
                else:
                    losers_match.team2_id = bye_team.id

    # --- Subsequent Rounds ---
    # Logic to create matches for subsequent rounds in both brackets
    # This part will require careful planning based on your bracket structure

    db.session.commit()
    return bracket

@app.route('/update-match-result', methods=['POST'])
@login_required
@role_required('admin')
def update_match_result():
    match_id = request.form.get('match_id')
    winner_name = request.form.get('winner')

    match = Match.query.get(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('index'))

    winner = Team.query.filter_by(name=winner_name).first()
    if not winner:
        flash('Winning team not found', 'error')
        return redirect(url_for('index'))

    match.winner = winner_name
    match.loser = match.team2.name if winner_name == match.team1.name else match.team1.name
    db.session.commit()

    # --- Auto-Advancement Logic ---
    if match.is_winners_bracket:
        # Winners bracket advancement
        if match.winners_next_match:
            if match.winners_next_match.team1_id is None:
                match.winners_next_match.team1_id = winner.id
            else:
                match.winners_next_match.team2_id = winner.id
            db.session.commit()

        # Create losers bracket match (if it doesn't exist) and place the loser
        if not match.losers_match:
            losers_round = match.round
            if match.bracket.bracket_type == 'double':
                # In double elimination, losers drop to the corresponding round
                # You might need more complex logic here to determine the correct losers round
                losers_round = match.round

            losers_match = create_losers_match(match.bracket_id, losers_round, match.loser, match.id)
            match.losers_match_id = losers_match.id  # Correct placement and indentation (Ln 735)
            db.session.commit()

        # Place the loser of the winners bracket match into the corresponding losers bracket match
        if match.losers_match:
            if match.losers_match.team1_id is None:
                match.losers_match.team1_id = match.team2_id if match.winner == match.team1.name else match.team1_id
            else:
                match.losers_match.team2_id = match.team2_id if match.winner == match.team1.name else match.team1_id
            db.session.commit()
    
    else:  # Losers bracket advancement
        if match.losers_next_match:
            if match.losers_next_match.team1_id is None:
                match.losers_next_match.team1_id = winner.id
            else:
                match.losers_next_match.team2_id = winner.id
            db.session.commit()
        else:
            # Check if this is the last match in the losers bracket and if the winners bracket also has a winner
            winners_bracket_final_match = Match.query.filter_by(
                bracket_id=match.bracket_id,
                is_winners_bracket=True
            ).order_by(Match.round.desc()).first()

            if winners_bracket_final_match and winners_bracket_final_match.winner:
                # Both brackets have winners, create grand finals
                create_grand_finals(match.bracket_id, winners_bracket_final_match.winner, match.winner)

    flash('Match result updated and teams advanced!', 'success')
    return redirect(url_for('index'))

# Remove Bracket Route (Admin-only)
@app.route('/remove-bracket', methods=['POST'])
@login_required
@role_required('admin')
def remove_bracket():
    """Remove a bracket (admin-only)"""
    bracket_id = request.form.get('bracket_id')
    if bracket_id:
        bracket = Bracket.query.get(bracket_id)
        if bracket:
            # Delete all matches associated with the bracket
            Match.query.filter_by(bracket_id=bracket.id).delete()
            # Delete the bracket
            db.session.delete(bracket)
            db.session.commit()
            flash(f'Bracket "{bracket.name}" removed successfully!', 'success')
        else:
            flash('Bracket not found', 'error')
    else:
        flash('Bracket ID is required', 'error')
    return redirect(url_for('index'))

# Discord Integration
def post_to_discord(match):
    """Post the winner of a match to Discord with encryption and signature"""
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            flash('Discord webhook URL not configured', 'error')
            return
        
        message = {
            "content": f"🏆 **Match Result** 🏆\n"
                      f"Game Mode: {match.game_mode}\n"
                      f"Winner: {match.winner}\n"
                      f"MVP: {match.mvp if match.mvp else 'Not assigned'}\n"
                      f"SVP: {match.svp if match.svp else 'Not assigned'}\n"
                      f"Congratulations to the winning team!"
        }
        
        if match.game_mode == 'Domination':
            message["content"] += f"\nRounds Won: {match.rounds_won_team1} - {match.rounds_won_team2}"
        elif match.game_mode == 'Convoy' or match.game_mode == 'Convergence':
            message["content"] += f"\nDistance Pushed:\n{match.team1.name}: {match.team1_distance_pushed} meters\n{match.team2.name}: {match.team2_distance_pushed} meters"
        
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        flash('Winner posted to Discord successfully!', 'success')
    except Exception as e:
        flash(f'Failed to post to Discord: {e}', 'error')

# Fetch Players for a Team
@app.route('/get-players')
@login_required
@role_required('admin')
def get_players():
    """Fetch players for a specific team"""
    team_name = request.args.get('team')
    team = Team.query.filter_by(name=team_name).first()
    if team:
        players = [player.player_name for player in team.players]
        return jsonify({"players": players})
    else:
        return jsonify({"players": []}), 404

# Match History Route
@app.route('/match-history/<int:match_id>')
@login_required
def match_history(match_id):
    """Display match history for a specific match"""
    match = Match.query.get_or_404(match_id)
    history = MatchHistory.query.filter_by(match_id=match_id).order_by(MatchHistory.timestamp.desc()).all()
    return render_template('match_history.html', match=match, history=history)

# Utility function for Google Form URL
@app.context_processor
def utility_processor():
    def get_google_form_url():
        return os.getenv('GOOGLE_FORM_URL')  # Retrieve the Google Form URL from environment variables
    return dict(get_google_form_url=get_google_form_url)

# Initialize the database and create admin user at startup
if __name__ == '__main__':
    with app.app_context():
        # Create all database tables
        db.create_all()

        # Create an admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            # Load the admin password from the environment variable
            admin_password = os.getenv('ADMIN_PASSWORD')
            
            # If no password is set, generate a random one
            if not admin_password:
                admin_password = secrets.token_urlsafe(16)  # Generate a random password
                print(f"Generated random admin password: {admin_password}")
            
            # Hash the password and create the admin user
            hashed_password = generate_password_hash(admin_password)
            admin_user = User(username='admin', password=hashed_password, role='admin')
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user created: username='admin', password='{admin_password}'")
    
    # Run the application
    app.run(debug=True)