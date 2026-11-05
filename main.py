import slint

# Slint's auto-loader finds app-window.slint in the current directory
class App(slint.loader.app_window.AppWindow):
    @slint.callback
    def request_increase_value(self):
        self.counter = self.counter + 1

app = App()
app.run()