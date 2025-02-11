import csv
import re
import argparse
from collections import defaultdict
import json
import os
import random

class Table:
    def __init__(self, table_id):
        self.table_id = table_id
        self.team_usage = defaultdict(int)
        self.last_used_by = []  # Keep track of recent teams that used this table
        
    def add_team(self, team):
        """Record a team playing on this table."""
        self.team_usage[team] += 1
        self.last_used_by.append(team)
            
    def get_usage(self, team):
        """Get number of times a team has played on this table."""
        return self.team_usage[team]
    
    def get_total_usage(self):
        """Get total number of times all teams have played on this table."""
        return sum(self.team_usage.values())
    
    def was_recently_used_by(self, team):
        """Check if team recently played on this table."""
        recent_usage = 0
        while self.last_used_by and team == self.last_used_by[-1 * (recent_usage + 1)]:
            recent_usage += 1
        return recent_usage



class Match:
    def __init__(self, match_str):
        """Initialize match from string format (e.g. '1-2')"""
        home_team, away_team = match_str.split('-')
        self.home_team = int(home_team)
        self.away_team = int(away_team)
        self.assigned_table = None
    
    def assign_table(self, table):
        """Assign a table to this match and update table usage."""
        self.assigned_table = table
        table.add_team(self.home_team)
        table.add_team(self.away_team)
    
    def __str__(self):
        table_str = f" on {self.assigned_table.table_id}" if self.assigned_table else ""
        return f"{self.home_team}-{self.away_team}{table_str}"

class Week:
    def __init__(self, week_id, date, matches, bye_team_id, num_teams, previous_week=None):
        self.week_id = int(week_id)
        self.date = date
        self.matches = [Match(match) for match in matches]
        self.available_tables = set()
        self.num_teams = num_teams
        self.bye_team_id = bye_team_id
        self.previous_week = previous_week  # Store reference to previous week

    def get_team_previous_table(self, team_id):
        """Get the table a team played on in the previous week."""
        if not self.previous_week:
            return None
        
        for match in self.previous_week.matches:
            if team_id in (match.home_team, match.away_team):
                return match.assigned_table
        return None
    
    def assign_tables(self, tables):
        """Assign tables to matches for this week."""
        table_list = list(tables.values())  # Convert the tables to a list
        random.shuffle(table_list)          # Shuffle the list in place
        
        self.available_tables = set(table_list)  # Convert the shuffled list back to a set
        print(f"Available tables: {self.available_tables}")
        
        for match in self.matches:
            if str(match.home_team) == str(self.bye_team_id) or str(match.away_team) == str(self.bye_team_id):
                continue  # Skip this match if either team is the bye team
            best_table = self.find_best_table(match)

            if best_table:
                match.assign_table(best_table)
                self.available_tables.remove(best_table)
            else:
                raise ValueError(f"No available table for match {match} in week {self.week_id}")
    
    def find_best_table(self, match):
        """Find the best available table for a match based on usage history."""
        if not self.available_tables:
            return None

        valid_tables = []
        for table in self.available_tables:
            # Get current usage counts for both teams on this table
            home_usage = table.get_usage(match.home_team)
            away_usage = table.get_usage(match.away_team)
            
            usage = (home_usage + away_usage) // table.get_total_usage() if table.get_total_usage() > 0 else 0
            valid_tables.append((table, usage))

        if not valid_tables:
            raise ValueError(f"No valid table available that maintains balance for match {match}")
        
        best_table = None
        min_value = None

        for table, match_usage in valid_tables:
            # Check if the table was recently used by either team
            recently_used = table.was_recently_used_by(match.home_team) + table.was_recently_used_by(match.away_team)
            
            # Calculate the total usage of the table by both teams
            total_usage = table.get_usage(match.home_team) + table.get_usage(match.away_team)
            
            # Create a tuple for comparison
            current_value = (
                recently_used,  # Prefer tables not recently used by the teams
                match_usage,
                total_usage
            )
            
            # Update the best table if this one is better
            if min_value is None or current_value < min_value:
                min_value = current_value
                best_table = table

        return best_table

    
    def __str__(self):
        return f"Week {self.week_id} ({self.date}): {[str(m) for m in self.matches]}"

class Schedule:
    def __init__(self):
        self.weeks = []
    
    def add_week(self, week):
        if self.weeks:
            week.previous_week = self.weeks[-1]
        self.weeks.append(week)
    
    def __str__(self):
        return "\n".join([str(week) for week in self.weeks])

