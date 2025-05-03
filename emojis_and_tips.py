import os
import urllib.parse
import requests

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set your GraphHopper API key (or use an environment variable)
key = os.getenv("GRAPHHOPPER_API_KEY")
if not key:
    print("API Key is missing!")
    exit(1)

# Allowed transportation modes
valid_modes = ['car', 'foot', 'bike', 'hike']

while True:
    # Ask user for travel mode
    user_mode = input("Enter mode of transport (car, foot, bike, hike): ").strip().lower()
    if user_mode not in valid_modes:
        print("Invalid or empty input. Defaulting to 'car'.")
        vehicle = "car"
    else:
        vehicle = user_mode

    # Get starting and destination locations
    start_city = input("Starting Location: ")
    end_city = input("Destination: ")

    # Use GraphHopper's geocoding API to get coordinates
    geocode_url = "https://graphhopper.com/api/1/geocode"
    start_url = f"{geocode_url}?q={urllib.parse.quote(start_city)}&limit=1&key={key}"
    end_url = f"{geocode_url}?q={urllib.parse.quote(end_city)}&limit=1&key={key}"

    start_data = requests.get(start_url).json()
    end_data = requests.get(end_url).json()

    if start_data["hits"] and end_data["hits"]:
        orig = start_data["hits"][0]
        dest = end_data["hits"][0]
        orig_coords = orig["point"]
        dest_coords = dest["point"]

        # Build routing URL with selected vehicle
        op = f"&point={orig_coords['lat']}%2C{orig_coords['lng']}"
        dp = f"&point={dest_coords['lat']}%2C{dest_coords['lng']}"
        base_url = "https://graphhopper.com/api/1/route?"
        paths_url = base_url + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + op + dp

        response = requests.get(paths_url)
        paths_status = response.status_code
        paths_data = response.json()

        print("=================================================")
        print(f"Routing API Status: {paths_status}")
        print(f"Routing API URL:\n{paths_url}")
        print("=================================================")

        if paths_status == 200:
            print(f"Directions from {orig['name']} to {dest['name']} by {vehicle}")
            print("=================================================")

            for step in paths_data["paths"][0]["instructions"]:
                text = step["text"]
                dist = step["distance"]
                print(f"{text} ( {dist/1000:.1f} km / {dist/1000/1.61:.1f} miles )")
                print("=============================================")

            # Calculate total distance and duration
            total_distance = paths_data["paths"][0]["distance"]
            total_time = paths_data["paths"][0]["time"]  # in milliseconds
            miles = total_distance / 1000 / 1.61
            km = total_distance / 1000
            seconds = total_time // 1000
            hr = seconds // 3600
            min = (seconds % 3600) // 60
            sec = seconds % 60

            print("=================================================")
            print(f"Distance Traveled: {miles:.1f} miles / {km:.1f} km")
            print(f"Trip Duration: {hr:02d}:{min:02d}:{sec:02d}")
            print("=================================================")
            break

        else:
            print("*************************************************")
            print("GraphHopper Routing API failed to return a valid route.")
            print("Error message: " + paths_data.get("message", "Unknown error"))
            print("*************************************************")
            print("Please enter valid locations again.\n")

    else:
        print("One or both locations could not be found. Try again.\n")


# ===== ENHANCED NAVIGATION ADDON =====
try:
    import google.generativeai as genai
    from datetime import datetime

    # Configure AI
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Improved sharp turn detection
    def detect_sharp_turn(instruction, next_instruction):
        """Detect sharp turns using distance and direction patterns"""
        curr_text = instruction["text"].lower()
        curr_dist = instruction["distance"]
        next_dist = next_instruction["distance"] if next_instruction else 0
        
        # Conditions for sharp turn:
        # 1. Contains "sharp" in text OR
        # 2. Very short segment (<30m) between longer segments
        is_sharp = ("sharp" in curr_text) or (curr_dist < 30 and next_dist > 100)
        
        if not is_sharp:
            return None
            
        if "left" in curr_text:
            return "⚠️↙️ SHARP LEFT"
        elif "right" in curr_text:
            return "⚠️↘️ SHARP RIGHT"
        return "⚠️↗️ SHARP TURN"

    # Generate AI tip with context
    def generate_ai_tip():
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
        
        response = model.generate_content(prompt)
        return response.text.strip('"')

    if paths_status == 200:
        instructions = paths_data["paths"][0]["instructions"]
        
        # Vehicle-specific emoji mapping
        vehicle_emojis = {
            'car': '🚗',      # Car emoji
            'bike': '🚲',     # Bicycle emoji
            'foot': '🚶',     # Walking person emoji
            'hike': '🥾',     # Hiking boot emoji
            'default': '📍'   # Default pin emoji
        }

        # Get the appropriate emoji for the vehicle
        vehicle_emoji = vehicle_emojis.get(vehicle.lower(), vehicle_emojis['default'])

        # Print header with respectful vehicle emoji
        print(f"\n{vehicle_emoji} Trip: {orig['name']} → {dest['name']} by {vehicle}")
        print(f"⏱ {hr:02d}:{min:02d}:{sec:02d} | 📏 {km:.1f} km / {miles:.1f} miles")
        print("━" * 40)
        
        # Display route with turn warnings
        for i in range(len(instructions)):
            current = instructions[i]
            next_instr = instructions[i+1] if i < len(instructions)-1 else None
            
            sharp_turn = detect_sharp_turn(current, next_instr)
            dist_km = current["distance"]/1000
            dist_miles = dist_km/1.61
            
            if sharp_turn:
                print(f"{sharp_turn}: {current['text']} ({dist_km:.1f} km / {dist_miles:.1f} miles)")
            else:
                direction = "↗️" if i == 0 else "➡️"  # Start arrow for first instruction
                print(f"{direction} {current['text']} ({dist_km:.1f} km / {dist_miles:.1f} miles)")

        # Generate and display tip
        try:
            print("━" * 40)
            print("💡 Smart Tip:")
            print(generate_ai_tip())
            print("━" * 40)
        except Exception as e:
            print(f"⚠️ Couldn't generate tip: {str(e)}")

except ImportError:
    print("\nℹ️ Install for smart features: pip install google-generativeai")
except Exception as e:
    print(f"\n⚠️ Enhancement error: {str(e)}")