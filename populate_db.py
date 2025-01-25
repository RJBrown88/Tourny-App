import argparse
from app import app, db, User, Team, Player, Match, Bracket
import random
from sqlalchemy import text
import math

def calculate_byes(num_teams):
    """Calculates the number of byes needed in the first round."""
    next_power_of_2 = 2**(math.ceil(math.log2(num_teams)))
    return next_power_of_2 - num_teams

def clear_database():
    """
    Clear all data from the database by dropping and recreating all tables,
    except the User table.
    """
    with app.app_context():
        # Reflect the database to get metadata about all tables
        db.reflect()

        # Get a list of all tables except the User table
        tables_to_drop = [
            table for table in db.metadata.tables.values()
            if table.name != 'user'  # Skip the User table
        ]

        # Drop each table individually using a Connection object
        with db.engine.connect() as connection:
            for table in tables_to_drop:
                # Wrap the SQL string in SQLAlchemy's text() function
                connection.execute(text(f"DROP TABLE IF EXISTS {table.name}"))

        # Recreate all tables (except User, which was not dropped)
        db.create_all()

        print("Database cleared successfully (User table preserved)!")

def generate_random_stats():
    """Generate random stats for a player."""
    return {
        "kills": random.randint(5, 20),
        "deaths": random.randint(2, 15),
        "assists": random.randint(3, 18),
        "final_hits": random.randint(10, 30),
        "kos": random.randint(1, 10),
        "damage_taken": random.randint(1500, 3000),
        "damage_given": random.randint(2000, 3500),
        "damage_healed": random.randint(500, 1500),
    }

def populate_single_elimination(num_teams):
    """
    Populate the database with a single-elimination bracket.
    """
    with app.app_context():
        # Create a bracket
        bracket = Bracket(name="Single Elimination Bracket", bracket_type="single")
        db.session.add(bracket)
        db.session.commit()

        print(f"Creating single-elimination bracket: '{bracket.name}'")

        # List of unique team names
        team_names = [
            "Team Alpha", "Team Bravo", "Team Charlie", "Team Delta",
            "Team Echo", "Team Foxtrot", "Team Gamma", "Team Omega"
        ]
        # Ensure the number of team names is not less than the number of teams requested
        while len(team_names) < num_teams:
            team_names.extend([f"Team {chr(i)}" for i in range(ord('A'), ord('Z') + 1) if f"Team {chr(i)}" not in team_names])
        # Truncate the list to match the exact number of teams needed
        team_names = team_names[:num_teams]

        # List of first names and last names for players
        first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack", "Karen"]
        last_names = ["Smith", "Johnson", "Brown", "Davis", "Wilson", "Miller", "Lee", "Garcia", "Taylor", "Moore", "Clark"]

        # List of available characters (ensure no duplicates within a team)
        characters = [
            "Black Panther", "Doctor Strange", "Groot", "The Punisher", "Hela", "Iron Man",
            "Loki", "Rocket Raccoon", "Mantis", "Peni Parker", "Magneto", "Magik",
            "Spider-Man", "Venom", "Scarlet Witch", "Star-Lord", "Storm", "Luna Snow",
            "Hulk", "Namor", "Adam Warlock", "Jeff the Land Shark", "Thor", "Black Widow",
            "Captain America", "Cloak and Dagger", "Hawkeye", "Iron Fist", "Moon Knight",
            "Psylocke", "Squirrel Girl", "Winter Soldier", "Wolverine", "Mister Fantastic",
            "Invisible Woman"
        ]

        # Create teams and players
        teams = []
        for i, team_name in enumerate(team_names):
            team = Team(name=team_name, seed=i+1)
            db.session.add(team)
            db.session.commit()  # Commit to get the team ID

            # Shuffle the characters to ensure randomness
            random.shuffle(characters)

            # Create 6 players for the team, ensuring unique characters
            for j in range(6):
                # Generate a unique player name
                player_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                # Assign a unique character
                character_played = characters[j]
                # Generate random stats
                stats = generate_random_stats()
                player = Player(
                    player_name=player_name,
                    team_id=team.id,
                    character_played=character_played,
                    kills=stats["kills"],
                    deaths=stats["deaths"],
                    assists=stats["assists"],
                    final_hits=stats["final_hits"],
                    kos=stats["kos"],
                    damage_taken=stats["damage_taken"],
                    damage_given=stats["damage_given"],
                    damage_healed=stats["damage_healed"],
                )
                db.session.add(player)

                # Update team totals
                team.total_kills += stats["kills"]
                team.total_deaths += stats["deaths"]
                team.total_assists += stats["assists"]
                team.total_final_hits += stats["final_hits"]
                team.total_kos += stats["kos"]
                team.total_damage_taken += stats["damage_taken"]
                team.total_damage_given += stats["damage_given"]
                team.total_damage_healed += stats["damage_healed"]

            db.session.commit()
            teams.append(team)

        # --- Create Matches for Single Elimination ---
        round_num = 1
        remaining_teams = teams
        while len(remaining_teams) > 1:
            round_matches = []
            print(f"Creating matches for round {round_num}...")
            for i in range(0, len(remaining_teams), 2):
                if (i + 1) < len(remaining_teams):
                    team1 = remaining_teams[i]
                    team2 = remaining_teams[i + 1]

                    match = Match(
                        bracket_id=bracket.id,
                        team1_id=team1.id,
                        team2_id=team2.id,
                        round=round_num,
                        is_winners_bracket=True,
                        # ... (Set other match properties as needed)
                    )
                    db.session.add(match)
                    round_matches.append(match)
                    print(f"  - Created match: {team1.name} vs {team2.name}")
                else:
                    # Handle bye (if any) - You might want to create a placeholder match or directly advance the team
                    print(f"  - Bye for team: {remaining_teams[i].name}")
                    pass

            db.session.flush()

            # Determine winners (for demo, we'll randomly pick one)
            for match in round_matches:
                match.winner = random.choice([match.team1.name, match.team2.name])
                print(f"  - Winner of match: {match.winner}")

            # Advance winners to the next round
            remaining_teams = [match.team1 if match.winner == match.team1.name else match.team2 for match in round_matches]
            round_num += 1

        db.session.commit()

        # Query and print summary data
        num_teams_created = db.session.query(Team).count()
        num_matches_created = db.session.query(Match).count()
        print(f"Successfully populated single-elimination bracket with {num_teams} teams!")
        print(f"  - Number of teams created: {num_teams_created}")
        print(f"  - Number of matches created: {num_matches_created}")

