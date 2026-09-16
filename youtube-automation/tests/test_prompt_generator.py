import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.generation.prompt_generator import PromptGenerator

def test_chatgpt_prompt_generation():
    # Load .env if present
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v

    generator = PromptGenerator(model="gpt-4o")
    
    test_vehicle = "Yamaha RX100"
    test_type = "motorcycle"
    test_color = "Glossy Cherry Red with Gold Pinstripes"
    
    print(f"\n=======================================================")
    print(f" Testing ChatGPT Prompt Generation for: {test_vehicle}")
    print(f"=======================================================\n")
    
    prompt = generator.generate_prompt_for_vehicle(
        vehicle_name=test_vehicle,
        vehicle_type=test_type,
        color_scheme=test_color,
        scale="1:12"
    )
    
    print("--- GENERATED PROMPT FROM CHATGPT (GPT-4o) ---\n")
    print(prompt)
    print("\n=======================================================")
    print(f"SUCCESS: Prompt generated ({len(prompt)} characters). Ready for Google Flow.")
    print("=======================================================\n")

if __name__ == "__main__":
    test_chatgpt_prompt_generation()
