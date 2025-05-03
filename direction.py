import os
import urllib.parse
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
key = os.getenv("GRAPHHOPPER_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

if not key or not gemini_key:
    print("API keys missing!")
    exit(1)

# Initialize Gemini
genai.configure(api_key=gemini_key)
model = genai.GenerativeModel("gemini-pro")

# Transportation modes
valid_modes = ['car', 'foot', 'bike', 'hike']

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

            direction_map = {
                -3: "Make a sharp left",
                -2: "Turn left",
                -1: "Bear left",
                 0: "Continue straight",
                 1: "Bear right",
                 2: "Turn right",
                 3: "Make a sharp right"
            }

            for step in paths_data["paths"][0]["instructions"]:
                sign = step.get("sign")
                dist = step["distance"]
                raw_instruction = direction_map.get(sign, step["text"])
                prompt = (
                    f"Rephrase the navigation step: '{step['text']}' "
                    f"to make it more helpful and natural. "
                    f"Add a famous nearby landmark if relevant. "
                    f"Distance is {dist/1000:.1f} km."
                )

                try:
                    gemini_response = model.generate_content(prompt)
                    enriched_instruction = gemini_response.text.strip()
                except Exception as e:
                    enriched_instruction = raw_instruction + f" and go for {dist/1000:.1f} km."

                print(f"{enriched_instruction}")
                print("=============================================")

            # Summary
            total_distance = paths_data["paths"][0]["distance"]
            total_time = paths_data["paths"][0]["time"]  # ms 
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
            print("GraphHopper Routing API failed.")
            print("Message: " + paths_data.get("message", "Unknown error"))
            print("*************************************************")
    else:
        print("Invalid locations. Try again.\n")