class TableAssignmentManager:
    def __init__(self, filename="787-2025-01-705-02-Schedule.csv", config_path="configs/table_configs.json"):
        self.filename = filename
        self.config_path = config_path
        self.schedule = Schedule()
        self.num_teams = 0
        self.bye_team_id = None
        self.tables = {}
        self.team_names = {}  # Add dictionary for team name mapping
        self.location_id, self.year, self.month, self.division, self.session = self.validate_filename()
        self.initialize_team_names()  # Add team names initialization
        self.initialize_tables()
        self.read_schedule()
    
    def validate_filename(self):
        """Validate and parse the filename pattern."""
        pattern = r"(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-Schedule\.csv"
        match = re.match(pattern, self.filename)
        if not match:
            raise ValueError("Filename does not match the required pattern.")
        return match.groups()
    
    def get_table_config(self):
        """Get table configuration from JSON file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            configs = json.load(f)
        
        location_config = configs.get(self.location_id)
        if not location_config:
            raise ValueError(f"No configuration found for location {self.location_id}")
            
        division_config = location_config.get(self.division)
        if not division_config:
            raise ValueError(f"No configuration found for division {self.division} at location {self.location_id}")
            
        return division_config
    
    def initialize_tables(self):
        """Initialize tables based on location and division configuration."""
        config = self.get_table_config()
        tableByeOffset = 0

        if self.bye_team_id:
            tableByeOffset = 1

        if len(config["table_ids"]) + tableByeOffset < self.num_teams // 2:
            raise ValueError(f"Not enough tables ({len(config['table_ids'])}) for {self.num_teams} teams")
        
        for table_key, table_id in zip(config["table_keys"], config["table_ids"]):
            self.tables[table_key] = Table(table_id)
    
    def initialize_team_names(self):
        """Initialize team name mapping from configuration."""
        config = self.get_table_config()
        if "team_ids" in config and "team_keys" in config:
            self.team_names = dict(zip(
                map(int, config["team_ids"]), 
                config["team_keys"]
            ))
        if "bye_team_id" in config:
            self.bye_team_id = config["bye_team_id"]
        else:   # Find index of "bye" in team_keys, case-insensitively
            self.bye_team_id = next((i for i, key in enumerate(config["team_keys"]) if key.lower() == "bye"), None)
    def get_team_name(self, team_id):
        """Get team name for a given team ID."""
        return self.team_names.get(team_id, str(team_id))
    
    def assign_all_tables(self):
        """Assign tables for all weeks in the schedule."""
        for week in self.schedule.weeks:
            week.assign_tables(self.tables)

    def read_schedule(self):
        """Read and parse the schedule CSV file."""
        teams = set()
        rows = []  # Store rows temporarily
        
        # First pass: collect all teams
        with open(self.filename, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) < 2 or row[1] == "No Play" or row[1] == "Playoff Week":
                    continue
                rows.append(row)  # Store valid rows
                week_id, date, *matches = row
                # Extract teams from matches
                for match in matches:
                    home, away = map(int, match.split('-'))
                    teams.add(home)
                    teams.add(away)
        
        # Set num_teams first
        self.num_teams = len(teams)
        if self.num_teams % 2 != 0:
            raise ValueError("Number of teams must be even (Do you need to add a bye?)")
        # Initialize usage counts for all teams on all tables

        # Second pass: create Week objects with correct num_teams
        for row in rows:
            week_id, date, *matches = row
            self.schedule.add_week(Week(week_id, date, matches, self.bye_team_id, self.num_teams))
        print(f"Schedule: {self.schedule}")
        return self.schedule


    def write_assignments(self):
        """Write table assignments to CSV file."""
        output_filename = self.filename.replace("Schedule.csv", "TableAssignments.csv")
        
        with open(output_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Week", "MatchDate", "Assignments"])
            
            for week in self.schedule.weeks:
                # Format assignments with team names
                assignments = ", ".join([
                    f"{self.get_team_name(match.home_team)}-{self.get_team_name(match.away_team)}: {match.assigned_table.table_id}"
                    for match in week.matches
                ])
                
                writer.writerow([week.week_id, week.date, assignments])

    def write_weekly_table_assignments(self):
        """Write weekly table assignments in team-column format."""
        output_filename = self.filename.replace("Schedule.csv", "TableStats.csv")
        
        # Get sorted list of team IDs and their names
        team_ids = sorted(self.team_names.keys())
        
        with open(output_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            # Write header row with team names
            header = ["", ""] + [self.get_team_name(team_id) for team_id in team_ids]
            writer.writerow(header)
            
            # Write each week's assignments
            for week in self.schedule.weeks:
                row = [week.week_id, week.date]
                
                # Initialize all teams' tables as empty for this week
                team_tables = ["" for _ in team_ids]
                
                # Fill in the tables for teams that play this week
                for match in week.matches:
                    # Find indices for home and away teams in our team_ids list
                    home_idx = team_ids.index(match.home_team)
                    away_idx = team_ids.index(match.away_team)
                    
                    # Add table assignments
                    team_tables[home_idx] = match.assigned_table.table_id
                    team_tables[away_idx] = match.assigned_table.table_id
                
                # Convert each table identifier to a string
                team_tables_as_strings = [f" {str(table)} " for table in team_tables]
                # Extend the row with the string-converted table identifiers
                row.extend(team_tables_as_strings)
                writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description="Assign tables to matches from a schedule CSV file.")
    parser.add_argument('filename', type=str, nargs='?', default="787-2025-01-705-02-Schedule.csv",
                       help='The schedule CSV file to process (default: 787-2025-01-705-02-Schedule.csv)')
    parser.add_argument('--config', type=str, default="configs/table_configs.json",
                       help='Path to table configuration JSON file')

    args = parser.parse_args()

    try:
        manager = TableAssignmentManager(args.filename, args.config)
        print(f"Location: {manager.location_id}, Division: {manager.division}")
        print(f"Using configuration from: {args.config}")
        print(f"Using tables: {[t.table_id for t in manager.tables.values()]}")
        print(f"Successfully loaded {len(manager.schedule.weeks)} weeks from schedule:")
        manager.assign_all_tables()
        manager.write_assignments()
        manager.write_weekly_table_assignments()
        print(f"Table assignments written to {args.filename.replace('Schedule.csv', 'TableAssignments.csv')}")
        print(f"Weekly table statistics written to {args.filename.replace('Schedule.csv', 'TableStats.csv')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
