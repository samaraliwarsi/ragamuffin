import slint
import os
import json
from core.retriever import get_context, ask_ollama
from core.indexer import build_index
import threading

class RagamuffinApp(slint.loader.ui.main_window.MainWindow):
    def __init__(self):
        super().__init__()
        self.history_file = "chat_history.json"
        
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        
        loaded_history = self.load_history()
        self.messages = slint.ListModel(loaded_history)

    def load_history(self):
        with open(self.history_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_history(self):
        data = [{"role": m["role"], "content": m["content"]} for m in self.messages]
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @slint.callback
    def send_message(self, text):
        self.is_loading = True
        self.current_input = ""
        self.messages.append({"role": "user", "content": text})
        
        try:
            context, metadata = get_context(text, n_results=6)
            answer = ask_ollama(text, context, temp=0.3)
        except Exception as e:
            answer = f"Error: {str(e)}"
        
        self.messages.append({"role": "assistant", "content": answer})
        self.save_history()
        self.is_loading = False

    @slint.callback
    def open_settings(self):
        print("Opening settings...") # Debug print
        self.settings_open = True
        
    @slint.callback
    def sync_vault(self):
        print("Starting vault sync in background...")
        
        def run_sync():
            try:
                count = build_index()
                print(f"Successfully indexed {count} chunks!")
            except Exception as e:
                print(f"Error syncing: {e}")
                
        # Run in a separate thread so the UI doesn't freeze
        threading.Thread(target=run_sync).start()
    # -------------------------

if __name__ == "__main__":
    app = RagamuffinApp()
    app.run()