def populate_double_elimination_power_of_2(num_teams):
    """
    Populate the database with a double-elimination bracket (power of 2 teams).
    """
    if not (num_teams > 0 and (num_teams & (num_teams - 1)) == 0):
        raise ValueError("Number of teams must be a power of 2 for this function.")

    with app.app_context():
        # Create a bracket
        bracket = Bracket(name="Double Elimination Bracket (Power of 2)", bracket_type="double")
        db.session.add(bracket)
        db.session.commit()
        print(f"Creating double-elimination bracket: '{bracket.name}'")

        # List of unique team names
        team_names = [f"Team {chr(i)}" for i in range(ord('A'), ord('A') + num_teams)]

        # List of first names and last names for players
        first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack", "Karen"]
        last_names = ["Smith", "Johnson", "Brown", "Davis", "Wilson", "Miller", "Lee", "Garcia", "Taylor", "Moore", "Clark"]

        # List of available characters (ensure no duplicates within a team)
        characters = [
            "Black Panther", "Doctor Strange", "Groot", "The Punisher", "Hela", "Iron Man",
            "Loki", "Rocket Raccoon", "Mantis", "Peni Parker", "Magneto", "Magik",
            "Spider-Man", "Venom", "Scarlet Witch", "Star-Lord", "Storm", "Luna Snow",
            "Hulk", "Namor", "Adam Warlock", "Jeff the Land Shark", "Thor", "Black Widow",
            "Captain America", "Cloak and Dagger", "Hawkeye", "Iron Fist", "Moon Knight",
            "Psylocke", "Squirrel Girl", "Winter Soldier", "Wolverine", "Mister Fantastic",
            "Invisible Woman"
        ]

        # Create teams and players
        teams = []
        print(f"Creating {num_teams} teams...")
        for i, team_name in enumerate(team_names):
            team = Team(name=team_name, seed=i + 1)
            db.session.add(team)
            db.session.commit()  # Commit to get the team ID
            print(f"  - Created team: {team.name} (seed: {team.seed})")

            # Shuffle the characters to ensure randomness
            random.shuffle(characters)

            # Create 6 players for the team, ensuring unique characters
            for j in range(6):
                # Generate a unique player name
                player_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                # Assign a unique character
                character_played = characters[j]
                # Generate random stats
                stats = generate_random_stats()
                player = Player(
                    player_name=player_name,
                    team_id=team.id,
                    character_played=character_played,
                    kills=stats["kills"],
                    deaths=stats["deaths"],
                    assists=stats["assists"],
                    final_hits=stats["final_hits"],
                    kos=stats["kos"],
                    damage_taken=stats["damage_taken"],
                    damage_given=stats["damage_given"],
                    damage_healed=stats["damage_healed"],
                )
                db.session.add(player)

                # Update team totals
                team.total_kills += stats["kills"]
                team.total_deaths += stats["deaths"]
                team.total_assists += stats["assists"]
                team.total_final_hits += stats["final_hits"]
                team.total_kos += stats["kos"]
                team.total_damage_taken += stats["damage_taken"]
                team.total_damage_given += stats["damage_given"]
                team.total_damage_healed += stats["damage_healed"]

            db.session.commit()
            teams.append(team)
        
        # --- Create Matches for Double Elimination (Power of 2) ---

        # Winners Bracket - Round 1
        winners_matches = []
        round_num = 1
        print(f"Creating matches for winners bracket round {round_num}...")
        for i in range(0, num_teams, 2):
            team1 = teams[i]
            team2 = teams[i+1]
            match = Match(bracket_id=bracket.id, team1_id=team1.id, team2_id=team2.id, round=round_num, is_winners_bracket=True)
            db.session.add(match)
            winners_matches.append(match)
            print(f"  - Created match: {team1.name} vs {team2.name}")
        db.session.flush()

        # Losers Bracket - Round 1
        losers_matches = []
        losers_round_num = 1
        print(f"Creating matches for losers bracket round {losers_round_num}...")
        for match in winners_matches:
            losers_match = Match(bracket_id=bracket.id, round=losers_round_num, is_winners_bracket=False)
            match.losers_match_id = losers_match.id  # Link losers match to winners match
            db.session.add(losers_match)
            losers_matches.append(losers_match)
            print(f"  - Created match: Losers Bracket Round {losers_round_num}")
        db.session.flush()

        # Function to advance a team in a bracket (winners or losers)
        def advance_team(match, next_match, winning_team_id):
            if next_match:
                if next_match.team1_id is None:
                    next_match.team1_id = winning_team_id
                else:
                    next_match.team2_id = winning_team_id
                db.session.commit()

        # Simulate the tournament
        winners_bracket_winners = {1: []}
        losers_bracket_winners = {1: []}

        # Winners Bracket - Round 1
        print("Simulating winners bracket round 1 matches...")
        for match in winners_matches:
            # Simulate outcome based on seed
            if random.random() < (match.team2.seed / (match.team1.seed + match.team2.seed)):
                winning_team = match.team1  # Higher seed wins
            else:
                winning_team = match.team2  # Lower seed wins

            losing_team = match.team2 if winning_team == match.team1 else match.team1
            match.winner = winning_team.name
            match.loser = losing_team.name
            print(f"  - Winner of match: {match.winner} (Loser: {match.loser})")

            winners_bracket_winners[1].append(winning_team)

            # Place the loser in the corresponding losers bracket match
            losers_match = match.losers_match
            if losers_match:
                losers_match.team1_id = losing_team.id  # Loser of round 1 always goes to team1
                db.session.commit()

        # Subsequent Rounds
        round_num = 2
        while len(winners_bracket_winners[round_num - 1]) > 1:
            winners_bracket_winners[round_num] = []
            losers_bracket_winners[round_num -1] = []

            # Winners Bracket Matches
            print(f"Creating matches for winners bracket round {round_num}...")
            for i in range(0, len(winners_bracket_winners[round_num - 1]), 2):
                team1 = winners_bracket_winners[round_num - 1][i]
                team2 = winners_bracket_winners[round_num - 1][i + 1]

                match = Match(bracket_id=bracket.id, team1_id=team1.id, team2_id=team2.id, round=round_num, is_winners_bracket=True)
                db.session.add(match)
                db.session.flush()
                print(f"  - Created match: {team1.name} vs {team2.name}")

                # Set the winners_next_match_id for the previous round's match
                if round_num > 1:
                  for prev_match in winners_matches:
                    if prev_match.round == round_num -1:
                        if prev_match.winner == team1.name or prev_match.winner == team2.name:
                            prev_match.winners_next_match_id = match.id
                            db.session.commit()
                
                winners_matches.append(match)

                # Simulate outcome based on seed
                if random.random() < (match.team2.seed / (match.team1.seed + match.team2.seed)):
                    winning_team = match.team1  # Higher seed wins
                else:
                    winning_team = match.team2  # Lower seed wins

                losing_team = match.team2 if winning_team == match.team1 else match.team1
                match.winner = winning_team.name
                match.loser = losing_team.name
                print(f"  - Winner of match: {match.winner} (Loser: {match.loser})")

                winners_bracket_winners[round_num].append(winning_team)

                # Create and link losers bracket match
                losers_match = Match(bracket_id=bracket.id, round=round_num, is_winners_bracket=False)
                db.session.add(losers_match)
                db.session.flush()
                match.losers_match_id = losers_match.id
                losers_matches.append(losers_match)
                print(f"  - Created match in losers bracket for loser: {losers_match.round}")

                # Place the loser in the corresponding losers bracket match
                if losers_match.team1_id is None:
                    losers_match.team1_id = losing_team.id
                else:
                    losers_match.team2_id = losing_team.id
                db.session.commit()

            # Losers Bracket Matches
            num_losers_matches = len(winners_bracket_winners[round_num])  # Number of losers bracket matches based on winners bracket
            print(f"Creating matches for losers bracket round {round_num}...")
            for i in range(0, num_losers_matches):
                # Skip the first round in losers bracket as it is already populated
                if round_num == 2:
                    losing_team_round_before = Match.query.filter_by(bracket_id=bracket.id, round=round_num - 1, is_winners_bracket=False).all()[i]
                    losers_match = losers_matches[i]
                    if losing_team_round_before.team1_id is not None:
                        losers_match.team2_id = losing_team_round_before.team1_id
                        db.session.commit()

                if round_num > 2:
                    # Get the two matches from the previous losers round
                    prev_losers_match_1 = losers_matches[(-1 * num_losers_matches) + (i * 2)] if len(losers_matches) > ((-1 * num_losers_matches) + (i * 2)) else None
                    prev_losers_match_2 = losers_matches[(-1 * num_losers_matches) + (i * 2) + 1] if len(losers_matches) > ((-1 * num_losers_matches) + (i * 2) + 1) else None
                    
                    # Get the winners of those matches
                    losers_team1 = Team.query.filter_by(name=prev_losers_match_1.winner).first() if prev_losers_match_1 and prev_losers_match_1.winner else None
                    losers_team2 = Team.query.filter_by(name=prev_losers_match_2.winner).first() if prev_losers_match_2 and prev_losers_match_2.winner else None

                    # Find the corresponding losers bracket match for the current round
                    current_losers_match = next((match for match in losers_matches if match.round == round_num and not match.team1_id and not match.team2_id), None)

                    if current_losers_match:
                        # Assign teams to the losers bracket match
                        if losers_team1:
                            current_losers_match.team1_id = losers_team1.id
                        if losers_team2:
                            current_losers_match.team2_id = losers_team2.id

                        # Determine the winner and advance to the next round
                        # Simulate outcome based on seed
                        if random.random() < (current_losers_match.team2.seed / (current_losers_match.team1.seed + current_losers_match.team2.seed)):
                            winning_team = current_losers_match.team1  # Higher seed wins
                        else:
                            winning_team = current_losers_match.team2  # Lower seed wins
                        current_losers_match.winner = winning_team.name if winning_team else None
                        print(f"  - Winner of match: {current_losers_match.winner}")

                        # Update the previous matches' losers_next_match_id
                        if prev_losers_match_1 and prev_losers_match_1.winner == current_losers_match.winner:
                            prev_losers_match_1.losers_next_match_id = current_losers_match.id
                        elif prev_losers_match_2 and prev_losers_match_2.winner == current_losers_match.winner:
                            prev_losers_match_2.losers_next_match_id = current_losers_match.id

                        # Add the winner to the next round's list
                        losers_bracket_winners[round_num].append(winning_team) if winning_team else None

                        db.session.commit()

            round_num += 1

        # Grand Finals
        winners_bracket_winner = winners_bracket_winners[list(winners_bracket_winners.keys())[-1]][0]
        losers_bracket_winner = losers_bracket_winners[list(winners_bracket_winners.keys())[-2]][0]
        grand_finals = Match(bracket_id=bracket.id, team1_id=winners_bracket_winner.id, team2_id=losers_bracket_winner.id, round=round_num, is_winners_bracket=False)
        db.session.add(grand_finals)
        db.session.flush()
        print(f"Creating grand finals match: {winners_bracket_winner.name} vs {losers_bracket_winner.name}")

        # Determine the winner of the grand finals
        if random.random() < (grand_finals.team2.seed / (grand_finals.team1.seed + grand_finals.team2.seed)):
            grand_finals_winner = grand_finals.team1  # Higher seed wins
        else:
            grand_finals_winner = grand_finals.team2  # Lower seed wins
        grand_finals.winner = grand_finals_winner.name
        grand_finals.loser = winners_bracket_winner.name if grand_finals_winner == losers_bracket_winner else losers_bracket_winner.name
        print(f"  - Winner of grand finals: {grand_finals.winner}")

        # Bracket Reset (if necessary)
        if grand_finals_winner == losers_bracket_winner:
            print("  - Bracket reset required!")
            bracket_reset = Match(bracket_id=bracket.id, team1_id=winners_bracket_winner.id, team2_id=losers_bracket_winner.id, round=round_num + 1, is_winners_bracket=False)
            db.session.add(bracket_reset)
            db.session.flush()

            # Determine the winner of the bracket reset
            if random.random() < (bracket_reset.team2.seed / (bracket_reset.team1.seed + bracket_reset.team2.seed)):
                bracket_reset_winner = bracket_reset.team1  # Higher seed wins
            else:
                bracket_reset_winner = bracket_reset.team2  # Lower seed wins
            bracket_reset.winner = bracket_reset_winner.name
            bracket_reset.loser = winners_bracket_winner.name if bracket_reset_winner == losers_bracket_winner else losers_bracket_winner.name
            print(f"  - Winner of bracket reset: {bracket_reset.winner}")

        db.session.commit()
        # Query and print summary data
        num_teams_created = db.session.query(Team).count()
        num_matches_created = db.session.query(Match).count()
        print(f"Successfully populated double-elimination bracket (power of 2) with {num_teams} teams!")
        print(f"  - Number of teams created: {num_teams_created}")
        print(f"  - Number of matches created: {num_matches_created}")

