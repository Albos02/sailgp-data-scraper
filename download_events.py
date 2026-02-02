import requests
import os
import time
import json
from datetime import datetime

with open("races-data.json", "r") as f:
    RAW_DATA = json.load(f)


def iso_to_unix_ms(iso_str):
    if not iso_str:
        return 0
    dt = datetime.fromisoformat(iso_str)
    return int(dt.timestamp() * 1000)


def select_from_list(options, prompt_text, show_count=False):
    print(f"\n--- {prompt_text} ---")
    max_length = max(len(k) for k in options.keys())
    for k, v in options.items():
        length = len(k)
        if show_count and "count" in v:
            # print(f"[{k}] {v['name']} ({v['count']} races)")
            print(
                " " * (max_length - length)
                + "["
                + k
                + "]"
                + " "
                + v["name"]
                + " ("
                + v["count"]
                + " "
                + "races)"
            )
        else:
            # print(f"[{k}]  {v['name']}")
            print(" " * (max_length - length) + "[" + k + "]" + " " + v["name"])
    print(" " * (max_length - 1) + "[A] " + "All")

    choice = input("\nSelect IDs (e.g. 1,3 or 1-2) or 'A': ").strip().upper()

    if choice == "A":
        return list(options.values())

    selected = []
    try:
        indices = []
        parts = [p.strip() for p in choice.split(",")]
        for part in parts:
            if "-" in part:
                start, end = map(int, part.split("-"))
                indices.extend([str(i) for i in range(start, end + 1)])
            else:
                indices.append(part)

        for idx in indices:
            if idx in options:
                selected.append(options[idx])
    except ValueError:
        print("Invalid input format.")

    return selected


def run_download(race_info):
    path = f"data/{race_info['season']}/{race_info['city']}/day_{race_info['day_num']}/{race_info['race_folder']}"
    os.makedirs(path, exist_ok=True)

    current_ts = race_info["start_ts"]
    end_ts = race_info["end_ts"]
    date_path = race_info["date_path"]

    print(f"\n📍 Event: {race_info['event_name']}")
    print(f"🏙️  City: {race_info['event_city']}")
    print(f"🗓️  Season: {race_info['season'].replace('_', ' ').title()}")
    print(f"🏁 Race: {race_info['race_name']}")
    print(f"📂 Path: {path}")

    downloaded = 0
    while current_ts <= end_ts:
        url = f"https://d3q91bfyfm610o.cloudfront.net/{date_path}/{current_ts}/RaceData.json"
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                with open(f"{path}/{current_ts}.json", "w") as f:
                    f.write(res.text)
                downloaded += 1
                print(f"  📥 Packets: {downloaded}", end="\r")
        except Exception:
            break

        current_ts += 500
        time.sleep(0.02)

    return downloaded


def main():
    seasons_available = {
        str(i + 1): {"id": s, "name": s.replace("_", " ").title()}
        for i, s in enumerate(RAW_DATA.keys())
    }

    selected_seasons = select_from_list(seasons_available, "SELECT SEASON(S)")
    if not selected_seasons:
        return

    event_options = {}
    event_idx = 1
    for season in selected_seasons:
        season_id = season["id"]
        season_data = RAW_DATA.get(season_id, {})
        events = season_data.get("events", {})
        for event_id, event_data in events.items():
            race_count = sum(
                len(day.get("races", [])) for day in event_data.get("days", [])
            )
            event_name = event_data.get("event_name", event_data.get("city", event_id))
            event_short_name = event_data.get(
                "short_name", event_data.get("city", event_id)
            )
            event_city = event_data.get("city", event_data.get("event_name", event_id))
            season_num = season_id.replace("season", "")
            event_options[str(event_idx)] = {
                "id": event_id,
                "name": f"{season['name']}  |  {event_short_name}  -  {event_city}",
                "season": season_id,
                "city": event_id,
                "race_count": race_count,
                "event_data": event_data,
            }
            event_idx += 1

    selected_events = select_from_list(
        event_options, "SELECT EVENT(S)", show_count=True
    )
    if not selected_events:
        return

    races_to_download = []
    for event in selected_events:
        season_id = event["season"]
        event_id = event["id"]
        event_data = event["event_data"]
        event_name = event_data.get("event_name", event_data.get("city", event_id))
        event_city = event_data.get("city", event_data.get("event_name", event_id))

        for d_idx, day in enumerate(event_data.get("days", []), 1):
            for race in day.get("races", []):
                race_start = race.get("start_date_time", race.get("start"))
                date_path = day.get("date_path") or (
                    day.get("date") or (race_start[:10] if race_start else "")
                )[:10].replace("-", "")
                races_to_download.append(
                    {
                        "event_name": event_name,
                        "event_city": event_city,
                        "season": season_id,
                        "race_name": race["name"],
                        "race_folder": race["name"].lower().replace(" ", "_"),
                        "city": event_id,
                        "day_num": d_idx,
                        "date_path": date_path,
                        "start_ts": iso_to_unix_ms(race_start),
                        "end_ts": iso_to_unix_ms(
                            race.get("end_date_time", race.get("end"))
                        ),
                    }
                )

    if races_to_download:
        print(
            f"\n📦 Queueing {len(races_to_download)} races from {len(selected_events)} event(s)..."
        )
        total_downloaded = 0
        for race in races_to_download:
            downloaded = run_download(race)
            total_downloaded += downloaded
        print(f"\n\n✨ All downloads complete. Total packets: {total_downloaded}")


if __name__ == "__main__":
    main()
