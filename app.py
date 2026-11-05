import slint
import os
import json
from core.retriever import get_context, ask_ollama

class RagamuffinApp(slint.loader.ui.main_window.MainWindow):
    def __init__(self):
        super().__init__()
        self.history_file = "chat_history.json"
        
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        
        loaded_history = self.load_history()
        
        # Wrap the list of dictionaries in a Slint ListModel
        self.messages = slint.ListModel(loaded_history)

    def load_history(self):
        with open(self.history_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_history(self):
        # Get the data back out of the model for saving
        data = [{"role": m["role"], "content": m["content"]} for m in self.messages]
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @slint.callback
    def send_message(self, text):
        self.is_loading = True
        self.current_input = ""
        
        # 1. Append user message (plain dict is fine)
        self.messages.append({"role": "user", "content": text})
        
        # 2. Run RAG
        try:
            context, metadata = get_context(text, n_results=6)
            answer = ask_ollama(text, context, temp=0.3)
        except Exception as e:
            answer = f"Error: {str(e)}"
        
        # 3. Append AI message
        self.messages.append({"role": "assistant", "content": answer})
        
        # 4. Save and finish
        self.save_history()
        self.is_loading = False

    @slint.callback
    def open_settings(self):
        self.settings_open = True

if __name__ == "__main__":
    app = RagamuffinApp()
    app.run()