def populate_double_elimination_not_power_of_2(num_teams):
    """
    Populate the database with a double-elimination bracket (not power of 2 teams).
    Handles byes.
    """
    if num_teams <= 0:
        raise ValueError("Number of teams must be greater than 0.")

    with app.app_context():
        # Create a bracket
        bracket = Bracket(name="Double Elimination Bracket (Not Power of 2)", bracket_type="double")
        db.session.add(bracket)
        db.session.commit()
        print(f"Creating double-elimination bracket: '{bracket.name}'")

        # List of unique team names
        team_names = [
            "Team Alpha", "Team Bravo", "Team Charlie", "Team Delta",
            "Team Echo", "Team Foxtrot", "Team Gamma", "Team Omega"
        ]
        # Ensure the number of team names is not less than the number of teams requested
        while len(team_names) < num_teams:
            team_names.extend([f"Team {chr(i)}" for i in range(ord('A'), ord('Z') + 1) if f"Team {chr(i)}" not in team_names])
        # Truncate the list to match the exact number of teams needed
        team_names = team_names[:num_teams]

        # List of first names and last names for players
        first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack", "Karen"]
        last_names = ["Smith", "Johnson", "Brown", "Davis", "Wilson", "Miller", "Lee", "Garcia", "Taylor", "Moore", "Clark"]

        # List of available characters (ensure no duplicates within a team)
        characters = [
            "Black Panther", "Doctor Strange", "Groot", "The Punisher", "Hela", "Iron Man",
            "Loki", "Rocket Raccoon", "Mantis", "Peni Parker", "Magneto", "Magik",
            "Spider-Man", "Venom", "Scarlet Witch", "Star-Lord", "Storm", "Luna Snow",
            "Hulk", "Namor", "Adam Warlock", "Jeff the Land Shark", "Thor", "Black Widow",
            "Captain America", "Cloak and Dagger", "Hawkeye", "Iron Fist", "Moon Knight",
            "Psylocke", "Squirrel Girl", "Winter Soldier", "Wolverine", "Mister Fantastic",
            "Invisible Woman"
        ]

        # Create teams and players
        teams = []
        print(f"Creating {num_teams} teams...")
        for i, team_name in enumerate(team_names):
            team = Team(name=team_name, seed=i+1)
            db.session.add(team)
            db.session.commit()  # Commit to get the team ID
            print(f"  - Created team: {team.name} (seed: {team.seed})")

            # Shuffle the characters to ensure randomness
            random.shuffle(characters)

            # Create 6 players for the team, ensuring unique characters
            for j in range(6):
                # Generate a unique player name
                player_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                # Assign a unique character
                character_played = characters[j]
                # Generate random stats
                stats = generate_random_stats()
                player = Player(
                    player_name=player_name,
                    team_id=team.id,
                    character_played=character_played,
                    kills=stats["kills"],
                    deaths=stats["deaths"],
                    assists=stats["assists"],
                    final_hits=stats["final_hits"],
                    kos=stats["kos"],
                    damage_taken=stats["damage_taken"],
                    damage_given=stats["damage_given"],
                    damage_healed=stats["damage_healed"],
                )
                db.session.add(player)

                # Update team totals
                team.total_kills += stats["kills"]
                team.total_deaths += stats["deaths"]
                team.total_assists += stats["assists"]
                team.total_final_hits += stats["final_hits"]
                team.total_kos += stats["kos"]
                team.total_damage_taken += stats["damage_taken"]
                team.total_damage_given += stats["damage_given"]
                team.total_damage_healed += stats["damage_healed"]

            db.session.commit()
            teams.append(team)

        # --- Create Matches ---

        # Winners Bracket - Round 1 (with byes):
        num_byes = calculate_byes(num_teams)
        round_num = 1
        winners_matches = []
        bye_teams = teams[:num_byes]  # Assign byes to the highest seeded teams
        remaining_teams = teams[num_byes:]  # Teams that will play in the first round

        match_index = 0
        print(f"Creating matches for winners bracket round {round_num}...")
        while match_index < len(remaining_teams) // 2:
            team1 = remaining_teams[match_index]
            team2 = remaining_teams[len(remaining_teams) - 1 - match_index]  # Pair from opposite ends for seeding

            match = Match(
                bracket_id=bracket.id,
                team1_id=team1.id,
                team2_id=team2.id,
                round=round_num,
                is_winners_bracket=True
            )
            db.session.add(match)
            winners_matches.append(match)
            print(f"  - Created match: {team1.name} vs {team2.name}")
            match_index += 1
        
        db.session.flush()

        # Add byes to the winners bracket
        for i, bye_team in enumerate(bye_teams):
            if i < len(winners_matches):
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

        # Create placeholder matches for byes in losers bracket
        losers_round_num = 1
        losers_matches = []  # Initialize the list for losers bracket matches

        # Losers Bracket - Round 1
        print(f"Creating matches for losers bracket round {losers_round_num}...")
        for i, bye_team in enumerate(bye_teams):
            losers_match = Match(
                bracket_id=bracket.id,
                round=losers_round_num,
                is_winners_bracket=False,
                team1_id=bye_team.id,  # Assign bye team to team1_id
                team2_id=None  # No opponent (bye)
            )
            db.session.add(losers_match)
            db.session.flush()

            # Set the winner for the bye match (since it's a bye)
            losers_match.winner = bye_team.name
            losers_matches.append(losers_match)
            print(f"  - Created match in losers bracket for bye team: {bye_team.name}")

        db.session.flush()

        # Simulate winners bracket matches and populate losers bracket
        winners_bracket_winners = {1: [Team.query.get(match.winner) for match in winners_matches if match.winner is not None]}
        round_num = 2  # Start from the second round for winners bracket

        while len(winners_bracket_winners[round_num - 1]) > 1:
            winners_bracket_winners[round_num] = []
            losers_bracket_winners = {}
            print(f"Creating matches for winners bracket round {round_num}...")
            for i in range(0, len(winners_bracket_winners[round_num - 1]), 2):
                team1 = winners_bracket_winners[round_num - 1][i]
                team2 = winners_bracket_winners[round_num - 1][i + 1] if i + 1 < len(winners_bracket_winners[round_num - 1]) else None

                if team2:  # Proceed if there are two teams to compete
                    match = Match(
                        bracket_id=bracket.id,
                        team1_id=team1.id,
                        team2_id=team2.id,
                        round=round_num,
                        is_winners_bracket=True
                    )
                    db.session.add(match)
                    db.session.flush()
                    print(f"  - Created match: {team1.name} vs {team2.name}")

                    # Set the winners_next_match_id for the previous round's match
                    for prev_match in winners_matches:
                        if prev_match.round == round_num - 1:
                            if prev_match.winner == team1.name or prev_match.winner == team2.name:
                                prev_match.winners_next_match_id = match.id
                                db.session.commit()

                    winners_matches.append(match)

                    # Simulate the match outcome based on seed
                    if random.random() < (team2.seed / (team1.seed + team2.seed)):
                        winning_team = team1
                        losing_team = team2
                    else:
                        winning_team = team2
                        losing_team = team1

                    match.winner = winning_team.name
                    match.loser = losing_team.name
                    print(f"  - Winner of match: {match.winner} (Loser: {match.loser})")
                    winners_bracket_winners[round_num].append(winning_team)

                    # Create and link the corresponding losers bracket match
                    losers_match = Match(bracket_id=bracket.id, round=round_num, is_winners_bracket=False)
                    db.session.add(losers_match)
                    db.session.flush()

                    match.losers_match_id = losers_match.id
                    losers_matches.append(losers_match)

                    # Assign the losing team to the corresponding losers bracket match
                    if losers_match.team1_id is None:
                        losers_match.team1_id = losing_team.id
                    else:
                        losers_match.team2_id = losing_team.id
                    db.session.commit()

            round_num += 1
        
        # Losers Bracket - Round 2 onwards
        losers_round_num = 2
        losers_bracket_winners = {1: [Team.query.get(match.winner) for match in losers_matches if match.winner is not None and match.round == 1]}
        
        while True:
            # Logic to create matches in subsequent rounds of losers bracket
            num_winners_previous_round = len(winners_bracket_winners.get(losers_round_num, []))
            num_losers_previous_round = len(losers_bracket_winners.get(losers_round_num - 1, []))

            # Determine the number of matches for this round
            num_matches_this_round = num_winners_previous_round + num_losers_previous_round // 2 if num_losers_previous_round > 0 else num_winners_previous_round

            # If no matches to be played, break the loop
            if num_matches_this_round == 0:
                break

            losers_bracket_winners[losers_round_num] = []
            print(f"Creating matches for losers bracket round {losers_round_num}...")

            # Create matches for this round
            for i in range(num_matches_this_round):
                match = Match(bracket_id=bracket.id, round=losers_round_num, is_winners_bracket=False)
                db.session.add(match)
                losers_matches.append(match)
                print(f"  - Created match in losers bracket round {losers_round_num}")

            db.session.flush()

            # Assign teams to the matches
            match_index = 0
            # Assign winners from the winners bracket to losers bracket matches
            for team in winners_bracket_winners.get(losers_round_num, []):
                if match_index < len(losers_matches):
                    if losers_matches[match_index].team1_id is None:
                        losers_matches[match_index].team1_id = team.id
                    else:
                        losers_matches[match_index].team2_id = team.id
                    match_index += 1

            # Assign winners from the previous losers bracket round
            for team in losers_bracket_winners.get(losers_round_num - 1, []):
                if match_index < len(losers_matches):
                    if losers_matches[match_index].team1_id is None:
                        losers_matches[match_index].team1_id = team.id
                    else:
                        losers_matches[match_index].team2_id = team.id
                    match_index += 1
            
            db.session.commit()

            # Simulate outcomes for the matches in this round
            for match in losers_matches:
                if match.round == losers_round_num:
                    # Check if the match has two teams
                    if match.team1_id and match.team2_id:
                        team1 = Team.query.get(match.team1_id)
                        team2 = Team.query.get(match.team2_id)

                        # Simulate outcome based on seed
                        if random.random() < (team2.seed / (team1.seed + team2.seed)):
                            winning_team = team1  # Higher seed wins
                        else:
                            winning_team = team2  # Lower seed wins

                        match.winner = winning_team.name
                        match.loser = team1.name if winning_team == team2 else team2.name
                        print(f"  - Winner of match: {match.winner} (Loser: {match.loser})")
                        losers_bracket_winners[losers_round_num].append(winning_team)
            
            db.session.commit()
            losers_round_num += 1

        # Grand Finals
        # Find the last match in the winners bracket to get the winner
        last_winners_match = db.session.query(Match).filter_by(bracket_id=bracket.id, is_winners_bracket=True).order_by(Match.round.desc()).first()
        winners_bracket_winner = Team.query.filter_by(name=last_winners_match.winner).first() if last_winners_match else None

        # Find the last match in the losers bracket to get the winner
        last_losers_match = db.session.query(Match).filter_by(bracket_id=bracket.id, is_winners_bracket=False).order_by(Match.round.desc()).first()
        losers_bracket_winner = Team.query.filter_by(name=last_losers_match.winner).first() if last_losers_match else None
        
        if winners_bracket_winner is not None and losers_bracket_winner is not None:
            grand_finals = Match(bracket_id=bracket.id, team1_id=winners_bracket_winner.id, team2_id=losers_bracket_winner.id, round=round_num, is_winners_bracket=False)
            db.session.add(grand_finals)
            db.session.flush()
            print(f"Creating grand finals match: {winners_bracket_winner.name} vs {losers_bracket_winner.name}")

            # Determine the winner of the grand finals
            if random.random() < (grand_finals.team2.seed / (grand_finals.team1.seed + grand_finals.team2.seed)):
                grand_finals_winner = grand_finals.team1  # Higher seed wins
            else:
                grand_finals_winner = grand_finals.team2  # Lower seed wins
            grand_finals.winner = grand_finals_winner.name
            grand_finals.loser = winners_bracket_winner.name if grand_finals_winner == losers_bracket_winner else losers_bracket_winner.name
            print(f"  - Winner of grand finals: {grand_finals.winner}")

            # Bracket Reset (if necessary)
            if grand_finals_winner == losers_bracket_winner:
                print("  - Bracket reset required!")
                bracket_reset = Match(bracket_id=bracket.id, team1_id=winners_bracket_winner.id, team2_id=losers_bracket_winner.id, round=round_num + 1, is_winners_bracket=False)
                db.session.add(bracket_reset)
                db.session.flush()

                # Determine the winner of the bracket reset
                if random.random() < (bracket_reset.team2.seed / (bracket_reset.team1.seed + bracket_reset.team2.seed)):
                    bracket_reset_winner = bracket_reset.team1  # Higher seed wins
                else:
                    bracket_reset_winner = bracket_reset.team2  # Lower seed wins
                bracket_reset.winner = bracket_reset_winner.name
                bracket_reset.loser = winners_bracket_winner.name if bracket_reset_winner == losers_bracket_winner else losers_bracket_winner.name
                print(f"  - Winner of bracket reset: {bracket_reset.winner}")

        db.session.commit()

        # Query and print summary data
        num_teams_created = db.session.query(Team).count()
        num_matches_created = db.session.query(Match).count()
        print(f"Successfully populated double-elimination bracket (not power of 2) with {num_teams} teams!")
        print(f"  - Number of teams created: {num_teams_created}")
        print(f"  - Number of matches created: {num_matches_created}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage the tournament database.")
    parser.add_argument("--clear", action="store_true", help="Clear the database (except the User table)")
    parser.add_argument("--populate_single", type=int, metavar="NUM_TEAMS", help="Populate with a single-elimination bracket")
    parser.add_argument("--populate_double_power2", type=int, metavar="NUM_TEAMS", help="Populate with a double-elimination bracket (power of 2 teams)")
    parser.add_argument("--populate_double", type=int, metavar="NUM_TEAMS", help="Populate with a double-elimination bracket (not power of 2 teams)")

    args = parser.parse_args()
    
    try:
        if args.clear:
            clear_database()
        elif args.populate_single:
            populate_single_elimination(args.populate_single)
        elif args.populate_double_power2:
            populate_double_elimination_power_of_2(args.populate_double_power2)
        elif args.populate_double:
            populate_double_elimination_not_power_of_2(args.populate_double)
        else:
            print("No action specified. Use --help to see available commands.")
        
        print("Database population completed!")
    except Exception as e:
        print(f"An error occurred: {e}")