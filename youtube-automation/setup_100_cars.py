"""
Setup 100 Popular Cars Database
-------------------------------
Reads youtube-automation/100_popular_cars_in_India.xlsx and populates:
youtube-automation/100 popular cars/vehicles.json
"""

import os
import json
import openpyxl

COLOR_MAP = {
    # Maruti Suzuki
    "Maruti Suzuki Swift": "Sizzling Red with Midnight Black Dual-Tone Roof",
    "Maruti Suzuki Dzire": "Sherwood Brown with Chrome Window Line Accents",
    "Maruti Suzuki Wagon R": "Silky Silver with Body-Colored Accents",
    "Maruti Suzuki Baleno": "Celestial Blue with Precision Cut Dual-Tone Alloys",
    "Maruti Suzuki Brezza": "Brave Khaki with Arctic White Roof",
    "Maruti Suzuki Fronx": "Nexa Blue with Geometric Gloss Chrome Grille",
    "Maruti Suzuki Grand Vitara": "Opulent Red with Midnight Black Contrast Roof",
    "Maruti Suzuki Ertiga": "Metallic Magma Grey with Front Chrome Wing",
    "Maruti Suzuki XL6": "Brave Khaki with Smoke Grey Tail Lamps and Roof Rails",
    "Maruti Suzuki Alto K10": "Solid White with High-Mount Stop Lamp",
    "Maruti Suzuki Celerio": "Speedy Blue with Fluid Aerodynamic Curve Line",
    "Maruti Suzuki S-Presso": "Starry Blue with SUV-Inspired Black Cladding",
    "Maruti Suzuki Ignis": "Lucent Orange with Black Roof and Trapezoidal Grille",
    "Maruti Suzuki Jimny": "Kinetic Yellow with Bluish Black Roof and Retro Round Lamps",
    "Maruti Suzuki Ciaz": "Pearl Sangria Red with Sleek Executive Chrome Strip",
    "Maruti Suzuki Eeco": "Metallic Silky Silver with Dual Sliding Doors",
    "Maruti Suzuki Invicto": "Mystic White with Distinctive Nexa Front Grille",

    # Tata Motors
    "Tata Punch": "Tornado Blue with White Contrast Roof and Tri-Arrow Grille",
    "Tata Nexon": "Fearless Purple with Signature Horizon LED Daytime Lightbar",
    "Tata Nexon EV": "Empowered Oxide Dual Tone with Signature Teal Blue Accents",
    "Tata Tiago": "Daytona Grey with Dynamic Chrome Grille Strip",
    "Tata Tiago EV": "Tropical Mist with Signature EV Blue Accents",
    "Tata Tigor": "Opal White with Projector Headlamps and Chrome Garnish",
    "Tata Tigor EV": "Signature Teal Blue with Aerodynamic Wheel Covers",
    "Tata Altroz": "Downtown Red with Glossy Black Contrast Roof and Laser Cut Alloys",
    "Tata Harrier": "Dark Edition Oberon Black with Blacked-Out Blackstone Alloys",
    "Tata Safari": "Cosmic Gold with Panoramic Sunroof Accents and Stepped Roof",
    "Tata Curvv": "Flame Red with Dramatic Aerodynamic Coupe Sloping Roofline",
    "Tata Curvv EV": "Virtual Sunrise Blue with Seamless Edge-to-Edge LED Light Strip",

    # Mahindra
    "Mahindra Thar": "Napoli Black with Rugged Off-Road All-Terrain Tyres and Hardtop",
    "Mahindra Thar Roxx": "Everest White with 5-Door Stance and Dual-Tone Black Roof",
    "Mahindra Scorpio": "Diamond White with Classic Roaring Stance and Ski-Rack Rails",
    "Mahindra Scorpio N": "Deep Forest Metallic with Chrome Talon Grille and High Bonnet",
    "Mahindra Scorpio Classic": "Galaxy Grey with Vertical Chrome Slats and Classic Spoiler",
    "Mahindra XUV700": "Electric Blue with Smart Flush Door Handles and Arrow-Head LEDs",
    "Mahindra XUV 3XO": "Citrine Yellow with Stealth Black Contrast Roof and C-Shaped LEDs",
    "Mahindra XUV300": "Red Rage with Dual-Tone Black Roof and Projector Headlamps",
    "Mahindra XUV400 EV": "Infinity Blue with Satin Copper Roof and Accents",
    "Mahindra Bolero": "Rocky Beige with Metal Bumper and Classic Rugged Side Decals",
    "Mahindra Bolero Neo": "Diamond White with Combat Hardtop and Alloy Wheels",
    "Mahindra Marazzo": "Aqua Marine with Shark-Fin Inspired Tail Lamps",

    # Hyundai
    "Hyundai Creta": "Abyss Black Pearl with Parametric Jewel Grille and Horizon Lightbar",
    "Hyundai Creta N Line": "Shadow Grey Matte with Thunder Red Lip Accents and Twin Tip Exhaust",
    "Hyundai Venue": "Typhoon Silver with Dark Chrome Radiator Grille",
    "Hyundai Venue N Line": "Polar White with Phantom Black Roof and Red Skid Plate Accents",
    "Hyundai Verna": "Starry Night Metallic with Horizon LED Strip and Parametric Grille",
    "Hyundai i20": "Fiery Red with Black Cascading Grille and Z-Shaped LED Tail Lamps",
    "Hyundai i20 N Line": "Thunder Blue with Athletic Red Skirts and Twin Exhaust",
    "Hyundai Exter": "Ranger Khaki with Black Cladding and H-Shaped Signature LEDs",
    "Hyundai Alcazar": "Titan Grey Matte with Dark Chrome Louvered Grille and Trio Beam LEDs",
    "Hyundai Tucson": "Amazon Grey with Parametric Hidden Lights and Dark Chrome Accents",
    "Hyundai Ioniq 5": "Gravity Gold Matte with Pixel LED Headlights and Aerodynamic Spoke Wheels",
    "Hyundai Grand i10 Nios": "Spark Green with Black Roof and Boomerang DRLs",
    "Hyundai Aura": "Starry Night with Integrated Rear Lip Spoiler",

    # Toyota
    "Toyota Innova Crysta": "Super White with Premium Chrome Front Louvers and Captain Seats",
    "Toyota Innova Hycross": "Blackish Ageha Glass Flake with Panoramic Roof and Muscular Bonnet",
    "Toyota Urban Cruiser Taisor": "Lucent Orange with Midnight Black Dual-Tone Roof",
    "Toyota Urban Cruiser Hyryder": "Cafe White with Midnight Black Roof and Crystal Acrylic Grille",
    "Toyota Fortuner": "Attitude Black with Massive Chrome Radiator Grille and Quad Projectors",
    "Toyota Fortuner Legender": "Platinum White Pearl with Black Contrast Roof and Aggressive Bi-LEDs",
    "Toyota Glanza": "Insta Blue with Swept-Back LED Projectors and Carbon Fiber Accents",
    "Toyota Hilux": "Emotional Red with Heavy-Duty Skid Plate and Steel Roll-Bar",
    "Toyota Land Cruiser": "Precious White Pearl with 300 Series Heavyweight Front Facia",
    "Toyota Land Cruiser Prado": "Attitude Black Metallic with Rugged Boxy Silhouette",
    "Toyota Camry": "Burning Black Crystal Shine with Satin Chrome Executive Facia",
    "Toyota Vellfire": "Black Metallic with Executive Lounge Dual Chrome Slats",
    "Toyota Rumion": "Spunky Blue with Chrome Wing Mesh Grille",

    # Kia
    "Kia Seltos": "Pewter Olive with Signature Tiger Nose Knurled Grille and Star Map LEDs",
    "Kia Sonet": "Intense Red with Black High-Gloss Knurled Grille and Red Brake Calipers",
    "Kia Carens": "Imperial Blue with Crown Jewel LED Headlamps and Star Map Lighting",
    "Kia Carnival": "Aurora Black Pearl with Limousine Dual Sunroof and Chrome Skirts",
    "Kia EV6": "Yacht Blue Matte with Cyberpunk Sequential LED Tail Light Bar",
    "Kia EV9": "Ocean Blue Matte with Digital Pattern Lighting Grille and Boxy Cyber Stance",

    # Honda
    "Honda City": "Radiant Red Metallic with Full LED Jewel Eye Headlights and Z-Tail Lamps",
    "Honda City e:HEV": "Obsidian Blue Pearl with Signature Blue H Emblem and Trunk Spoiler",
    "Honda Elevate": "Phoenix Orange Pearl with Bold Square-Jaw Chrome Grille",
    "Honda Amaze": "Meteoroid Grey Metallic with Sleek Solid Wing Chrome Face",

    # Skoda & Volkswagen
    "Skoda Slavia": "Crystal Blue with Crystalline Split Tail Lamps and Hexagonal Grille",
    "Skoda Kushaq": "Tornado Red with Signature Butterfly Grille and Two-Tone Machine Alloys",
    "Skoda Kodiaq": "Lava Blue Metallic with Panoramic Sunroof and Illuminated Grille Ribs",
    "Skoda Superb": "Rosso Brunello Wine Metallic with Executive Matrix LED Lights",
    "Volkswagen Virtus": "Wild Cherry Red with Gloss Black GT Spoilers and Red Brake Calipers",
    "Volkswagen Taigun": "Curcuma Yellow with Infinity LED Tail Bar and Trapezoidal Chrome Trim",
    "Volkswagen Tiguan": "Nightshade Blue Metallic with IQ.Light Matrix Headlamps",

    # MG
    "MG Hector": "Candy White with Argyle Inspired Diamond Mesh Grille and Connected LEDs",
    "MG Hector Plus": "Havana Grey with Dual-Tone Machined Alloys and Panoramic Roof",
    "MG Astor": "Spiced Orange with Celestial Diamond Grille and Full LED Hawkeye Lamps",
    "MG Comet EV": "Apple Green with Dual-Tone Black Canopy and Extended LED Horizon Bar",
    "MG ZS EV": "Ferrite White with Integrated Aero Wheel Covers and Grille-Less Front",
    "MG Gloster": "Warm White with Massive Dual-Tone Octagonal Grille and Twin Exhausts",

    # Jeep
    "Jeep Compass": "Techno Metallic Green with 7-Slot Chrome Grille and Trapezoidal Arches",
    "Jeep Meridian": "Magnesio Grey with Velvet Matte Finish and Extended 3-Row Body",
    "Jeep Wrangler": "Firecracker Red with Removable Freedom Top Doors and Exposed Hinges",
    "Jeep Grand Cherokee": "Bright White with Black Contrast Roof and Signature Quadra-Trac Badge",

    # Renault & Nissan
    "Renault Kwid": "Zanskar Blue with Dual-Tone Roof and High Ground Clearance Stance",
    "Renault Kiger": "Radiant Red with Mystery Black Roof and Tri-Octa Pure Vision LEDs",
    "Renault Triber": "Metal Mustard with Roof Rails and Flexible 7-Seater Profile",
    "Nissan Magnite": "Flare Garnet Red with Onyx Black Roof and L-Shaped Chrome DRLs",
    "Nissan X-Trail": "Champagne Silver with V-Motion Chrome Grille and Split LED Lights",

    # Force & Others
    "Force Gurkha": "Red Rage with Snorkel Intake, 4x4 Badge and Heavy-Duty Steel Bumpers",
    "Citroen C3": "Zesty Orange with Polar White Roof and Chevron Chrome Grille",
    "Citroen C3 Aircross": "Steel Grey with Cosmo Blue Pack and Dual Chevron Cheeks",
    "Citroen Basalt": "Garnet Red with Aerodynamic Coupe Sloping Rear Profile"
}


