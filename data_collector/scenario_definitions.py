SUPPORTED_GESTURES = [
    "Pinch_In_Left", "Pinch_In_Right",
    "Pinch_Out_Left", "Pinch_Out_Right",
    "Play_Pause_Left", "Play_Pause_Right",
    "Volume_Up_Left", "Volume_Up_Right",
    "Volume_Down_Left", "Volume_Down_Right",
    "Swipe_Left", "Swipe_Right",
    "No_Gesture",
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
        - Play_Pause_Left/Right: 거리 × 위치 × 6회 = 54단계 (손은 제스처명에 따라 고정)
        - Volume_Up/Down_Left/Right: 거리 × 위치 × 6회 = 54단계 (손은 제스처명에 따라 고정)
        - Swipe_Left, Swipe_Right: 거리 × 위치 × 6회 = 54단계 (Swipe_Left=오른손, Swipe_Right=왼손)
        """
        self.gesture_name = gesture_name
        self.scenarios = []
        self.current_index = 0

        if gesture_name not in self.SUPPORTED_GESTURES:
            self.total_scenarios = 0
            return

        # No_Gesture는 시나리오 없이 자유롭게 수집 (다양한 정지/대기 포즈)
        if gesture_name == "No_Gesture":
            # 간단한 시나리오: 다양한 정지 상태를 수집하도록 안내
            # 사용자가 자유롭게 다양한 정지 포즈를 녹화하도록 함
            self.scenarios = [{
                "display_text": "정지/대기 상태 녹화 (양손 보이지만 움직이지 않음)"
            }]
            self.total_scenarios = 1
            return

        distances = [70, 140, 200]
        positions = ["Top", "Center", "Bottom"]  # 상단, 중앙, 하단
        reps = 6

        # 제스처별 손 고정 (훈련용으로 좌/우 분리)
        if gesture_name in (
            "Pinch_In_Left",
            "Pinch_Out_Left",
            "Play_Pause_Left",
            "Volume_Up_Left",
            "Volume_Down_Left",
        ):
            hands = ["Left"]
        elif gesture_name in (
            "Pinch_In_Right",
            "Pinch_Out_Right",
            "Play_Pause_Right",
            "Volume_Up_Right",
            "Volume_Down_Right",
        ):
            hands = ["Right"]
        elif gesture_name == "Swipe_Left":
            hands = ["Right"]
        elif gesture_name == "Swipe_Right":
            hands = ["Left"]
        else:
            # Fallback (should not happen if SUPPORTED_GESTURES is kept in sync)
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
        No_Gesture의 경우: {action}_{timestamp}_{username}.npy
        """
        step = self.get_current_step()
        if step:
            action = self.gesture_name.lower()
            user_suffix = ""
            if username:
                clean_user = username.strip().replace(" ", "_").lower()
                user_suffix = f"_{clean_user}"
            
            # No_Gesture는 시나리오 구조가 없으므로 타임스탬프 사용
            if self.gesture_name == "No_Gesture":
                import time
                timestamp = int(time.time() * 1000)
                return f"{action}_{timestamp}{user_suffix}.npy"
            
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
