import requests
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
import threading

# Azure OpenAI 설정
endpoint = "https://eueastproject3-team2.openai.azure.com/"
deployment = "project3-team2-gpt-4o"
subscription_key = "a83ed49c38b54298bb690a721a87599b"

# NanumGothic 폰트 등록
LabelBase.register(name='NanumGothic', fn_regular='NanumGothic.ttf')

# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, callback):
    headers = {
        'Content-Type': 'application/json',
        'api-key': subscription_key,
    }

    data = {
        'messages': [{'role': 'user', 'content': message}],
    }

    url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version=2023-03-15-preview"

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            Clock.schedule_once(lambda dt: callback(content), 0)
        else:
            Clock.schedule_once(lambda dt: callback(f'Error: {response.status_code} - Unable to fetch response from Azure OpenAI.'), 0)
    except Exception as e:
        Clock.schedule_once(lambda dt: callback(f'Error: {str(e)}'), 0)

# 메인 화면에서 캐릭터를 선택하는 화면 (MainScreen)
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        main_layout = BoxLayout(orientation="horizontal")

        char_select_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1))

        group_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        group_label = Label(text="Eruza", font_name='NanumGothic', size_hint_x=0.3, font_size="20sp")
        group_message = Label(text="안녕 우린 Eruza야", font_name='NanumGothic', size_hint_x=0.7, font_size="20sp")
        group_layout.add_widget(group_label)
        group_layout.add_widget(group_message)
        char_select_layout.add_widget(group_layout)

        self.char_buttons = [
            ("Wynter", "최근 대화내용"),
            ("Erika", "최근 대화내용"),
            ("Min", "최근 대화내용"),
            ("J.K", "최근 대화내용"),
            ("Luis", "최근 대화내용"),
            ("NEXA", "최근 대화내용"),
        ]

        for char_name, greeting in self.char_buttons:
            char_button_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=80)
            btn_icon = Button(text=f"{char_name}\nicon", size_hint_x=0.3, font_name='NanumGothic')
            btn_icon.bind(on_press=lambda instance, char_name=char_name: self.switch_to_chat(char_name))
            btn_text = Label(text=f"{char_name}\n{greeting}", font_name='NanumGothic', size_hint_x=0.7, halign='left')
            char_button_layout.add_widget(btn_icon)
            char_button_layout.add_widget(btn_text)
            char_select_layout.add_widget(char_button_layout)

        main_layout.add_widget(char_select_layout)
        self.add_widget(main_layout)

    def switch_to_chat(self, char_name):
        chat_screen = self.manager.get_screen('chat')
        chat_screen.update_character(char_name)
        self.manager.current = 'chat'

# 대화 화면 (ChatScreen)
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.chat_history = {}

        chat_layout = BoxLayout(orientation='vertical')

        top_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        back_button = Button(text="<", size_hint=(0.1, 1), font_size="20sp", font_name='NanumGothic')
        back_button.bind(on_press=self.go_back)
        self.character_label = Label(text="캐릭터를 선택하세요", size_hint=(0.9, 1), font_size="24sp", font_name='NanumGothic', halign='center', valign='middle')

        top_layout.add_widget(back_button)
        top_layout.add_widget(self.character_label)
        chat_layout.add_widget(top_layout)

        self.scroll_view = ScrollView(size_hint=(1, 0.8))
        self.message_layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=10, spacing=10)
        self.message_layout.bind(minimum_height=self.message_layout.setter('height'))
        self.scroll_view.add_widget(self.message_layout)
        chat_layout.add_widget(self.scroll_view)

        input_layout = BoxLayout(size_hint=(1, 0.1))
        self.text_input = TextInput(hint_text="메시지를 입력하세요...", multiline=False, font_name='NanumGothic')
        self.text_input.bind(on_text_validate=self.send_message)
        send_button = Button(text="전송", size_hint=(0.2, 1), font_name='NanumGothic')
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)
        chat_layout.add_widget(input_layout)

        self.add_widget(chat_layout)

    def update_character(self, char_name):
        self.character_label.text = char_name
        self.current_character = char_name

        self.message_layout.clear_widgets()

        if char_name in self.chat_history:
            for message in self.chat_history[char_name]:
                self.add_message(message)

    def go_back(self, instance):
        self.manager.current = 'main'

    def send_message(self, instance):
        user_message = self.text_input.text
        if user_message:
            self.add_message(f"나: {user_message}", align='right')
            if self.current_character not in self.chat_history:
                self.chat_history[self.current_character] = []
            self.chat_history[self.current_character].append(f"나: {user_message}")

            self.text_input.text = ""
            self.text_input.focus = True  # 전송 후 입력창에 바로 포커스 유지

            threading.Thread(target=get_openai_response, args=(user_message, self.receive_message)).start()

    def receive_message(self, bot_message):
        self.add_message(f"{self.current_character}: {bot_message}", align='left')
        self.chat_history[self.current_character].append(f"{self.current_character}: {bot_message}")

    def add_message(self, message, align='left'):
        # 왼쪽과 오른쪽 정렬에 따라 BoxLayout을 달리 설정
        message_layout = BoxLayout(orientation='horizontal', size_hint_y=None, padding=10)

        if align == 'left':
            label = Label(text=message, size_hint=(0.8, None), font_name='NanumGothic', halign='left', valign='middle', text_size=(self.width * 0.75, None))
            message_layout.add_widget(label)
            message_layout.add_widget(Label(size_hint_x=0.2))  # 오른쪽에 빈 공간 추가
        else:
            message_layout.add_widget(Label(size_hint_x=0.2))  # 왼쪽에 빈 공간 추가
            label = Label(text=message, size_hint=(0.8, None), font_name='NanumGothic', halign='right', valign='middle', text_size=(self.width * 0.75, None))
            message_layout.add_widget(label)

        label.bind(size=self.update_text_size)
        label.bind(texture_size=label.setter('size'))
        self.message_layout.add_widget(message_layout)

        self.message_layout.height += label.texture_size[1]

        self.scroll_view.scroll_to(label)

    def update_text_size(self, instance, value):
        instance.text_size = (self.width * 0.75, None)  # 너비의 75%를 사용하여 텍스트 크기를 조정

class TestApp(App):
    def build(self):
        sm = ScreenManager()
        main_screen = MainScreen(name='main')
        chat_screen = ChatScreen(name='chat')
        sm.add_widget(main_screen)
        sm.add_widget(chat_screen)
        return sm

if __name__ == "__main__":
    TestApp().run()
