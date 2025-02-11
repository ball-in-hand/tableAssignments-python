"""
Table Assignment Manager for League Schedules

This module handles reading and displaying league schedules from CSV files.
It parses schedule files named in the format: league-year-session-division-location-Schedule.csv
"""

import csv
import re
import argparse
import json
import os
import random
import math
from typing import List, Optional
from collections import defaultdict
from itertools import permutations

class Team:
    def __init__(self, team_id: int, team_value: str):
        self.team_id = team_id
        self.team_value = team_value
        self.tables_assigned: Optional[List[Table]] = None
    def __str__(self) -> str:
        """Return string representation of team."""
        return f"Team {self.team_id}: {self.team_value} ({self.tables_assigned})"

class Table:
    def __init__(self, table_id: int, table_value: str):
        self.table_id = table_id
        self.table_value = table_value
    def __str__(self) -> str:
        """Return string representation of table."""
        return f"Table {self.table_id}: {self.table_value}"

class Match:
    """Represents a match between two teams."""
    
    def __init__(self, home_team: Team, away_team: Team):
        """Initialize a match with home and away team IDs."""
        self.home_team = home_team
        self.away_team = away_team
        self.table_assigned: Optional[Table] = None
        self.candidate_tables: Optional[Table] = None

    def assign_table(self, table: Table):
        """Assign a table to the match."""
        self.table_assigned = table
        self.home_team.tables_assigned.append(table)
        self.away_team.tables_assigned.append(table)

    def assign_candidate_table(self, table: Table):
        """Assign a candidate table to the match."""
        self.candidate_tables.append(table)

    def remove_table(self):
        """Remove a table from the match."""
        self.table_assigned = None
        self.home_team.tables_assigned.pop()
        self.away_team.tables_assigned.pop()

    @classmethod
    def from_string(cls, match_str: str) -> 'Match':
        """Create a Match object from a string in format 'home-away'."""
        try:
            home, away = map(int, match_str.split('-'))
            return cls(home_team=home, away_team=away)
        except ValueError as e:
            raise ValueError(f"Invalid match format: {match_str}") from e

    def __str__(self) -> str:
        """Return string representation of match in format 'home-away'."""
        return f"{self.home_team}-{self.away_team}"

class Week:
    """Represents a week in the schedule containing multiple matches."""
    
    def __init__(self, week_id: int, date: str, matches: List[Match], bye_team_id: Optional[int]):
        """Initialize a week with its ID, date, matches, and optional bye team."""
        self.week_id = week_id
        self.weeks_total = 0
        self.date = date
        self.matches = matches
        self.bye_team_id = bye_team_id
        self.debug = True
        self.tables: Optional[List[Table]] = None

    def __str__(self) -> str:
        """Return string representation of week including date and matches."""
        match_str = ', '.join(str(m) for m in self.matches)
        return f"Week {self.week_id} ({self.date}): [{match_str}]"
    
    def set_weeks_total(self, weeks_total: int):
        """Set the total number of weeks in the schedule."""
        self.weeks_total = weeks_total
    
    def assign_tables(self, tables: List[Table]):
        print(f"\nAssigning tables for Week {self.week_id}")
        
        available_tables = tables.copy()
        print(f"Available tables at start: {[t.table_id for t in available_tables]}")
        
        if str(self.week_id) == "1":
            print("First week - random assignment")
            random.shuffle(available_tables)
            random.shuffle(self.matches)
            for match in self.matches:
                assigned_table = available_tables.pop()
                match.assign_table(assigned_table)
                print(f"Match {match.home_team}-{match.away_team} assigned to table {assigned_table.table_id}")
        else:
            success = self.assign_tables_to_matches(self.matches, available_tables)
            if not success:
                print("WARNING: Unable to find a valid table assignment for all matches!")

    def assign_tables_to_matches(self, matches: List[Match], available_tables: List[Table]) -> bool:
        """
        Find valid table assignments by checking all permutations against constraints.
        Returns True if a valid assignment is found, False otherwise.
        """
        # Calculate maximum times a team can use a table based on total weeks in schedule
        num_tables = len(available_tables)
        max_usage_per_table = math.ceil(self.weeks_total / num_tables)  # Round up division
        
        def reset_assignments():
            """Reset all table assignments for this week."""
            for match in matches:
                if match.table_assigned:
                    match.remove_table()

        def populate_match_candidate_tables(match_table_pairs):
            """
            1. Neither team should have played on this table last week
            """
         
            for match, proposed_table in match_table_pairs:
                # Check if either team played on this table last week
                if any(proposed_table == team.tables_assigned[-1] for team in [match.home_team, match.away_team] 
                      if team.tables_assigned):
                    return False
            
                match.assign_candidate_table(proposed_table)
            
            return True

        def get_permutations(table_permutations):
            """Try a sequence of table permutations."""
            for table_permutation in table_permutations:
                candidate_pairs = list(zip(matches, table_permutation))
                
                if populate_match_candidate_tables(candidate_pairs):
                    # Found a valid assignment
                    print(f"\nFound valid assignment: {candidate_pairs}")
                    return True
            return False

        print("\nFinding valid table assignments...")
        
        perms = list(permutations(available_tables, len(matches)))
        if get_permutations(perms):
            return True
            
        # Reset any assignments
        reset_assignments()
        return False

