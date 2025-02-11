import csv
from collections import defaultdict
import pandas as pd
import json
import re

def load_team_names(filename):
    """Load team names from config based on filename pattern."""
    pattern = r"(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-TableAssignments\.csv"
    match = re.match(pattern, filename)
    if not match:
        return {}
        
    location_id, _, _, division, _ = match.groups()
    
    try:
        with open("configs/table_configs.json", 'r') as f:
            configs = json.load(f)
            division_config = configs[location_id][division]
            return dict(zip(
                map(str, division_config["team_ids"]), 
                division_config["team_keys"]
            ))
    except:
        return {}

def analyze_table_stats(filename):
    """Analyze table assignments from the TableStats CSV format."""
    # Read the CSV file directly into a DataFrame
    df = pd.read_csv(filename)
    
    # Get team names (all columns except Week and MatchDate)
    team_names = df.columns[2:]
    
    # Initialize dictionary to store counts
    team_table_counts = defaultdict(lambda: defaultdict(int))
    
    # Process each row
    for _, row in df.iterrows():
        # Count table assignments for each team
        for team in team_names:
            if pd.notna(row[team]) and row[team] != '':  # Check if team played
                table = str(row[team])
                team_table_counts[team][table] += 1
    
    # Convert counts to DataFrame
    all_tables = sorted(set(
        table for counts in team_table_counts.values() 
        for table in counts.keys()
    ))
    
    # Create a list of rows for the DataFrame
    rows = []
    for team in sorted(team_table_counts.keys()):
        row = {'Team': team}
        for table in all_tables:
            row[f'Table {table}'] = team_table_counts[team][table]
        rows.append(row)
    
    # Create and return the DataFrame
    return pd.DataFrame(rows)

def main():
    filename = "787-2025-01-705-02-TableStats.csv"
    
    print("Analyzing table assignments...")
    results_df = analyze_table_stats(filename)
    
    # Calculate and add total games column
    results_df['Total Games'] = results_df.iloc[:, 1:].sum(axis=1)
    
    # Print results
    print("\nTable Assignment Statistics:")
    print("===========================")
    print(results_df.to_string(index=False))
    
    # Print summary statistics
    print("\nSummary Statistics:")
    print("=================")
    for table in results_df.columns[1:-1]:  # Exclude 'Team' and 'Total Games' columns
        print(f"\n{table}:")
        print(f"  Min: {results_df[table].min()} games")
        print(f"  Max: {results_df[table].max()} games")
        print(f"  Average: {results_df[table].mean():.2f} games")

if __name__ == "__main__":
    main() 