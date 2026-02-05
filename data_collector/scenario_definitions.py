SUPPORTED_GESTURES = [
    "Pinch_In_Left", "Pinch_In_Right",
    "Pinch_Out_Left", "Pinch_Out_Right",
    "Swipe_Left", "Swipe_Right",
    "Unknown",  # 인식 불명/기타 자세 학습용 (모션 인식 시 동작 없음)
]


class ScenarioManager:
    """
    Manages the data collection scenarios based on a defined structure.
    """
    def __init__(self):
        self.scenarios = [] 
        self.current_index = 0
        self.total_scenarios = 0
        self.gesture_name = ""
        self.SUPPORTED_GESTURES = SUPPORTED_GESTURES

    def generate_scenarios(self, gesture_name):
        """
        Generates scenarios for a given gesture name.
        - Pinch_*_Left/Right: 거리 × 위치 × 6회 = 54단계 (손은 제스처명에 따라 고정)
        - Swipe_Left, Swipe_Right: 거리 × 위치 × 6회 = 54단계 (Swipe_Left=오른손, Swipe_Right=왼손)
        """
        self.gesture_name = gesture_name
        self.scenarios = []
        self.current_index = 0

        if gesture_name not in self.SUPPORTED_GESTURES:
            self.total_scenarios = 0
            return
        if gesture_name == "Unknown":
            # Unknown은 시나리오 없이 수동 에피소드로만 수집
            self.total_scenarios = 0
            return

        distances = [70, 140, 200]
        positions = ["Top", "Center", "Bottom"]  # 상단, 중앙, 하단
        reps = 6

        # 제스처별 손 고정 (훈련용으로 좌/우 분리)
        if gesture_name in ("Pinch_In_Left", "Pinch_Out_Left"):
            hands = ["Left"]
        elif gesture_name in ("Pinch_In_Right", "Pinch_Out_Right"):
            hands = ["Right"]
        elif gesture_name == "Swipe_Left":
            hands = ["Right"]
        else:  # Swipe_Right
            hands = ["Left"]

        korean_map = {
            "Right": "오른손", "Left": "왼손",
            "Top": "상단", "Center": "중앙", "Bottom": "하단",
            "Outward": "바깥으로", "Inward": "안쪽으로",
        }

        for dist in distances:
            for hand in hands:
                for pos in positions:
                    fixed_direction = "Outward"
                    for i in range(reps):
                        step = {
                            "distance": dist,
                            "hand": hand,
                            "position": pos,
                            "direction": fixed_direction,
                            "rep": i + 1,
                            "display_text": f"{dist}cm | {korean_map.get(hand, hand)} | {korean_map.get(pos, pos)}"
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
        Generates filename: {action}_{distance}cm_{hand}_{position}_{direction}_{rep}_{username}.npy
        """
        step = self.get_current_step()
        if step:
            action = self.gesture_name.lower()
            user_suffix = ""
            if username:
                clean_user = username.strip().replace(" ", "_").lower()
                user_suffix = f"_{clean_user}"
            return f"{action}_{step['distance']}cm_{step['hand'].lower()}_{step['position'].lower()}_{step['direction'].lower()}_{step['rep']:02d}{user_suffix}.npy"
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
