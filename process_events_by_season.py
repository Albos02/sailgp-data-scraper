import json
import os
import re
from pathlib import Path


def slugify(text):
    if not text:
        return "unknown"
    return re.sub(r"\W+", "_", text.lower()).strip("_")


def extract_leaderboard_items(leaderboard):
    if not leaderboard:
        return []
    items = leaderboard.get("items", [])
    results = []
    for item in items:
        team_info = item.get("team", {})
        fleet_data = item.get("fleetData", {})
        results.append(
            {
                "pos": item.get("position"),
                "prev_pos": item.get("previousPosition"),
                "team_code": team_info.get("code"),
                "team_name": team_info.get("name"),
                "pts": item.get("points"),
                "driver": item.get("helmsmanOverride") or item.get("helmFullName"),
                "country": fleet_data.get("country"),
                "regatta_points": fleet_data.get("regatta_points"),
                "regatta_rank": fleet_data.get("regatta_rank"),
                "season_points": fleet_data.get("season_points"),
                "season_rank": fleet_data.get("season_rank"),
                "split": fleet_data.get("split"),
            }
        )
    return results


def extract_location_data(location):
    if not location:
        return {"lat": None, "lon": None, "location_name": None}

    return {
        "lat": location.get("lat"),
        "lon": location.get("lon"),
        "location_name": location.get("locationName"),
    }


def clean_leaderboard(leaderboard):
    if not leaderboard:
        return []
    if all(
        not entry or all(v is None for v in entry.values()) for entry in leaderboard
    ):
        return []
    return leaderboard


def extract_race_days_data(entry):
    days = []
    for day in entry.get("raceDays", []):
        day_data = {
            "contentful_id": day.get("contentfulId"),
            "name": day.get("name"),
            "day_label": day.get("dayLabel"),
            "date": day.get("date"),
            "date_path": day.get("date_path"),
            "start_ts": day.get("start_ts"),
            "end_ts": day.get("end_ts"),
            "status": day.get("status"),
            "start_date_time": day.get("startDateTime"),
            "end_date_time": day.get("endDateTime"),
            "race_summary": day.get("raceSummary"),
            "leaderboard": extract_leaderboard_items(day.get("appLeaderboard")),
            "races": [],
        }
        for race in day.get("races", []):
            day_data["races"].append(
                {
                    "contentful_id": race.get("contentfulId"),
                    "name": race.get("name"),
                    "start_date_time": race.get("startDateTime"),
                    "end_date_time": race.get("endDateTime"),
                    "leaderboard": extract_leaderboard_items(
                        race.get("appLeaderboard")
                    ),
                }
            )
        days.append(day_data)
    return days


def clean_race_days_data(days):
    cleaned_days = []
    for day in days:
        day["leaderboard"] = clean_leaderboard(day.get("leaderboard", []))
        for race in day.get("races", []):
            race["leaderboard"] = clean_leaderboard(race.get("leaderboard", []))
        cleaned_days.append(day)
    return cleaned_days


