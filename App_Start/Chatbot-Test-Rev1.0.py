import os
import requests
import threading
import json
import datetime
from kivy.uix.image import Image  # 이미지를 표시하기 위한 Image 위젯 가져오기
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import FadeTransition

# 사용자 정의 폰트 등록

myfont = "SUIT-Regular"
LabelBase.register(name=myfont, fn_regular="SUIT-Regular.ttf")


# Azure OpenAI 설정
endpoint = "https://eueastproject3-team2.openai.azure.com/"
deployment = "project3-team2-gpt-4o"
subscription_key = "a83ed49c38b54298bb690a721a87599b"


def load_grounding_data(folder_path):
    grounding_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith((".txt", ".pdf", ".docx")):
                grounding_files.append(os.path.join(root, file))

    grounding_data = {}
    for file_path in grounding_files:
        try:
            file_content = self.read_file(file_path)
            persona_name = os.path.splitext(os.path.basename(file_path))[0]
            grounding_data[persona_name] = file_content
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")

    return grounding_data


def get_openai_response(user_message, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": subscription_key,
    }

    # 그라운딩 데이터를 시스템 메시지로 포함시키기
    system_message = f"""CS 챗봇답게 소비자에게 아주 친절하게 답변해 주세요. 어떤 일이 있어도 CS 챗봇은 반드시 친절하게 대답해야 합니다! 
    사용자가 질문하는 것에 대해 답변은 사람처럼 해주고, 사용자의 질문사항에 대한 답변을 최대한 간추려서 2문장까지만 말해줘요.
    이모티콘은 사용하지 말아 주세요. 이 페르소나의 정보는 다음과 같습니다:

{grounding_data}

"""

    data = {
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
            {"role": "user", "content": user_message},
        ]
    }

    url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version=2024-05-01-preview"

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            # 메시지를 추가할 때 누가 보냈는지 명시 (여기서는 'nepoiA')
            Clock.schedule_once(lambda dt: callback("nepoiA", content), 0)
        else:
            Clock.schedule_once(
                lambda dt: callback(
                    "Error", f"Error: {response.status_code} - Unable to fetch response from Azure OpenAI."
                ),
                0,
            )
    except Exception as e:
        Clock.schedule_once(lambda dt: callback("Error", f"Error: {str(e)}"), 0)

# 화면 관리자
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 메인 레이아웃 설정
        layout = BoxLayout(orientation="vertical")

        # 챗봇의 이름과 이미지를 포함한 헤더 추가
        header = BoxLayout(orientation="horizontal", size_hint_y=0.08)
        back_button = Button(text="<", size_hint_x=0.1)
        back_button.bind(on_press=self.go_back)
        header.add_widget(back_button)
        self.bot_label = Label(text="nepoiA", font_name=myfont, font_size=24)
        header.add_widget(self.bot_label)

        layout.add_widget(header)

        # 채팅 메시지를 위한 ScrollView
        self.scroll_view = ScrollView(size_hint=(1, 0.75))
        self.chat_layout = BoxLayout(
            orientation="vertical", size_hint_y=None, padding=[10, 10, 10, 10]
        )
        self.chat_layout.bind(minimum_height=self.chat_layout.setter("height"))
        self.scroll_view.add_widget(self.chat_layout)
        layout.add_widget(self.scroll_view)

        # 메시지 입력 상자
        input_layout = BoxLayout(size_hint=(1, 0.1))
        self.text_input = TextInput(
            hint_text="매직을 입력하세요...",
            multiline=True,
            font_name=myfont,
            size_hint_x=0.8,
            input_type="text",
            background_color=(1, 1, 1, 1),  # 입력창 배경을 하울색으로 설정
            foreground_color=(0, 0, 0, 1),  # 입력 텍스트를 객정색으로 설정
            hint_text_color=(0.5, 0.5, 0.5, 1),  # 히트 텍스트를 회색으로 설정
            write_tab=False,  # Tab 키를 누라도 입력창에서 커서가 유지되도록 함
        )
        send_button = Button(
            text="전송",
            size_hint=(0.2, 1),
            font_name=myfont,
        )
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)

        layout.add_widget(input_layout)
        self.add_widget(layout)

        # 배경 색상을 흰색으로 설정
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

        # 키보드 이벤트 바인딩
        Window.bind(on_key_down=self._on_key_down)

        # 초기 인사 메시지
        Clock.schedule_once(
            lambda dt: self.add_chat_message(
                "nepoiA",
                "안녕하세요! 저는 버츠얼 아이돌 그룹 nepoiA를 대표하는 CS 챟번입니다! \n어디서 도움을 드린 것일까요?",
                align="left",
            )
        )

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if key == 13:  # Enter key
            if "shift" in modifiers or "ctrl" in modifiers:
                # Shift 또는 Ctrl + Enter -> 새 줄 추가
                self.text_input.text += "\n"
            else:
                # Enter 키만 눌렀을 때 -> 메시지 전송
                if (
                    not hasattr(self, "waiting_for_response")
                    or not self.waiting_for_response
                ):
                    self.send_message(None)
            return True
        return False

    def go_back(self, instance):
        App.get_running_app().root.current = "menu"

    def send_message(self, instance):
        user_message = self.text_input.text.strip()
        if user_message:
            self.add_chat_message("나", user_message, align="right")
            self.text_input.text = ""

            # 전역 함수 호출 시 self를 사용하지 않도록 수정
            threading.Thread(
                target=get_openai_response,
                args=(
                    user_message,
                    load_grounding_data(
                        "Chatbotgrounding-data"
                    ),  # self.load_grounding_data -> load_grounding_data로 수정
                    self.add_chat_message,
                ),
            ).start()

    def add_chat_message(self, sender, message, align="left"):
        time_str = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        message_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, padding=[10, 5], spacing=10
        )

        if align == "left":
            message_layout.padding = [20, 5, 40, 5]
        else:
            message_layout.padding = [40, 5, 20, 5]

        if sender == "nepoiA":
            icon_source = "chatbot-data/chatbot.png"
        else:
            icon_source = None

        if icon_source:
            icon = Image(source=icon_source, size_hint=(0.2, None), height=90)
            if align == "left":
                message_layout.add_widget(icon)

        label = Label(
            text=f"[b]{sender}[/b] ({time_str}):\n{message}",
            markup=True,
            size_hint_y=None,
            font_name=myfont,
            halign=align,
            valign="middle",
            color=(0, 0, 0, 1),  # 그라자색을 객정색으로 설정
        )
        label.bind(size=label.setter("text_size"))

        if align == "left":
            message_layout.add_widget(label)
            message_layout.add_widget(Label(size_hint_x=0.2))
        else:
            message_layout.add_widget(Label(size_hint_x=0.2))
            message_layout.add_widget(label)

        self.chat_layout.add_widget(message_layout)
        self.chat_layout.height += message_layout.height + 20

        # 새 메시지가 추가될 때마다 아래로 스크롤
        Clock.schedule_once(
            lambda dt: self.scroll_view.scroll_to(message_layout), 0.001
        )

    def _update_message_height(self, instance, size):
        instance.parent.height = size[1] + 20


class ChatbotApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(ChatScreen(name="chat"))
        return sm


if __name__ == "__main__":
    ChatbotApp().run()
