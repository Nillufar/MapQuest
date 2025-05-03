import os
import urllib.parse
import requests
from datetime import datetime
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Load environment variables
load_dotenv()

# API Keys
key = os.getenv("GRAPHHOPPER_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

if not key:
    print("GraphHopper API key missing!")
    exit(1)

# Configure Gemini if available
if GEMINI_AVAILABLE and gemini_key:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    GEMINI_AVAILABLE = False

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

def generate_ai_tip(orig, dest, km, miles, hr, min, vehicle):
    if not GEMINI_AVAILABLE:
        return "Gemini AI not available."

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
        # Log the prompt to verify its correctness
        print(f"Sending prompt to Gemini AI:\n{prompt}")
        
        response = model.generate_content(prompt)
        
        # Log the response for debugging
        print(f"Gemini AI Response: {response.text.strip()}")

        # Check if the response is valid or empty
        if not response.text.strip():
            return "No valid tip generated."
        
        return response.text.strip('"')
    except Exception as e:
        print(f"Error generating smart tip: {e}")
        return "No smart tip generated."

# Navigation prompt enrich
def enrich_instruction(text, dist):
    if not GEMINI_AVAILABLE:
        return text + f" ({dist/1000:.1f} km)"

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

    # Function to geocode a location and return JSON hit
    def get_coords(city):
        geo_url = "https://graphhopper.com/api/1/geocode"
        url = f"{geo_url}?q={urllib.parse.quote(city)}&limit=1&key={key}"
        try:
            resp = requests.get(url).json()
            if resp["hits"]:
                return resp["hits"][0]
            else:
                print(f"❌ Could not find: {city}")
                return None
        except Exception as e:
            print(f"🚨 Error fetching location '{city}': {e}")
            return None

    # Input origin and destination
    start_city = input("Starting Location: ")
    end_city = input("Destination: ")

    # Input waypoints
    waypoints = []
    print("Enter intermediate stops (leave blank to finish):")
    while True:
        stop = input("Stop: ").strip()
        if not stop:
            break
        waypoints.append(stop)

    # Collect and validate all locations
    all_cities = [start_city] + waypoints + [end_city]
    locations = [get_coords(city) for city in all_cities]

    if any(loc is None for loc in locations):
        print("❌ One or more locations were invalid. Please try again.")
        exit(1)

    # Define origin and destination
    orig = locations[0]  # The first location is the origin
    dest = locations[-1]  # The last location is the destination

    # Build routing URL for multiple points
    point_params = "".join([f"&point={loc['point']['lat']}%2C{loc['point']['lng']}" for loc in locations])
    route_base = "https://graphhopper.com/api/1/route?"
    paths_url = route_base + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + point_params

    # Display route stops (start, waypoints, destination)
    print("\n📍 Planned Route:")
    for i, loc in enumerate(locations):
        emoji = "🏁" if i == len(locations) - 1 else f"{i+1:>2}."
        print(f" {emoji} {loc['name']}")
        print("━" * 40)

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

            # Determine emoji based on instruction text
            text_lower = step["text"].lower()
            if "arrive" in text_lower or "destination" in text_lower:
                direction_emoji = "🏁 "  # Finish flag for arrival
            elif "left" in text_lower:
                direction_emoji = "⬅️ "  # Left arrow
            elif "right" in text_lower:
                direction_emoji = "➡️ "  # Right arrow
            elif "straight" in text_lower or "continue" in text_lower:
                direction_emoji = "⬆️ "  # Up arrow (for straight/continue)
            else:
                direction_emoji = "➡️ "  # Default (fallback)
            
            prefix = sharp_turn + ": " if sharp_turn else direction_emoji
            print(f"{prefix}{enriched}")
            print("=" * 45)  # Separator line

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
