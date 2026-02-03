import json
import os
from pathlib import Path
from datetime import datetime, timezone


def load_races_data():
    with open("races-data.json", "r") as f:
        return json.load(f)


def normalize_race_name(name):
    if not name:
        return ""
    return name.lower().replace("-", " ").replace("_", " ").strip()


def get_all_expected_races(races_data):
    expected_races = []
    for season_key, season_data in races_data.items():
        if "events" not in season_data:
            continue
        for event_key, event_data in season_data["events"].items():
            if "days" not in event_data:
                continue
            for day in event_data["days"]:
                if "races" not in day:
                    continue
                for race in day["races"]:
                    expected_races.append(
                        {
                            "season": season_key,
                            "event": event_key,
                            "race_name": race.get("name"),
                            "race_name_normalized": normalize_race_name(
                                race.get("name")
                            ),
                            "start_date_time": race.get("start_date_time"),
                            "contentful_id": race.get("contentful_id"),
                        }
                    )
    return expected_races


def get_all_downloaded_races(data_dir):
    downloaded_races = []
    for season_folder in sorted(os.listdir(data_dir)):
        season_path = os.path.join(data_dir, season_folder)
        if not os.path.isdir(season_path):
            continue
        for event_folder in sorted(os.listdir(season_path)):
            event_path = os.path.join(season_path, event_folder)
            if not os.path.isdir(event_path):
                continue
            for day_folder in sorted(os.listdir(event_path)):
                day_path = os.path.join(event_path, day_folder)
                if not os.path.isdir(day_path):
                    continue
                for race_folder in sorted(os.listdir(day_path)):
                    race_path = os.path.join(day_path, race_folder)
                    if not os.path.isdir(race_path):
                        continue
                    downloaded_races.append(
                        {
                            "season": season_folder,
                            "event": event_folder,
                            "race_folder": race_folder,
                            "race_folder_normalized": normalize_race_name(race_folder),
                            "full_path": race_path,
                        }
                    )
    return downloaded_races