def extract_comprehensive_data(file_path, season_num):
    with open(file_path, "r") as f:
        data = json.load(f)

    events_dict = {}

    for idx, entry in enumerate(data):
        leaderboard = entry.get("appLeaderboard", {})

        short_name_subtitle = entry.get("shortNameSubtitle", "")
        short_name = entry.get("shortName", "")
        location_name = entry.get("locationName", "")
        city_heading = (
            location_name
            or short_name
            or leaderboard.get("appNavHeading", "Unknown City")
        )
        event_key = slugify(city_heading)

        sponsor_info = leaderboard.get("appSponsor", {})
        location_data = extract_location_data(entry.get("location", {}))

        items = leaderboard.get("items", [])
        winner_info = None
        if items and items[0].get("position") == 1:
            first_item = items[0]
            winner_team = first_item.get("team", {})
            helm_name = (
                first_item.get("helmFullName")
                or first_item.get("helmsmanOverride")
                or first_item.get("fleetData", {}).get("driver_full_name")
            )
            if not helm_name:
                for athlete in winner_team.get("athletes", []):
                    if athlete.get("isHelm"):
                        helm_name = athlete.get("name")
                        break
            winner_info = {
                "team_code": winner_team.get("code"),
                "team_name": winner_team.get("name"),
                "helm_name": helm_name,
            }

        sponsor = None
        if sponsor_info and sponsor_info.get("name"):
            sponsor = {
                "name": sponsor_info.get("name"),
                "url": sponsor_info.get("url"),
                "logo_url": sponsor_info.get("logo", {}).get("file", {}).get("url")
                if sponsor_info.get("logo")
                else None,
            }

        event_data = {
            "event_id": entry.get("contentfulId"),
            "event_number": entry.get("eventNumber", idx + 1),
            "event_season": entry.get("eventSeason"),
            "event_name": entry.get("name") or leaderboard.get("heading"),
            "short_name": short_name,
            "short_name_subtitle": short_name_subtitle,
            "event_label": entry.get("eventLabel"),
            "broadcast_tab_name": entry.get("broadcastTabName"),
            "city": city_heading,
            "country": entry.get("countryName"),
            "country_code": entry.get("countryAbbreviation"),
            "dates": {
                "start": entry.get("startDateTime"),
                "end": entry.get("endDateTime"),
            },
            "location": location_data,
            "sponsor": sponsor,
            "is_live_event": leaderboard.get("isLiveEvent", False),
            "regatta_id": entry.get("regattaId"),
            "website_url": entry.get("websiteUrl"),
            "tickets_url": entry.get("ticketsUrl"),
            "ticket_available_state": entry.get("ticketAvailableState"),
            "introduction": entry.get("introduction"),
            "winner": winner_info,
            "pre_race_summary": entry.get("preRaceSummary"),
            "post_race_summary": entry.get("postRaceSummary"),
            "leaderboard_info": entry.get("leaderboardInfo"),
            "contentful_type": entry.get("contentfulType"),
            "created": entry.get("created"),
            "updated": entry.get("updated"),
            "results_summary": extract_leaderboard_items(leaderboard),
            "days": clean_race_days_data(extract_race_days_data(entry)),
            "teams": {},
        }

        teams_to_process = [
            item["team"] for item in leaderboard.get("items", []) if item.get("team")
        ]
        for team_info in teams_to_process:
            code = team_info.get("code", "UNK")
            if code in event_data["teams"]:
                continue

            crew = []
            for a in team_info.get("athletes", []):
                if not isinstance(a, dict):
                    continue
                biography = a.get("biographyPage", {}).get("components", [{}])[0]
                crew.append(
                    {
                        "contentful_id": a.get("contentfulId"),
                        "athlete_id": a.get("athleteId"),
                        "name": a.get("name"),
                        "first_name": a.get("firstName"),
                        "last_name": a.get("lastName"),
                        "role": a.get("role"),
                        "is_helm": a.get("isHelm"),
                        "dob": a.get("dateOfBirth"),
                        "hometown": a.get("hometown"),
                        "hometown_label": a.get("hometownLabel"),
                        "height": a.get("height"),
                        "weight": a.get("weight"),
                        "nationality": a.get("nationality"),
                        "profile_url": biography.get("url"),
                        "biography": a.get("careerHistory", {}).get("content")
                        if isinstance(a.get("careerHistory"), dict)
                        else a.get("careerHistory"),
                        "socials": {
                            "facebook": a.get("facebook"),
                            "instagram": a.get("instagram"),
                            "twitter": a.get("twitter"),
                        },
                        "photo_url": a.get("photo", {}).get("file", {}).get("url")
                        if a.get("photo")
                        else None,
                        "profile_photo_url": a.get("profilePhoto", {})
                        .get("file", {})
                        .get("url")
                        if a.get("profilePhoto")
                        else None,
                    }
                )

            event_data["teams"][code] = {
                "contentful_id": team_info.get("contentfulId"),
                "code": code,
                "name": team_info.get("name"),
                "full_name": team_info.get("fullName"),
                "is_active": team_info.get("isActive"),
                "boat_id": team_info.get("dataBoatId"),
                "order": team_info.get("order"),
                "sim_data": {
                    "color": team_info.get("simColour"),
                    "flag_url": team_info.get("simFlag", {}).get("file", {}).get("url")
                    if team_info.get("simFlag")
                    else None,
                },
                "colors": {
                    "hex": team_info.get("hexColor"),
                    "primary": team_info.get("primaryTeamHexColour"),
                    "secondary": team_info.get("secondaryTeamHexColour"),
                    "tertiary": team_info.get("tertiaryTeamHexColour"),
                    "text": team_info.get("textColor"),
                },
                "urls": {
                    "team": team_info.get("url"),
                    "logo": team_info.get("logo", {}).get("file", {}).get("url")
                    if team_info.get("logo")
                    else None,
                    "wordmark": team_info.get("wordmark", {}).get("file", {}).get("url")
                    if team_info.get("wordmark")
                    else None,
                    "team_photo": team_info.get("teamPhoto", {})
                    .get("file", {})
                    .get("url")
                    if team_info.get("teamPhoto")
                    else None,
                    "flag": team_info.get("leaderboardFlag", {})
                    .get("file", {})
                    .get("url")
                    if team_info.get("leaderboardFlag")
                    else None,
                    "app_flag": team_info.get("appCountryFlag", {})
                    .get("file", {})
                    .get("url")
                    if team_info.get("appCountryFlag")
                    else None,
                },
                "socials": {
                    "facebook": team_info.get("facebookUrl"),
                    "instagram": team_info.get("instagramUrl"),
                    "twitter": team_info.get("twitterUrl"),
                    "youtube": team_info.get("youTubeUrl"),
                    "linkedin": team_info.get("linkedInUrl"),
                },
                "crew": crew,
            }

        event_data["num_teams"] = len(event_data["teams"])
        event_data["num_crew"] = sum(
            len(t["crew"]) for t in event_data["teams"].values()
        )
        event_data["num_days"] = len(event_data["days"])

        events_dict[event_key] = event_data

    return events_dict


final_dict = {}
for i in range(1, 7):
    path = f"races-info/season_{i}.json"
    if os.path.exists(path):
        final_dict[f"season{i}"] = {
            "season_number": i,
            "events": extract_comprehensive_data(path, i),
        }

with open("races-data.json", "w") as f:
    json.dump(final_dict, f, indent=2)

print(f"Created races-data.json with {len(final_dict)} seasons")

for season_key, season_data in final_dict.items():
    num_events = len(season_data.get("events", {}))
    total_teams = sum(
        len(e.get("teams", {})) for e in season_data.get("events", {}).values()
    )
    total_crew = sum(
        e.get("num_crew", 0) for e in season_data.get("events", {}).values()
    )
    print(
        f"{season_key}: {num_events} events, {total_teams} teams, {total_crew} crew members"
    )
