import csv
import re
import argparse
from collections import defaultdict, deque
import itertools

def parse_filename(filename):
    # Validate and parse the filename
    pattern = r"(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-Schedule\.csv"
    match = re.match(pattern, filename)
    if not match:
        raise ValueError("Filename does not match the required pattern.")
    return match.groups()

def read_schedule(filename):
    schedule = []
    with open(filename, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) < 2 or row[1] == "No Play":
                continue
            schedule.append(row)
    return schedule

def assign_tables(schedule):
    global table_usage_count, table_history
    table_pairs = ["1-2", "3-4", "5-6", "7-8"]
    table_usage_count = defaultdict(lambda: defaultdict(int))
    table_history = defaultdict(lambda: deque(maxlen=20))
    assignments = []

    while schedule:
        week = schedule.pop(0)
        week_number, match_date, *matches = week
        week_assignments = {}
        available_tables = table_pairs.copy()
        available_tables_combo = itertools.combinations(available_tables, len(matches))
        used_table = None

        # Try different table assignments
        for match in matches:
            print(match)
            if (used_table): 
                available_tables_combo.remove(used_table)
            for combo in available_tables_combo:
                for table in combo:
                    print(table)
                    home_team, away_team = match.split('-')
                    if ((len(table_history[home_team]) == 0 or table != table_history[home_team][-1]) and
                        (len(table_history[away_team]) == 0 or table != table_history[away_team][-1]) and
                        (abs(table_usage_count[home_team][table] - table_usage_count[away_team][table]) <= 3)):
                        week_assignments[match] = table
                        table_usage_count[home_team][table] += 1
                        table_usage_count[away_team][table] += 1
                        table_history[home_team].append(table)
                        table_history[away_team].append(table)
                        used_table = table
                        break
            # Only append if all matches for the week are successfully assigned
            assignments.append((week_number, match_date, week_assignments))
            print(assignments)
    return assignments

def write_assignments(filename, assignments):
    output_filename = filename.replace("Schedule.csv", "TableAssignments.csv")
    with open(output_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Week", "MatchDate", "Assignments"])
        for week_number, match_date, week_assignments in assignments:
            assignment_str = "; ".join([f"{match}: {table}" for match, table in week_assignments.items()])
            writer.writerow([week_number, match_date, assignment_str])

def main():
    parser = argparse.ArgumentParser(description="Assign tables to matches from a schedule CSV file.")
    parser.add_argument('filename', type=str, nargs='?', default="787-2025-01-705-02-Schedule.csv",
                        help='The schedule CSV file to process (default: 787-2025-01-705-02-Schedule.csv)')

    args = parser.parse_args()

    try:
        parse_filename(args.filename)
        schedule = read_schedule(args.filename)
        assignments = assign_tables(schedule)
        write_assignments(args.filename, assignments)
        print(f"Table assignments written to {args.filename.replace('Schedule.csv', 'TableAssignments.csv')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()