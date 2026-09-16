"""
YouTube Shorts Metadata Generator
---------------------------------
Generates optimized, viral Titles, Descriptions, and Tags for Car & Bike ASMR unboxing Shorts.
"""

import re
import sys
from typing import Dict, Any, List

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def clean_tag(text: str) -> str:
    """Converts a vehicle name or feature into a clean hashtag."""
    tag = re.sub(r'[^a-zA-Z0-9]', '', text)
    return tag.lower()

def generate_short_metadata(vehicle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates YouTube Shorts metadata (Title, Description, Tags, Category, Audience).
    """
    name = vehicle.get("vehicle_name", "Supercar")
    v_type = vehicle.get("type", "car").lower()
    color = vehicle.get("color_scheme", "Custom Edition")
    scale = vehicle.get("scale", "1:18")

    tag_type = "cars" if v_type == "car" else "bikes"
    emoji = "🏎️" if v_type == "car" else "🏍️"
    
    is_assembly = vehicle.get("is_assembly", False) or "assembly" in vehicle.get("source_excel", "").lower()
    
    # 1. Viral YouTube Shorts Title (strictly < 100 chars, ideally 60-80 chars)
    # Must include #shorts, emojis, and vehicle name
    action_word = "Assembly" if is_assembly else "Unboxing"
    base_title = f"Miniature {name} ASMR {action_word} {emoji} #shorts #{tag_type}"
    if len(base_title) > 95:
        base_title = f"{name} ASMR {action_word} {emoji} #shorts #{tag_type}"
    if len(base_title) > 95:
        base_title = f"{name} {action_word} {emoji} #shorts"

    title = base_title

    # 2. Rich YouTube Shorts Description
    primary_hashtag = f"#{clean_tag(name)}"
    if is_assembly:
        description = f"""Assembling a hyper-realistic 1:12 scale miniature {name} part by part with precision tools on a wooden workbench! {emoji}✨

Experience the satisfying tactile clicks, screw fastening, and authentic mechanical assembly in high-definition ASMR sound.

🔔 Subscribe for daily satisfying miniature vehicle builds & assemblies!
👍 Like if you love the sound of craftsmanship.

Vehicle: {name}
Scale: 1:12 Miniature Model
Category: {v_type.capitalize()}

#shorts #asmr #{tag_type} #diecast #miniature #assembly {primary_hashtag} #satisfying #craftsmanship #restoration
"""
    else:
        description = f"""Unboxing a hyper-realistic {scale} scale miniature {name} ({color}) on a polished dark walnut studio tabletop! {emoji}✨

Experience the satisfying tactile clicks, peels, and engine details in high-definition ASMR sound.

🔔 Subscribe for daily satisfying miniature vehicle unboxings!
👍 Like if you love the sound of craftsmanship.

Vehicle: {name}
Scale: {scale}
Color: {color}
Category: {v_type.capitalize()}

#shorts #asmr #{tag_type} #diecast #miniature {primary_hashtag} #satisfying #hotwheels #supercars #automotive
"""

    # 3. SEO Tags (comma-separated list for YouTube Studio tags box, max 500 chars total)
    if is_assembly:
        tags_list = [
            name,
            f"{name} assembly",
            f"{name} asmr",
            f"miniature {name}",
            f"diecast {name}",
            f"{v_type} assembly",
            "asmr assembly",
            "satisfying asmr",
            "bike asmr" if v_type != "car" else "car asmr",
            "bike assembly" if v_type != "car" else "car assembly",
            "miniature assembly",
            "shorts",
            "viral shorts",
            "youtube shorts"
        ]
    else:
        tags_list = [
            name,
            f"{name} asmr",
            f"miniature {name}",
            f"diecast {name}",
            f"{scale} {name}",
            f"{v_type} unboxing",
            "asmr unboxing",
            "satisfying asmr",
            "car asmr" if v_type == "car" else "bike asmr",
            "diecast unboxing",
            "miniature car" if v_type == "car" else "miniature bike",
            "shorts",
            "viral shorts",
            "youtube shorts"
        ]
    
    # Ensure total tag string length is under 480 characters
    cur_len = 0
    final_tags: List[str] = []
    for t in tags_list:
        if cur_len + len(t) + 2 <= 480:
            final_tags.append(t)
            cur_len += len(t) + 2

    return {
        "title": title,
        "description": description.strip(),
        "tags": final_tags,
        "tags_csv": ", ".join(final_tags),
        "category": "Autos & Vehicles",
        "made_for_kids": False
    }


if __name__ == "__main__":
    sample_vehicle = {
        "id": 21,
        "vehicle_name": "Bugatti Chiron Super Sport 300+",
        "type": "car",
        "color_scheme": "Matte Jet Black with Dual Racing Orange Stripes",
        "scale": "1:18"
    }
    meta = generate_short_metadata(sample_vehicle)
    print("=== PREVIEW METADATA ===")
    print(f"TITLE ({len(meta['title'])} chars):\n{meta['title']}\n")
    print(f"DESCRIPTION:\n{meta['description']}\n")
    print(f"TAGS ({len(meta['tags_csv'])} chars):\n{meta['tags_csv']}\n")
    print(f"CATEGORY: {meta['category']}")
    print(f"MADE FOR KIDS: {meta['made_for_kids']}")