def parse_datetime_to_timestamp(start_date_time):
    if not start_date_time:
        return None
    try:
        dt = datetime.fromisoformat(start_date_time.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def get_first_file_info(race_path):
    files = sorted([f for f in os.listdir(race_path) if f.endswith(".json")])
    if not files:
        return None, None, None, None
    first_file = files[0]
    last_file = files[-1]
    try:
        first_timestamp = int(first_file.replace(".json", ""))
        last_timestamp = int(last_file.replace(".json", ""))
        return first_file, first_timestamp, last_file, last_timestamp
    except ValueError:
        return first_file, None, last_file, None


def check_boat_status_in_file(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            race_status = data[0].get("raceStatus", {})
            boat_statuses = data[0].get("boatStatuses", [])
            if boat_statuses:
                return boat_statuses[0].get("boatStatus", "Unknown")
            return race_status.get("status", "Unknown")
    except Exception as e:
        return f"Error: {e}"
    return "No data"


def main():
    data_dir = "data"
    races_data = load_races_data()

    expected_races = get_all_expected_races(races_data)
    downloaded_races = get_all_downloaded_races(data_dir)

    print("=" * 80)
    print("SAILGP DATA SCRAPER - FEEDBACK REPORT")
    print("=" * 80)

    total_expected = len(expected_races)
    total_downloaded = len(downloaded_races)

    print(f"\nTotal races expected from races-data.json: {total_expected}")
    print(f"Total race folders downloaded: {total_downloaded}")

    events_in_data = set()
    for race in downloaded_races:
        events_in_data.add((race["season"], race["event"]))

    expected_events = set()
    for race in expected_races:
        expected_events.add((race["season"], race["event"]))

    events_downloaded = len(events_in_data)
    events_expected = len(expected_events)
    event_completion_pct = (
        (events_downloaded / events_expected * 100) if events_expected > 0 else 0
    )

    print(f"\n--- EVENT COMPLETION ---")
    print(f"Expected events: {events_expected}")
    print(f"Downloaded events: {events_downloaded}")
    print(f"Event completion: {event_completion_pct:.1f}%")

    ok_events = []
    incomplete_events = []

    for season, event in expected_events:
        event_key = f"{season}/{event}"
        event_races = [
            r for r in expected_races if r["season"] == season and r["event"] == event
        ]
        expected_event_race_names_norm = set(
            r["race_name_normalized"] for r in event_races
        )

        downloaded_event_races = [
            r for r in downloaded_races if r["season"] == season and r["event"] == event
        ]
        downloaded_event_race_names_norm = set(
            r["race_folder_normalized"] for r in downloaded_event_races
        )

        missing_races_norm = (
            expected_event_race_names_norm - downloaded_event_race_names_norm
        )
        extra_races_norm = (
            downloaded_event_race_names_norm - expected_event_race_names_norm
        )

        missing_races = []
        for norm_name in missing_races_norm:
            race_info = next(
                (r for r in event_races if r["race_name_normalized"] == norm_name), None
            )
            if race_info:
                missing_races.append(race_info["race_name"])

        extra_races = []
        for norm_name in extra_races_norm:
            race_info = next(
                (
                    r
                    for r in downloaded_event_races
                    if r["race_folder_normalized"] == norm_name
                ),
                None,
            )
            if race_info:
                extra_races.append(race_info["race_folder"])

        if not missing_races and not extra_races:
            ok_events.append(event_key)
        else:
            incomplete_events.append(
                {
                    "event": event_key,
                    "missing": missing_races,
                    "extra": extra_races,
                }
            )

    print(f"\n--- RACE FOLDER COMPLETION ---")
    race_folder_pct = (
        (total_downloaded / total_expected * 100) if total_expected > 0 else 0
    )
    print(
        f"Race folders present: {race_folder_pct:.1f}% ({total_downloaded}/{total_expected})"
    )

    if incomplete_events:
        print("\nIncomplete events (missing or extra races):")
        for evt in incomplete_events:
            print(f"\n  {evt['event']}:")
            if evt["missing"]:
                print(f"    Missing races: {', '.join(evt['missing'])}")
            if evt["extra"]:
                print(f"    Extra race folders: {', '.join(evt['extra'])}")

    print("\n" + "=" * 80)
    print("DETAILED RACE VALIDATION")
    print("=" * 80)

    incomplete_races = []
    ok_races = []
    error_races = []

    for race in downloaded_races:
        race_path = race["full_path"]
        season = race["season"]
        event = race["event"]
        race_folder = race["race_folder"]
        race_folder_norm = race["race_folder_normalized"]

        expected_race_info = next(
            (
                r
                for r in expected_races
                if r["season"] == season
                and r["event"] == event
                and r["race_name_normalized"] == race_folder_norm
            ),
            None,
        )

        if not expected_race_info:
            error_races.append(
                {
                    "season": season,
                    "event": event,
                    "race": race_folder,
                    "issue": "No matching race in races-data.json",
                }
            )
            continue

        start_time_str = expected_race_info["start_date_time"]
        expected_timestamp = parse_datetime_to_timestamp(start_time_str)
        first_file_name, file_timestamp, last_file_name, last_file_timestamp = (
            get_first_file_info(race_path)
        )

        if not first_file_name:
            incomplete_races.append(
                {
                    "season": season,
                    "event": event,
                    "race": race_folder,
                    "issues": ["No JSON files found"],
                    "boat_status": "Unknown",
                    "timestamp": None,
                    "expected_timestamp": expected_timestamp,
                }
            )
            continue

        first_file_path = os.path.join(race_path, first_file_name)
        first_boat_status = check_boat_status_in_file(first_file_path)

        if not last_file_name:
            incomplete_races.append(
                {
                    "season": season,
                    "event": event,
                    "race": race_folder,
                    "issues": ["No last file found"],
                    "boat_status": first_boat_status,
                    "timestamp": file_timestamp,
                    "expected_timestamp": expected_timestamp,
                }
            )
            continue

        last_file_path = os.path.join(race_path, last_file_name)
        last_boat_status = check_boat_status_in_file(last_file_path)

        checks_passed = True
        issues = []

        if expected_timestamp and file_timestamp:
            if abs(expected_timestamp - file_timestamp) > 1000:
                issues.append(
                    f"First file timestamp mismatch: expected {expected_timestamp}, got {file_timestamp}"
                )
                checks_passed = False

        if last_boat_status != "Terminated":
            issues.append(
                f"Last file first boatStatus is '{last_boat_status}' (expected 'Terminated')"
            )
            checks_passed = False

        if checks_passed:
            ok_races.append(
                {
                    "season": season,
                    "event": event,
                    "race": race_folder,
                    "boat_status": last_boat_status,
                    "timestamp": file_timestamp,
                }
            )
        else:
            if not issues:
                issues.append("Unknown validation issue")
            incomplete_races.append(
                {
                    "season": season,
                    "event": event,
                    "race": race_folder,
                    "issues": issues,
                    "boat_status": last_boat_status,
                    "timestamp": file_timestamp,
                    "expected_timestamp": expected_timestamp,
                }
            )

    print(f"\n--- RACE DATA VALIDATION ---")
    print(f"OK races: {len(ok_races)}")
    print(f"Invalid races: {len(incomplete_races)}")
    print(f"Error races (no match in data): {len(error_races)}")

    if incomplete_races:
        print("\n--- INVALID RACES ---")
        for race in incomplete_races:
            print(f"\n{race['season']}/{race['event']}/{race['race']}:")
            issues = race.get("issues", ["Unknown issue"])
            for issue in issues:
                print(f"  - {issue}")
            boat_status = race.get("boat_status", "Unknown")
            print(f"  Last file first boatStatus: {boat_status}")
            expected_ts = race.get("expected_timestamp")
            if expected_ts:
                print(f"  Expected timestamp: {expected_ts}")
            file_ts = race.get("timestamp")
            if file_ts:
                print(f"  File timestamp: {file_ts}")

    if error_races:
        print("\n--- ERROR RACES (no matching data) ---")
        for race in error_races:
            print(f"  {race['season']}/{race['event']}/{race['race']}: {race['issue']}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(
        f"Event completion: {event_completion_pct:.1f}% ({events_downloaded}/{events_expected})"
    )
    print(
        f"Race folder completion: {race_folder_pct:.1f}% ({total_downloaded}/{total_expected})"
    )
    valid_races = len(ok_races)
    invalid_races = len(incomplete_races)
    total_validated = valid_races + invalid_races
    valid_race_pct = (valid_races / total_validated * 100) if total_validated > 0 else 0
    print(f"Valid race data: {valid_race_pct:.1f}% ({valid_races}/{total_validated})")
    print(f"Incomplete/Invalid races: {invalid_races}")

    if incomplete_races:
        print("\nIncomplete races list:")
        for race in incomplete_races:
            print(f"  - {race['season']}/{race['event']}/{race['race']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