def build_100_cars():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_xlsx = os.path.join(script_dir, "100_popular_cars_in_India.xlsx")
    target_dir = os.path.join(script_dir, "100 popular cars")
    os.makedirs(target_dir, exist_ok=True)
    target_json = os.path.join(target_dir, "vehicles.json")

    wb = openpyxl.load_workbook(src_xlsx)
    ws = wb.active

    cars_list = []
    for r in list(ws.iter_rows())[1:]:
        c_id = r[0].value
        c_name = str(r[1].value or "").strip()
        if not c_id or not c_name:
            continue

        c_id = int(c_id)
        color = COLOR_MAP.get(c_name, "Glossy Dual-Tone Metallic with High-Gloss Black Accents")

        car_item = {
            "id": c_id,
            "vehicle_name": c_name,
            "type": "car",
            "color_scheme": color,
            "scale": "1:18",
            "source_excel": "100_popular_cars_in_India",
            "status": "PENDING"
        }
        cars_list.append(car_item)

    # Save to vehicles.json
    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(cars_list, f, indent=2)

    print(f"[+] Successfully created: {target_json}")
    print(f"[+] Total vehicles configured: {len(cars_list)}")

    # Print preview
    print("\nSample Preview:")
    for v in cars_list[:5]:
        print(f"  ID {v['id']:2d}: {v['vehicle_name']} -> {v['color_scheme']}")
    print(f"  ... and {len(cars_list) - 5} more cars.")


if __name__ == "__main__":
    build_100_cars()
