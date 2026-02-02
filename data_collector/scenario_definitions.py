
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
        if gesture_name in ["Swipe_Left", "Swipe_Right", "Pinch_In", "Pinch_Out"]:
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
                        # 방향(Direction) 로직 제거: 제스처 이름 자체가 방향을 내포하거나, 단일 방향으로 통일
                        # 요청사항: "바깥으로/안쪽으로 경우의 수 없애주고"
                        # 따라서 모든 경우에 대해 기본 방향(예: Outward) 하나만 수행하거나, 방향 속성을 제외.
                        # 파일명 유지를 위해 Gesture Name에 따라 고정값 사용.
                        # Swipe_Left: 통상적으로 오른손 기준 Outward(오른쪽->왼쪽). 
                        # 여기서는 단순히 'Outward'로 고정하거나 Loop를 제거.
                        
                        fixed_direction = "Outward" # 단순화

                        for speed in speeds:
                            for i in range(reps):
                                step = {
                                    # Data for Filename
                                    "distance": dist,
                                    "hand": hand,
                                    "position": pos,
                                    "direction": fixed_direction,
                                    "speed": speed,
                                    "rep": i + 1,
                                    
                                    # Text for Display (Korean)
                                    # 방향 정보는 표시에서 제외 (요청사항 반영)
                                    "display_text": f"{dist}cm | {korean_map.get(hand, hand)} | {korean_map.get(pos, pos)} | {korean_map.get(speed, speed)}"
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

    def get_filename(self, username=""):
        """
        Generates filename: {action}_{distance}cm_{hand}_{position}_{direction}_{speed}_{rep}_{username}.npy
        """
        step = self.get_current_step()
        if step:
            # Action name lowercased
            action = self.gesture_name.lower()
            
            # Username processing (remove spaces, lowercase)
            user_suffix = ""
            if username:
                clean_user = username.strip().replace(" ", "_").lower()
                user_suffix = f"_{clean_user}"
            
            return f"{action}_{step['distance']}cm_{step['hand'].lower()}_{step['position'].lower()}_{step['direction'].lower()}_{step['speed'].lower()}_{step['rep']:02d}{user_suffix}.npy"
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
