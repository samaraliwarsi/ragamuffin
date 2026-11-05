import slint
import os
import json
import threading
import queue
import datetime
from core.retriever import get_context, ask_ollama, get_all_sources
from core.indexer import build_index

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

        # Thread-safe queue for communicating between background threads and UI
        self.ui_queue = queue.Queue()
        
        # Poll the queue every 100ms using a Slint Timer
        self.timer = slint.Timer()
        self.timer.start(slint.TimerMode.Repeated, datetime.timedelta(milliseconds=100), self.process_ui_queue)

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
    def open_settings(self):
        self.settings_open = True
        
    @slint.callback
    def sync_vault(self):
        # Show immediate feedback
        self.ui_queue.put(("notification", "Syncing vault... Please wait."))
        
        def run_sync():
            try:
                count = build_index()
                # Put results into the queue for the main thread
                self.ui_queue.put(("reload_anchors", None))
                self.ui_queue.put(("notification", f"Sync Complete! Indexed {count} chunks."))
                
                # Clear notification after 3 seconds
                threading.Timer(3.0, lambda: self.ui_queue.put(("clear_notification", None))).start()
                
            except Exception as e:
                self.ui_queue.put(("notification", "Sync failed. Check terminal."))
                print(f"Error syncing: {e}")
                
        threading.Thread(target=run_sync).start()

if __name__ == "__main__":
    app = RagamuffinApp()
    app.run()