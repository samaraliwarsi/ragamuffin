import os
os.environ["SLINT_BACKEND"] = "winit-femtovg" # WINDOWS
# os.environ["SLINT_BACKEND"] = "winit-femtovg-wgpu" (WHEN ON MAC)
import slint
import json
import threading
import queue
import datetime
from core.retriever import get_context, ask_ollama_stream, get_all_sources
from core.indexer import build_index
import tkinter as tk
import re

CONFIG_FILE = "config.json"

def format_slint_markdown(text):
    text = re.sub(r'^#+\s*(.*)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*-\s*(.*)$', r'• \1', text, flags=re.MULTILINE)
    return text

class RagamuffinApp(slint.loader.ui.main_window.MainWindow):
    def __init__(self):
        super().__init__()
        self.streaming_content = ""
        self.history_file = "chat_history.json"
        
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        
        loaded_history = self.load_history()
        self.messages = slint.ListModel(loaded_history)
        self.load_anchor_files()

        self.config = self.load_config()
        self.default_prompt = """You are an expert lore keeper and creative writing partner for a novelist. Answer the user's question using ONLY the provided context from their notes. When brainstorming or ideating, separate canon facts from new ideas clearly."""
        self.vault_path = self.config.get("vault_path", "")
        self.system_prompt = self.config.get("system_prompt") or self.default_prompt
        self.mode = self.config.get("mode") or "Strict"
        self.keep_alive = self.config.get("keep_alive") or "5m"
        self.history_limit = str(self.config.get("history_limit", 10))

        self.ui_queue = queue.Queue()
        self.timer = slint.Timer()
        self.timer.start(slint.TimerMode.Repeated, datetime.timedelta(milliseconds=100), self.process_ui_queue)

    # ---- HELPER FOR SAFE LIST ACCESS ---
    def get_messages_as_dicts(self):
        result = []
        for m in self.messages:
            if hasattr(m, "role"):
                result.append({
                    "role": m.role, 
                    "content": m.content, 
                    "sources": getattr(m, "sources", "")
                })
            else:
                result.append({
                    "role": m.get("role", "user"), 
                    "content": m.get("content", ""), 
                    "sources": m.get("sources", "")
                })
        return result

    def get_anchor_name(self, f):
        return getattr(f, "name", f.get("name") if isinstance(f, dict) else "")

    def get_anchor_selected(self, f):
        return getattr(f, "selected", f.get("selected") if isinstance(f, dict) else False) 

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {}

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
                    elif action == "stream_start":
                        self.streaming_content = ""
                        self.messages.append({"role": "assistant", "content": "", "sources": payload})
                        self.is_loading = False
                    elif action == "stream_chunk":
                        self.streaming_content += payload
                        formatted = format_slint_markdown(self.streaming_content)
                        current_list = self.get_messages_as_dicts()
                        if current_list:
                            current_list[-1]["content"] = formatted
                            self.messages = slint.ListModel(current_list)
                    elif action == "stream_done":
                        self.save_history()
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
        data = self.get_messages_as_dicts()
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @slint.callback
    def open_settings(self):
        self.vault_path = self.config.get("vault_path", "")
        self.system_prompt = self.config.get("system_prompt") or self.default_prompt
        self.mode = self.config.get("mode") or "Strict"
        self.keep_alive = self.config.get("keep_alive") or "5m"
        self.history_limit = str(self.config.get("history_limit", 10))
        self.config["mode"] = self.mode
        self.config["keep_alive"] = self.keep_alive
        self.config["history_limit"] = int(self.history_limit)
        self.settings_open = True

    @slint.callback
    def save_settings(self, path, prompt, mode, keepalive, limit):
        self.config["vault_path"] = path
        self.config["system_prompt"] = prompt or self.default_prompt
        self.config["mode"] = mode or "Strict"
        self.config["keep_alive"] = keepalive or "5m"
        try:
            self.config["history_limit"] = int(limit)
        except:
            self.config["history_limit"] = 10

        self.save_config()
        
        self.vault_path = path
        self.system_prompt = self.config["system_prompt"]
        self.mode = self.config["mode"]
        self.keep_alive = self.config["keep_alive"]
        self.history_limit = str(self.config["history_limit"])
        
        self.ui_queue.put(("notification", "Settings saved!"))
        threading.Timer(3.0, lambda: self.ui_queue.put(("clear_notification", None))).start()

    @slint.callback
    def toggle_anchor(self, file_name):
        new_list = []
        for f in self.anchor_files:
            name = self.get_anchor_name(f)
            selected = self.get_anchor_selected(f)
            if name == file_name:
                new_list.append({"name": name, "selected": not selected})
            else:
                new_list.append({"name": name, "selected": selected})
        self.anchor_files = slint.ListModel(new_list)

    @slint.callback
    def clear_anchors(self):
        new_list = [{"name": self.get_anchor_name(f), "selected": False} for f in self.anchor_files]
        self.anchor_files = slint.ListModel(new_list)

    @slint.callback
    def copy_text(self, text):
        try:
            r = tk.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(text)
            r.update()
            r.destroy()
        except Exception as e:
            print(f"Failed to copy: {e}")

    @slint.callback
    def send_message(self, text):
        self.is_loading = True
        self.current_input = ""
        self.messages.append({"role": "user", "content": text, "sources": ""})
        
        current_list = self.get_messages_as_dicts()
        history_msgs = current_list[:-1]

        try: 
            limit = int(self.history_limit)
        except ValueError:
            limit = 10

        recent_history = history_msgs[-limit:] if limit > 0 else []
        history_payload = [{"role": m["role"], "content": m["content"]} for m in recent_history]
        
        selected_anchors = [self.get_anchor_name(f) for f in self.anchor_files if self.get_anchor_selected(f)]
        safe_queue = self.ui_queue
        mode = self.mode
        keep_alive = self.keep_alive if self.keep_alive else "5m" 
        system_prompt = self.system_prompt

        def run_query(query, anchors, hist, m, ka, sp, q):
            try:
                context, metadata = get_context(query, n_results=6, anchor_files=anchors)
                unique_sources = list(set(meta['source'] for meta in metadata))
                sources_str = ", ".join(unique_sources)
                
                q.put(("stream_start", sources_str))
                
                for chunk in ask_ollama_stream(query, context, hist, m, ka, sp):
                    q.put(("stream_chunk", chunk))
                
                q.put(("stream_done", None))
                
            except Exception as e:
                q.put(("stream_start", ""))
                q.put(("stream_chunk", f"Error: {str(e)}"))
                q.put(("stream_done", None))
                
        threading.Thread(
            target=run_query,
            args=(text, selected_anchors, history_payload, mode, keep_alive, system_prompt, safe_queue)
        ).start()
        
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