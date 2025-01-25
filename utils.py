import math
import random

def calculate_byes(num_teams):
    """Calculates the number of byes needed in the first round."""
    next_power_of_2 = 2 ** (math.ceil(math.log2(num_teams)))
    return next_power_of_2 - num_teams

def simulate_match(team1, team2):
    """Simulates a match outcome based on team seeds."""
    if random.random() < (team2.seed / (team1.seed + team2.seed)):
        return team1  # Higher seed wins
    else:
        return team2  # Lower seed wins