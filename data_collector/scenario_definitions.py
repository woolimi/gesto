
class ScenarioManager:
    """
    Manages the data collection scenarios based on a defined structure.
    """
    def __init__(self):
        self.scenarios = [] 
        self.current_index = 0
        self.total_scenarios = 0
        self.gesture_name = ""

    def generate_scenarios(self, gesture_name):
        """
        Generates scenarios for a given gesture name.
        Currently supports 'Swipe_Left' and 'Swipe_Right' with the 144-step logic.
        """
        self.gesture_name = gesture_name
        self.scenarios = []
        self.current_index = 0
        
        # Common Logic for Swipe Gestures
        if gesture_name in ["Swipe_Left", "Swipe_Right"]:
            distances = [70, 140, 200]
            hands = ["Right", "Left"]
            speeds = ["Normal", "Slow", "Fast"] # 보통, 느림, 빠름
            reps = 2

            # Korean mappings for display
            korean_map = {
                "Right": "오른손", "Left": "왼손",
                "Center": "중앙", "Up": "위", "Down": "아래", "Up_Down": "위/아래",
                "Outward": "바깥으로", "Inward": "안쪽으로",
                "Normal": "보통", "Slow": "느림", "Fast": "빠름"
            }

            for dist in distances:
                for hand in hands:
                    positions = []
                    if dist == 70:
                        positions = ["Center", "Up", "Down"]
                    elif dist == 140:
                        positions = ["Center", "Up", "Down"]
                    elif dist == 200:
                        positions = ["Center", "Up_Down"] # 200cm logic

                    for pos in positions:
                        directions = []
                        # Logic for Directions
                        if dist == 70:
                            directions = ["Outward", "Inward"]
                        elif dist == 140:
                            if pos == "Center":
                                directions = ["Outward", "Inward"]
                            else:
                                directions = ["Outward"]
                        elif dist == 200:
                            directions = ["Outward"]

                        for direction in directions:
                            for speed in speeds:
                                for i in range(reps):
                                    step = {
                                        # Data for Filename
                                        "distance": dist,
                                        "hand": hand,
                                        "position": pos,
                                        "direction": direction,
                                        "speed": speed,
                                        "rep": i + 1,
                                        
                                        # Text for Display (Korean)
                                        "display_text": f"{dist}cm | {korean_map.get(hand, hand)} | {korean_map.get(pos, pos)} | {korean_map.get(direction, direction)} | {korean_map.get(speed, speed)}"
                                    }
                                    self.scenarios.append(step)
        
        self.total_scenarios = len(self.scenarios)
        print(f"Generated {self.total_scenarios} scenarios for {gesture_name}")

    def get_current_step(self):
        if 0 <= self.current_index < self.total_scenarios:
            return self.scenarios[self.current_index]
        return None

    def get_progress_text(self):
        if self.total_scenarios == 0:
            return "No Scenarios"
        percentage = int((self.current_index + 1) / self.total_scenarios * 100)
        return f"Step: {self.current_index + 1} / {self.total_scenarios} ({percentage}%)"

    def get_instruction_text(self):
        step = self.get_current_step()
        if step:
            return step['display_text']
        return "모든 시나리오 완료!"

    def get_filename(self):
        """
        Generates filename: {action}_{distance}cm_{hand}_{position}_{direction}_{speed}_{rep}.npy
        """
        step = self.get_current_step()
        if step:
            # Action name lowercased
            action = self.gesture_name.lower()
            return f"{action}_{step['distance']}cm_{step['hand'].lower()}_{step['position'].lower()}_{step['direction'].lower()}_{step['speed'].lower()}_{step['rep']:02d}.npy"
        return "unknown.npy"

    def next(self):
        if self.current_index < self.total_scenarios:
            self.current_index += 1
            return True
        return False

    def prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False
    
    def is_finished(self):
        return self.current_index >= self.total_scenarios
