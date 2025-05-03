import os
import urllib.parse
import requests
from datetime import datetime
from dotenv import load_dotenv

import google.generativeai as genai

from src.tts.google_tts import text_to_speech, play_audio

load_dotenv()

# API Keys
key = os.getenv("GRAPHHOPPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Gemini API key missing!")
    exit(1)

if not key:
    print("GraphHopper API key missing!")
    exit(1)

# Configure Gemini if available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

# Allowed modes
valid_modes = ['car', 'foot', 'bike', 'hike']

# Sharp turn detector
def detect_sharp_turn(curr, nxt):
    curr_text = curr["text"].lower()
    curr_dist = curr["distance"]
    next_dist = nxt["distance"] if nxt else 0
    is_sharp = "sharp" in curr_text or (curr_dist < 30 and next_dist > 100)

    if not is_sharp:
        return None
    if "left" in curr_text:
        return "⚠️↙️ SHARP LEFT"
    elif "right" in curr_text:
        return "⚠️↘️ SHARP RIGHT"
    return "⚠️↗️ SHARP TURN"

# AI Smart Tip
def generate_ai_tip(orig, dest, km, miles, hr, min, vehicle):
    now = datetime.now()
    context = {
        "from": orig['name'],
        "to": dest['name'],
        "distance_km": f"{km:.1f}",
        "distance_miles": f"{miles:.1f}",
        "duration": f"{hr}h {min}m",
        "vehicle": vehicle,
        "time_of_day": now.strftime("%H:%M"),
        "is_weekend": now.weekday() >= 5
    }

    prompt = f"""Generate ONE practical tip for this trip in under 15 words:
    {context}
    Format: "[Emoji] [Tip]"
         Examples:
         "⛽ Fuel up before rural stretch"
         "🚦 Avoid downtown until 19:00"
         "⚠️ 2 sharp turns next 5km" """

    try:
        response = model.generate_content(prompt)
        return response.text.strip('"')
    except:
        return "No smart tip generated."

# Navigation prompt enrich
def enrich_instruction(text, dist):
    prompt = (
    f"Rewrite this direction in more human-friendly language."
    f"If none fits, just keep it simple. '{text}' ({dist/1000:.1f} km). Max 10 words. "
    f"Example: 'Turn left at the traffic light' → 'Turn left at Starbucks'."
    )


    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return text + f" ({dist/1000:.1f} km)"


# Emoji for transport
vehicle_emojis = {
    'car': '🚗', 'bike': '🚲', 'foot': '🚶', 'hike': '🥾', 'default': '📍'
}

# Main Loop
while True:
    user_mode = input("Enter mode of transport (car, foot, bike, hike): ").strip().lower()
    vehicle = user_mode if user_mode in valid_modes else "car"
    if user_mode not in valid_modes:
        print("Invalid or empty input. Defaulting to 'car'.")

    start_city = input("Starting Location: ")
    end_city = input("Destination: ")

    # Geocoding
    geo_url = "https://graphhopper.com/api/1/geocode"
    start_url = f"{geo_url}?q={urllib.parse.quote(start_city)}&limit=1&key={key}"
    end_url = f"{geo_url}?q={urllib.parse.quote(end_city)}&limit=1&key={key}"
    start_data = requests.get(start_url).json()
    end_data = requests.get(end_url).json()

    if start_data["hits"] and end_data["hits"]:
        orig = start_data["hits"][0]
        dest = end_data["hits"][0]
        orig_coords = orig["point"]
        dest_coords = dest["point"]

        # Routing
        base_url = "https://graphhopper.com/api/1/route?"
        points = f"&point={orig_coords['lat']}%2C{orig_coords['lng']}&point={dest_coords['lat']}%2C{dest_coords['lng']}"
        paths_url = base_url + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + points

        response = requests.get(paths_url)
        paths_status = response.status_code
        paths_data = response.json()

        print("=================================================")
        print(f"Routing API Status: {paths_status}")
        print(f"Routing API URL:\n{paths_url}")
        print("=================================================")

        if paths_status == 200:
            instructions = paths_data["paths"][0]["instructions"]
            total_distance = paths_data["paths"][0]["distance"]
            total_time = paths_data["paths"][0]["time"]

            km = total_distance / 1000
            miles = km / 1.61
            seconds = total_time // 1000
            hr = seconds // 3600
            min = (seconds % 3600) // 60
            sec = seconds % 60

            print(f"{vehicle_emojis.get(vehicle, vehicle_emojis['default'])} Trip: {orig['name']} → {dest['name']} by {vehicle}")
            print(f"⏱ {hr:02d}:{min:02d}:{sec:02d} | 📏 {km:.1f} km / {miles:.1f} miles")
            print("━" * 40)

            for i in range(len(instructions)):
                step = instructions[i]
                next_step = instructions[i+1] if i+1 < len(instructions) else None
                sharp_turn = detect_sharp_turn(step, next_step)
                enriched = enrich_instruction(step["text"], step["distance"])
                prefix = sharp_turn + ": " if sharp_turn else "➡️ "
                direction = f"{prefix}{enriched}"
                print(direction)
                text_to_speech(direction, output_file="output.mp3")
                play_audio("output.mp3")
              
                print("=============================================")

            print("=================================================")
            print(f"Distance Traveled: {miles:.1f} miles / {km:.1f} km")
            print(f"Trip Duration: {hr:02d}:{min:02d}:{sec:02d}")
            print("=================================================")

            print("━" * 40)
            print("💡 Smart Tip:")
            print(generate_ai_tip(orig, dest, km, miles, hr, min, vehicle))
            print("━" * 40)
            break
        else:
            print("*************************************************")
            print("GraphHopper Routing API failed.")
            print("Message: " + paths_data.get("message", "Unknown error"))
            print("*************************************************")
    else:
        print("Invalid locations. Try again.\n")
