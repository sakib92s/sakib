from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import cv2
import requests
import tempfile
from kivy.lang import Builder
Builder.load_file('attendance.kv')

SERVER_IP = 'http://192.168.253.44:5000'  # Change to your Flask server IP

class LoginScreen(BoxLayout):
    def __init__(self, switch_screen_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.switch_screen_callback = switch_screen_callback

        self.add_widget(Label(text="Organization Login"))
        self.email = TextInput(hint_text="Email", multiline=False)
        self.password = TextInput(hint_text="Password", password=True, multiline=False)

        self.status_label = Label(text="")
        self.login_btn = Button(text="Login")
        self.login_btn.bind(on_press=self.login)

        self.add_widget(self.email)
        self.add_widget(self.password)
        self.add_widget(self.login_btn)
        self.add_widget(self.status_label)

    def login(self, instance):
        email = self.email.text
        password = self.password.text
        try:
            response = requests.post(f'{SERVER_IP}/login', data={'email': email, 'password': password})
            result = response.json()
            if result['status'] == 'success':
                self.switch_screen_callback()  # Switch to scanner screen
            else:
                self.status_label.text = "Invalid credentials"
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"

class FaceScanner(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.image = Image(size_hint=(1, 0.7))
        self.add_widget(self.image)

        self.status_label = Label(text="Click SCAN to mark attendance", size_hint=(1, 0.1))
        self.add_widget(self.status_label)

        self.scan_button = Button(text="SCAN", size_hint=(1, 0.2))
        self.scan_button.bind(on_press=self.capture_and_send)
        self.add_widget(self.scan_button)

        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update, 1.0 / 30.0)

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            buf = cv2.flip(frame, 0).tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.image.texture = texture

    def capture_and_send(self, instance):
        ret, frame = self.capture.read()
        if not ret:
            self.status_label.text = "Camera error!"
            return

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            cv2.imwrite(temp_file.name, frame)

        try:
            with open(temp_file.name, 'rb') as img:
                files = {'image': img}
                response = requests.post(f'{SERVER_IP}/scan', files=files)
            result = response.json()

            if result['status'] == 'matched':
                self.status_label.text = f"[✔] {result['name']}: Attendance Marked"
            elif result['status'] == 'unmatched':
                self.status_label.text = "[✖] Face not matched"
            elif result['status'] == 'not_registered':
                self.status_label.text = "[!] Face found but not in DB"
            else:
                self.status_label.text = "[!] Error: " + result.get('message', '')
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"

class AttendanceApp(App):
    def build(self):
        self.root_widget = BoxLayout()
        self.show_login()
        return self.root_widget

    def show_login(self):
        self.root_widget.clear_widgets()
        self.root_widget.add_widget(LoginScreen(self.show_scanner))

    def show_scanner(self):
        self.root_widget.clear_widgets()
        self.root_widget.add_widget(FaceScanner())

if __name__ == '__main__':
    AttendanceApp().run()