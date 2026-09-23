"""
Setup Popular Cars USA Canada Top 50 Database
----------------------------------------------
Reads Popular_Cars_USA_Canada_Top_50.xlsx and populates:
youtube-automation/popular_cars_usa_canada/vehicles.json
"""

import os
import json
import openpyxl

COLOR_MAP = {
    # Pickups & Trucks
    "Ford F-150": "Agate Black Metallic with Chrome Grille and C-Clamp LED Headlights",
    "Chevrolet Silverado 1500": "Red Hot with Dual-Outlet Exhaust and High-Gloss Black Grille",
    "Ram 1500": "Delmonico Red Pearl with Chrome Billet Grille and Sport Performance Hood",
    "GMC Sierra 1500": "Titanium Rush Metallic with Signature C-Shape LEDs and Vader Chrome Accents",
    "Toyota Tacoma": "Solar Octane Orange with TRD Pro Heritage Grille and Rigid Fog Lamps",
    "Toyota Tundra": "Magnetic Gray Metallic with Massive Octagonal Grille and LED Lightbar",
    "Ford Maverick": "Cyber Orange Metallic with FX4 Off-Road Graphics and Black Bed Liner",

    # SUVs & Crossovers
    "Toyota RAV4": "Cavalry Blue with Ice Edge Contrast Roof and Rugged Fender Flares",
    "Honda CR-V": "Canyon River Blue Metallic with Gloss Black Grille and Dual Exhaust Finishers",
    "Chevrolet Equinox": "Iridescent Pearl Tricoat with Gloss Black Roof Rails and Chrome Accents",
    "Ford Explorer": "Carbonized Gray Metallic with Black Painted Roof and Quad Exhaust Outlets",
    "Hyundai Tucson": "Amazon Grey with Dark Chrome Parametric Hidden LED DRLs",
    "Nissan Rogue": "Sunset Drift ChromaFlair with Super Black Two-Tone Roof",
    "Jeep Grand Cherokee": "Baltic Grey Metallic with Gloss Black Roof and 7-Slot Grille",
    "Jeep Wrangler": "Firecracker Red with Black Freedom Hardtop and Exposed Door Hinges",
    "Subaru Crosstrek": "Sun Blaze Pearl with Rugged Body Cladding and Black Alloy Wheels",
    "Kia Sportage": "Jungle Green with Matte Black Badging and Boomerang LED DRLs",
    "Subaru Forester": "Autumn Green Metallic with Raised Roof Rails and Hexagonal Grille",
    "Chevrolet Tahoe": "Sterling Gray Metallic with RST Performance Grille and 22-Inch Wheels",
    "Ford Bronco": "Area 51 Blue with Modular Hardtop and Heavy-Duty Sasquatch Wheels",
    "Toyota Highlander": "Moon Dust Metallic with Twin-Tip Exhaust and Silver Roof Rails",
    "Kia Sorento": "Wolf Gray with Gloss Black Accents and Vertical Star-Map LED Lights",
    "Chevrolet Trax": "Nitro Yellow Metallic with Activ Black Bowties and Titanium Accents",
    "Ford Escape": "Vapor Blue Metallic with Coast-to-Coast LED Lightbar and ST-Line Grille",
    "Mazda CX-5": "Soul Red Crystal Metallic with Signature Wing Chrome Mesh and Dual Exhaust",
    "Mazda CX-30": "Polymetal Gray Metallic with Black Cladding and Gloss Black Mirrors",
    "Honda Pilot": "Diffused Sky Blue with Rugged TrailSport Grille and Steel Skid Plates",
    "Toyota 4Runner": "Terra Brown Metallic with TRD Pro Aluminum Skid Plate and Heritage Grille",
    "Chevrolet Suburban": "Empire Beige Metallic with High Country Chrome Grille and Power Steps",
    "GMC Yukon": "Onyx Black with Denali Galvano Chrome Mesh and Signature C-Lighting",
    "Cadillac Escalade": "Black Raven with Galvano Chrome Mesh Grille and 3-Foot Vertical LED Blades",
    "Jeep Compass": "Laser Blue Pearl with Gloss Black Roof and Chrome-Rings 7-Slot Grille",
    "Hyundai Santa Fe": "Terracotta Orange Matte with H-Shaped LED Headlights and Boxy Tailgate",
    "Kia Telluride": "Dark Moss Green with Amber LED Running Lights and X-Line High-Rider Stance",
    "Nissan Pathfinder": "Boulder Gray Pearl with Black Two-Tone Roof and Rugged V-Motion Face",

    # Sedans & Hatchbacks
    "Toyota Camry": "Supersonic Red with Midnight Black Dual-Tone Roof and Quad Chrome Tips",
    "Toyota Corolla": "Celestite Metallic with Sport Mesh Front Grille and LED Headlights",
    "Honda Civic": "Rallye Red with Gloss Black Decklid Spoiler and Center Exhaust",
    "Honda Accord": "Meteorite Gray Metallic with Gloss Black Mesh Grille and Fastback Silhouette",
    "Nissan Sentra": "Monarch Orange Metallic with Super Black Roof and V-Motion Grille",
    "Hyundai Elantra": "Intense Blue with Parametric Jewel Front Fascia and Angular Sculpting",

    # Minivan
    "Toyota Sienna": "Ruby Flare Pearl with Sport Mesh Front Fascia and Chrome Sliders",

    # Electric Vehicles
    "Tesla Model Y": "Deep Blue Metallic with Stealth Satin Aero Wheels and Panoramic Glass Roof",
    "Tesla Model 3": "Solid Black with Satin Aero Covers and Glass Panoramic Canopy",
    "Ford Mustang Mach-E": "Cyber Orange Metallic with Dark Aero Grille Shield and Panoramic Glass",

    # Sports & Muscle Cars
    "Ford Mustang": "Grabber Blue Metallic with Black GT Racing Stripes and Quad Exhaust Tips",
    "Chevrolet Corvette": "Torch Red with Carbon Flash High-Wing Spoiler and Mid-Engine Glass Cover",
    "Dodge Charger": "Plum Crazy Purple with Hellcat Dual-Snorkel Hood and Widebody Flares",
    "Dodge Challenger": "TorRed with Satin Black Dual Racing Stripes and Shaker Hood Scoop",
    "Chevrolet Camaro": "Vivid Orange Metallic with ZL1 Carbon Fiber Hood Insert and Black Wing"
}


def build_usa_cars():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    src_xlsx = os.path.join(root_dir, "Popular_Cars_USA_Canada_Top_50.xlsx")
    target_dir = os.path.join(script_dir, "popular_cars_usa_canada")
    os.makedirs(target_dir, exist_ok=True)
    target_json = os.path.join(target_dir, "vehicles.json")

    if not os.path.exists(src_xlsx):
        print(f"[-] Source Excel not found: {src_xlsx}")
        return

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
            "source_excel": "Popular_Cars_USA_Canada_Top_50",
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
    build_usa_cars()
