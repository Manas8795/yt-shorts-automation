import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger("prompt_generator")


class PromptGenerator:
    """
    Generates tailored, photorealistic Cars & Bikes ASMR prompts for Google Flow
    using OpenAI GPT-4o with automatic seamless local template fallback.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        template_path: str = "config/prompt_framework.txt",
        motorcycle_template_path: str = "config/prompt_framework_motorcycle.txt"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.template_path = template_path
        self.motorcycle_template_path = motorcycle_template_path

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(self.template_path):
            self.template_path = os.path.join(base_dir, self.template_path)
        if not os.path.isabs(self.motorcycle_template_path):
            self.motorcycle_template_path = os.path.join(base_dir, self.motorcycle_template_path)

        self.car_template = self._load_file(self.template_path)
        self.motorcycle_template = self._load_file(self.motorcycle_template_path)

    def _load_file(self, path: str) -> str:
        """Loads a template file."""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def generate_local_fallback_prompt(
        self,
        vehicle_name: str,
        vehicle_type: str = "car",
        color_scheme: str = "",
        scale: str = ""
    ) -> str:
        """
        Generates the prompt directly using the exact vehicle-type specific storyboard framework.
        Bikes get motorcycle unboxing steps (kickstand, handlebars, bike seat, key ignition).
        Cars get car unboxing steps (doors, cabin interior bucket seats, dashboard, action payoff).
        """
        import re
        is_bike = any(b in vehicle_type.lower() for b in ["motorcycle", "bike", "scooter"])
        template = self.motorcycle_template if (is_bike and self.motorcycle_template) else self.car_template

        eff_scale = scale or ("1:12" if is_bike else "1:18")
        eff_color = color_scheme or "Gloss Finish"

        context = {
            # Standard common keys (both cases)
            "vehicle_name": vehicle_name,
            "VEHICLE_NAME": vehicle_name,
            "vehicle_type": vehicle_type,
            "VEHICLE_TYPE": vehicle_type,
            "color_scheme": eff_color,
            "COLOR_SCHEME": eff_color,
            "paint_color": eff_color,
            "PAINT_COLOR": eff_color,
            "scale": eff_scale,
            "SCALE": eff_scale,

            # Premium car storyboard placeholders
            "HERO_FRONT_FEATURE": "sculpted front hood, aerodynamic fascia, and iconic brand badge",
            "IGNITION_ACTION": "push-to-start ignition button on the center console",
            "HEADLIGHT_ACTION": "sharp projector LED headlights and daytime running lights",
            "FRONT_FEATURE_1": "aerodynamic front bumper intake",
            "FRONT_FEATURE_2": "signature front grille texture",
            "HERO_BODY_DETAIL": "flawless metallic door contour and side mirrors",
            "WHEELS_DETAIL": "diamond-cut multi-spoke alloy wheels with realistic rubber tires and disc brakes",
            "HERO_FEATURE_1": "sculpted front bumper and air dams",
            "HERO_FEATURE_2": "detailed front grille and emblem",
            "HERO_FEATURE_3": "crystal-clear headlight lenses and LED daytime signatures",
            "HERO_FEATURE_4": "aerodynamic hood creases and gloss paint finish",
            "INTERIOR_FEATURE_1": "detailed sport bucket seats with contrast stitching",
            "INTERIOR_FEATURE_2": "illuminated digital cockpit and central touchscreen infotainment",
            "INTERIOR_FEATURE_3": "multi-function steering wheel with paddle shifters",
            "INTERIOR_FEATURE_4": "center console with precision gear selector and metallic trim",
            "REAR_ANGLE": "low rear three-quarter angle",
            "THROTTLE_ACTION": "miniature accelerator pedal",
            "FINAL_ACTION": "launches forward with realistic tabletop tire grip and a controlled power slide",
            "FINAL_POSE": "30-degree angled heroic stance",
            "FINAL_HERO_FEATURE": "iconic front fascia and glowing LED headlights"
        }

        if template:
            def _replace_placeholder(match):
                key = match.group(1)
                return str(context.get(key, context.get(key.upper(), context.get(key.lower(), match.group(0)))))

            return re.sub(r'\{([A-Za-z0-9_]+)\}', _replace_placeholder, template)

        prompt = (
            f"A hyper-realistic macro-lens ASMR unboxing video featuring a HUGE premium Poké Ball containing a HUGE 1:18-scale die-cast miniature {vehicle_name} on a smooth wooden tabletop.\n\n"
            f"Cinematic studio lighting, realistic shadows, sharp macro focus, shallow depth of field, premium collector's-display aesthetic.\n\n"
            f"Directly generate the complete 10-second vertical 9:16 video scene now."
        )
        return prompt

    def generate_prompt_for_vehicle(
        self,
        vehicle_name: str,
        vehicle_type: str = "car",
        color_scheme: str = "",
        scale: str = ""
    ) -> str:
        """
        Attempts OpenAI GPT-4o prompt generation using the 8-shot framework.
        If quota is exhausted or API key is not present, falls back seamlessly to the exact local template.
        """
        if not self.api_key:
            logger.info("No OpenAI API key detected. Using local ASMR framework generator.")
            return self.generate_local_fallback_prompt(vehicle_name, vehicle_type, color_scheme, scale)

        logger.info(f"Attempting OpenAI ({self.model}) prompt generation for: {vehicle_name}")

        system_instruction = (
            "You are an expert AI prompt engineer specialized in hyper-realistic automotive ASMR video generation "
            "for Google Flow. You produce dense, photorealistic video prompts strictly following the exact "
            "8-shot die-cast miniature unboxing sequence. Output ONLY the final prompt text without markdown formatting or pleasantries."
        )

        is_bike = any(b in vehicle_type.lower() for b in ["motorcycle", "bike", "scooter"])
        template = self.motorcycle_template if (is_bike and self.motorcycle_template) else self.car_template

        user_prompt = f"""
Apply the following 8-Shot ASMR Storyboard Framework to create the exact prompt for:
- Vehicle: {vehicle_name} (Type: {vehicle_type})

FRAMEWORK SPECIFICATION:
{template or self.generate_local_fallback_prompt(vehicle_name, vehicle_type, color_scheme, scale)}
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1200
        }

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}"
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                generated_prompt = result["choices"][0]["message"]["content"].strip()
                logger.info(f"Successfully generated custom prompt ({len(generated_prompt)} chars) via OpenAI GPT-4o for {vehicle_name}")
                return generated_prompt

        except urllib.error.HTTPError as e:
            logger.warning(f"OpenAI API quota/billing limit reached ({e.code}). Switching to built-in ASMR Framework Engine.")
            return self.generate_local_fallback_prompt(vehicle_name, vehicle_type, color_scheme, scale)
        except Exception as e:
            logger.warning(f"OpenAI API call failed ({e}). Switching to built-in ASMR Framework Engine.")
            return self.generate_local_fallback_prompt(vehicle_name, vehicle_type, color_scheme, scale)

