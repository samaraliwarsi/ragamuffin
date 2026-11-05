import slint
import os
import json
import threading
import queue
import datetime
from core.retriever import get_context, ask_ollama, get_all_sources
from core.indexer import build_index

CONFIG_FILE = "config.json"

class RagamuffinApp(slint.loader.ui.main_window.MainWindow):
    def __init__(self):
        super().__init__()
        self.history_file = "chat_history.json"
        
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        
        loaded_history = self.load_history()
        self.messages = slint.ListModel(loaded_history)
        self.load_anchor_files()

        # Load Vault Path from config
        self.config = self.load_config()
        self.vault_path = self.config.get("vault_path", "")

        # Thread-safe queue for UI updates
        self.ui_queue = queue.Queue()
        self.timer = slint.Timer()
        self.timer.start(slint.TimerMode.Repeated, datetime.timedelta(milliseconds=100), self.process_ui_queue)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {"vault_path": ""}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def process_ui_queue(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                if isinstance(task, tuple):
                    action, payload = task
                    if action == "notification":
                        self.notification = payload
                    elif action == "clear_notification":
                        self.notification = ""
                    elif action == "reload_anchors":
                        self.load_anchor_files()
        except queue.Empty:
            pass

    def load_anchor_files(self):
        sources = get_all_sources()
        anchor_list = [{"name": s, "selected": False} for s in sources]
        self.anchor_files = slint.ListModel(anchor_list)

    def load_history(self):
        with open(self.history_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_history(self):
        data = [{"role": m["role"], "content": m["content"]} for m in self.messages]
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @slint.callback
    def open_settings(self):
        self.vault_path = self.config.get("vault_path", "")
        self.settings_open = True

    @slint.callback
    def save_vault_path(self, path):
        self.config["vault_path"] = path
        self.save_config()
        self.vault_path = path
        self.ui_queue.put(("notification", "Vault path saved!"))
        threading.Timer(3.0, lambda: self.ui_queue.put(("clear_notification", None))).start()

    @slint.callback
    def toggle_anchor(self, file_name):
        new_list = []
        for f in self.anchor_files:
            if f["name"] == file_name:
                new_list.append({"name": f["name"], "selected": not f["selected"]})
            else:
                new_list.append({"name": f["name"], "selected": f["selected"]})
        self.anchor_files = slint.ListModel(new_list)

    @slint.callback
    def clear_anchors(self):
        new_list = [{"name": f["name"], "selected": False} for f in self.anchor_files]
        self.anchor_files = slint.ListModel(new_list)

    @slint.callback
    def send_message(self, text):
        self.is_loading = True
        self.current_input = ""
        self.messages.append({"role": "user", "content": text})
        
        selected_anchors = [f["name"] for f in self.anchor_files if f["selected"]]
        
        try:
            context, metadata = get_context(text, n_results=6, anchor_files=selected_anchors)
            answer = ask_ollama(text, context, temp=0.3)
        except Exception as e:
            answer = f"Error: {str(e)}"
        
        self.messages.append({"role": "assistant", "content": answer})
        self.save_history()
        self.is_loading = False

    @slint.callback
    def sync_vault(self):
        current_path = self.vault_path 

        if not current_path or not os.path.exists(current_path):
            self.ui_queue.put(("notification", "Error: Set a valid Vault Path in Settings first."))
            threading.Timer(4.0, lambda: self.ui_queue.put(("clear_notification", None))).start()
            return

        self.ui_queue.put(("notification", "Syncing vault... Check terminal for progress."))
        
        safe_queue = self.ui_queue
        
        def run_sync(path, q):
            try:
                count = build_index(path) 
                
                q.put(("reload_anchors", None))
                q.put(("notification", f"Sync Complete! Processed {count} files."))
                
                threading.Timer(3.0, lambda: q.put(("clear_notification", None))).start()
                
            except Exception as e:
                q.put(("notification", f"Sync failed: {str(e)}"))
                print(f"Error syncing: {e}")
                
        threading.Thread(target=run_sync, args=(current_path, safe_queue)).start()

if __name__ == "__main__":
    app = RagamuffinApp()
    app.run()