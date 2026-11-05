import slint
import os
import json
from core.retriever import get_context, ask_ollama

class RagamuffinApp(slint.loader.main_window.MainWindow):
    def __init__(self):
        super().__init__()
        self.history_file = "chat_history.json"
        
        # 1. Load history on startup (creates file if missing)
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        
        loaded_history = self.load_history()
        
        # Convert dict to Slint struct
        formatted_history = []
        for m in loaded_history:
            formatted_history.append({"role": m["role"], "content": m["content"]})
        
        self.messages = formatted_history

    def load_history(self):
        with open(self.history_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_history(self, new_messages):
        # Convert Slint struct to dict
        data = [{"role": m.role, "content": m.content} for m in new_messages]
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @slint.callback
    def send_message(self, text):
        self.is_loading = True
        
        # Add user message to UI
        new_messages = self.messages
        new_messages.append({"role": "user", "content": text})
        self.messages = new_messages
        self.current_input = ""
        
        # Run RAG
        try:
            context, metadata = get_context(text, n_results=6)
            answer = ask_ollama(text, context, temp=0.3)
        except Exception as e:
            answer = f"Error: {str(e)}"
        
        # Add AI message to UI
        new_messages.append({"role": "assistant", "content": answer})
        self.messages = new_messages
        
        # Save to disk
        self.save_history(new_messages)
        self.is_loading = False

    @slint.callback
    def open_settings(self):
        self.settings_open = True

if __name__ == "__main__":
    app = RagamuffinApp()
    app.run()