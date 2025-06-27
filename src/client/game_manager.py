from src.shared import config

class GameManager:
    def __init__(self):
        self.game_screen_state = config.GAME_STATE_START_SCREEN
        self.current_state = None
        self.client_id = None
        self.final_score = 0
        self._processed_event_ids = set()
        self._timer_warning_played = False
        self.is_disconnected = False

    def update_state(self, new_state):
        # Selalu update client_id jika ada di state baru
        if "client_id" in new_state:
            if self.client_id != new_state["client_id"]:
                print(f"[DEBUG] client_id berubah: {self.client_id} -> {new_state['client_id']}")
            self.client_id = new_state["client_id"]
        self.current_state = new_state
        # Debug: pastikan client_id selalu ada di players
        if self.current_state and self.client_id not in self.current_state.get("players", {}):
            print(f"[WARNING] client_id {self.client_id} tidak ditemukan di state['players']! Mungkin sedang merge atau ada bug.")

    def check_state_transitions(self, asset_manager):
        if not self.current_state:
            return
        is_game_started = self.current_state.get("game_started", False)
        if is_game_started and self.game_screen_state == config.GAME_STATE_START_SCREEN:
            self.game_screen_state = config.GAME_STATE_PLAYING
            asset_manager.sound_manager.play_music('KitchenBGM.mp3')
            self._timer_warning_played = False
            self._processed_event_ids.clear()
        elif self.game_screen_state == config.GAME_STATE_PLAYING:
            if self.current_state.get('timer', 1) <= 0:
                self.game_screen_state = config.GAME_STATE_END_SCREEN
                self.final_score = self.current_state.get("score", 0)
                asset_manager.sound_manager.stop_music()
                asset_manager.sound_manager.play_sfx("Mission Complete")
        elif not is_game_started:
            self.game_screen_state = config.GAME_STATE_START_SCREEN
            asset_manager.sound_manager.stop_music()
        elif (self.game_screen_state == config.GAME_STATE_END_SCREEN or self.game_screen_state == config.GAME_STATE_START_SCREEN) and not is_game_started:
            if self.game_screen_state != config.GAME_STATE_START_SCREEN:
                self.game_screen_state = config.GAME_STATE_START_SCREEN

    def check_game_events(self, asset_manager):
        if self.game_screen_state != config.GAME_STATE_PLAYING or not self.current_state:
            return
        if self.current_state.get('timer', 999) <= 10 and not self._timer_warning_played:
            asset_manager.sound_manager.play_sfx('Running out of Time', volume=0.7)
            self._timer_warning_played = True
        if "visual_effects" in self.current_state:
            for event in self.current_state["visual_effects"].get("game_events", []):
                if event["id"] not in self._processed_event_ids:
                    if event["type"] == "recipe_fusion":
                        asset_manager.sound_manager.play_sfx("Success Order", volume=0.6)
                        self._processed_event_ids.add(event["id"])

    def handle_disconnect(self):
        print("Disconnected from server.")
        self.is_disconnected = True