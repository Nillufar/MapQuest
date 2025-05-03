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
    user_mode = input("Enter mode of transport (car, foot, bike, hike): ").strip().lower()
    if user_mode not in valid_modes:
        print("Invalid or empty input. Defaulting to 'car'.")
        vehicle = "car"
    else:
        vehicle = user_mode
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
                phrase = direction_map.get(sign, step["text"])
                print(f"{phrase} and go for {dist/1000:.1f} km ({dist/1000/1.61:.1f} miles).")
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