class Schedule:
    """Contains all weeks in a league-year-session-division schedule."""
    
    def __init__(self):
        """Initialize an empty schedule."""
        self.weeks = []
    
    def add_week(self, week: Week):
        """Add a week to the schedule."""
        self.weeks.append(week)
    
    def __str__(self) -> str:
        """Return string representation of entire schedule."""
        return "\n".join([str(week) for week in self.weeks])

class TableAssignmentManager:
    """Manages reading and displaying league schedules."""
    
    def __init__(self, filename: str = "787-2025-01-705-02-Schedule.csv", 
                 config_path: str = "configs/table_configs.json"):
        """
        Initialize the manager with schedule file and config.
        
        Args:
            filename: CSV file containing schedule (league-year-session-division-location-Schedule.csv)
            config_path: JSON file containing league configuration
        """
        self.debug = True
        self.filename = filename
        self.config_path = config_path
        self.schedule = Schedule()
        self.bye_team_id = None
        self.tables = []
        self.teams = []
        # Parse schedule filename components
        self.league_id, self.year, self.session, self.division, self.location_id = self.validate_filename()
        
        # Load configuration and schedule
        self.initialize_from_config()
        self.read_schedule()
    
    def validate_filename(self) -> tuple:
        """
        Validate and parse the schedule filename pattern.
        
        Returns:
            Tuple of (league_id, year, session, division, location_id)
        
        Raises:
            ValueError: If filename doesn't match expected pattern
        """
        pattern = r"(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-Schedule\.csv"
        match = re.match(pattern, self.filename)
        if not match:
            raise ValueError("Filename does not match the required pattern.")
        return match.groups()
    
    def initialize_from_config(self):
        """
        Initialize configuration from JSON file.
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If league or division config not found
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            configs = json.load(f)
        
        league_config = configs.get(self.league_id)
        if not league_config:
            raise ValueError(f"No configuration found for league {self.league_id}")
            
        division_config = league_config.get(self.division)
        if not division_config:
            raise ValueError(f"No configuration found for division {self.division}")
            
        self.bye_team_id = division_config.get("bye_team_id")
        # Convert table_values and team_values to objects
        self.tables = [Table(table_id, table_value) for table_id, table_value in zip(division_config.get("table_ids", []), division_config.get("table_values", []))]
        self.teams = [Team(team_id, team_value) for team_id, team_value in zip(division_config.get("team_ids", []), division_config.get("team_values", []))]
    
    def assign_all_tables(self):
        """Assign tables to all matches in the schedule and output results."""
        for week in self.schedule.weeks:
            week.set_weeks_total(len(self.schedule.weeks))
            week.assign_tables(self.tables)
            print(f"Week {week.week_id} assigned tables: {week.tables}")
        
        # Output results in TableStats format
        self.output_table_stats()

    def read_schedule(self) -> Schedule:
        """
        Read and parse the schedule CSV file.
        
        Returns:
            Schedule object containing all weeks and matches
        """
        with open(self.filename, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) < 2 or row[1] == "No Play" or row[1] == "Playoff Week":
                    continue
                week_id, date, *match_strings = row
                # Convert string matches to Match objects using existing Team objects
                matches = []
                for match_str in match_strings:
                    try:
                        home_id, away_id = map(str, match_str.split('-'))  # Convert to strings
                        home_team = next((team for team in self.teams if str(team.team_id) == home_id), None)
                        away_team = next((team for team in self.teams if str(team.team_id) == away_id), None)
                        
                        if home_team is None or away_team is None:
                            continue

                        matches.append(Match(home_team, away_team))
                    except Exception as e:
                        print(f"Error processing match {match_str}: {e}")
                self.schedule.add_week(Week(week_id, date, matches, self.bye_team_id))
        return self.schedule

    def output_table_stats(self):
        """
        Output table assignments in the same format as TableStats.csv.
        Creates a CSV file with week number, date, and table assignments for each team.
        """
        # Get team names in order from config
        team_names = [team.team_value for team in self.teams]
        
        # Create output filename based on input filename
        output_filename = self.filename.replace('Schedule.csv', 'TableStats.csv')
        
        with open(output_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header row
            writer.writerow(['', ''] + team_names)
            
            # Write data rows
            for week in self.schedule.weeks:
                row = [week.week_id, week.date]
                
                # For each team, find their assigned table for this week
                for team in self.teams:
                    # Find match where this team played
                    match = next((m for m in week.matches 
                                if m.home_team.team_id == team.team_id 
                                or m.away_team.team_id == team.team_id), None)
                    
                    if match and match.table_assigned:
                        row.append(match.table_assigned.table_value)
                    else:
                        row.append('')  # Empty cell if no table assigned
                
                writer.writerow(row)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Read and display schedule from CSV file.")
    parser.add_argument('filename', type=str, nargs='?', 
                       default="787-2025-01-705-02-Schedule.csv",
                       help='The schedule CSV file to process')
    parser.add_argument('--config', type=str, 
                       default="configs/table_configs.json",
                       help='Path to table configuration JSON file')

    args = parser.parse_args()

    try:
        manager = TableAssignmentManager(args.filename, args.config)
        print(f"League: {manager.league_id}, Year: {manager.year}, "
              f"Session: {manager.session}, Division: {manager.division}, "
              f"Location: {manager.location_id}")
        print(f"Using configuration from: {args.config}")
        manager.assign_all_tables()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
