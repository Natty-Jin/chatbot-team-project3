from kivy.uix.image import Image
import os
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
from kivy.core.window import Window
import threading
import docx
import PyPDF2
import json
import datetime
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import ScreenManager, FadeTransition
import sys

# Azure OpenAI 설정
endpoint = "https://eueastproject3-team2.openai.azure.com/"
deployment = "project3-team2-gpt-4o"
subscription_key = "a83ed49c38b54298bb690a721a87599b"

# 변환된 폰트 등록
myfont = "SUIT-Regular"
CS_Chatbot_name = "nepoiA"

# NanumGothic 폰트 등록
LabelBase.register(name=myfont, fn_regular=f"{myfont}.ttf")


# 파일에서 내용을 읽어오는 함수들
def read_txt_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def read_docx_file(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def read_pdf_file(file_path):
    with open(file_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])


def read_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        return read_txt_file(file_path)
    elif ext == ".docx":
        return read_docx_file(file_path)
    elif ext == ".pdf":
        return read_pdf_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# 그라운딩 데이터 폴더에서 모든 파일을 읽어와서 시스템 메시지에 추가
def load_grounding_data(folder_path):
    grounding_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith((".txt", ".pdf", ".docx")):
                grounding_files.append(os.path.join(root, file))

    grounding_data = {}
    for file_path in grounding_files:
        try:
            file_content = read_file(file_path)
            persona_name = os.path.splitext(os.path.basename(file_path))[0]
            grounding_data[persona_name] = file_content
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")

    return grounding_data


# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, CS_Chatbot_name, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": subscription_key,
    }

    # 그라운딩 데이터를 시스템 메시지로 포함
    system_message = f"""너는 {CS_Chatbot_name}라는 챗봇이야 .사용자의 질문 정보에 맞는 답변을 사용해야해, 이모티콘은 절대 사용하지마!
                        CS 챗봇답게 소비자에게 아주 친절하게 답변해 주세요. 어떤 일이 있어도 CS 챗봇은 반드시 친절하게 대답해야해!
                        사용자가 질문하는 것에 대해서 답변은 사람처럼 해줘야해 사용자의 질문사항의 답변을 최대한 간추려서 2문장까지만 말해줘
                        다음은 사용자의 질문에 따른 질문과 답변 양식이야 :\n\n{grounding_data}\n\n
                        답변 마지막에는 !!를 붙여 좀 더 생기있게 해줘
                        """

    data = {
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
            {"role": "user", "content": message},
        ],
    }

    url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version=2024-05-01-preview"

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            Clock.schedule_once(lambda dt: callback(content), 0)
        else:
            Clock.schedule_once(
                lambda dt: callback(
                    f"Error: {response.status_code} - Unable to fetch response from Azure OpenAI."
                ),
                0,
            )
    except Exception as e:
        Clock.schedule_once(lambda dt: callback(f"Error: {str(e)}"), 0)


# 키보드 이벤트 핸들링 (상단으로 이동)
def _on_key_down(window, key, _scancode, _codepoint, modifiers):
    if key == 13:  # Enter key
        if "shift" in modifiers or "ctrl" in modifiers:
            # Shift 또는 Ctrl + Enter -> 줄바꿈 추가
            window.children[0].children[0].user_input.text += "\n"
        else:
            # Enter만 눌렀을 때 -> 메시지 전송
            window.children[0].children[0].send_message(window.children[0].children[0].send_button)
        return True
    return False


# 챗봇 UI 구현을 위한 클래스
class CSChatbotApp(App):
    def build(self):
        self.title = "CS Chatbot - nopoiA"
        Window.size = (400, 600)  # 기본 창 크기 설정
        self.manager = ScreenManager(transition=FadeTransition())

        self.chat_screen = ChatScreen(name="chat")
        self.manager.add_widget(self.chat_screen)

        return self.manager


# 채팅 화면 클래스
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)

        # 전체 레이아웃 설정
        self.layout = BoxLayout(orientation="vertical", padding=10, spacing=10)

        # 스크롤 가능한 채팅 창 구현
        self.chat_scroll = ScrollView(size_hint=(1, 0.8))
        self.chat_layout = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=5
        )
        self.chat_layout.bind(minimum_height=self.chat_layout.setter("height"))
        self.chat_scroll.add_widget(self.chat_layout)

        # 사용자 입력 및 버튼 영역
        self.input_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        self.user_input = TextInput(
            size_hint=(0.8, 1),
            multiline=False,
            hint_text="광시문제를 입력하세요...",
            font_name=myfont,
        )
        self.user_input.bind(text=self.on_text)
        self.send_button = Button(text="전송", size_hint=(0.2, 1), font_name=myfont)
        self.send_button.bind(on_release=self.send_message)
        self.input_layout.add_widget(self.user_input)
        self.input_layout.add_widget(self.send_button)

        # 뒤로가기 버튼 추가
        self.go_back_button = Button(
            text="뒤로가기", size_hint=(1, 0.1), font_name=myfont
        )
        self.go_back_button.bind(on_release=self.go_back)

        # 레이아웃에 추가
        self.layout.add_widget(self.chat_scroll)
        self.layout.add_widget(self.input_layout)
        self.layout.add_widget(self.go_back_button)
        self.add_widget(self.layout)

        # 배경 색상 설정
        with self.canvas.before:
            Color(0.53, 0.81, 0.98, 1)  # 하늘색 배경
            self.rect = Rectangle(size=Window.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        # 키보드 및 뒤로가기 버튼 핸들러 추가
        Window.bind(on_key_down=_on_key_down)

        # 유저 입력 잠금 플래그
        self.user_input_locked = False

    # 배경 업데이트 함수
    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    # 사용자 메시지 전송 처리
    def send_message(self, instance):
        if self.user_input_locked:
            return

        user_message = self.user_input.text
        if user_message:
            self.display_message(user_message, "user")
            self.user_input.text = ""
            self.user_input_locked = True  # 유저 입력 잠금

            # 봇 응답 스레딩 처리 (응답 지연 시 UI 프리징 방지)
            threading.Thread(
                target=self.generate_bot_response, args=(user_message,)
            ).start()

    # 챗봇 응답 생성 및 표시
    def generate_bot_response(self, user_message):
        # Azure OpenAI API 호출하여 응답 생성
        grounding_data = load_grounding_data("Cahtbotgrounding-data/nepoiA.pdf")
        get_openai_response(
            user_message, CS_Chatbot_name, grounding_data, self.display_message_callback
        )

    # 챗봇 응답 콜백 함수
    def display_message_callback(self, response_message):
        self.display_message(response_message, "bot")
        self.user_input_locked = False  # 유저 입력 잠금 해제

    # 메시지 표시
    def display_message(self, message, sender):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        if sender == "user":
            msg_label = Label(
                text=f"나: {message}\n{current_time}",
                size_hint_y=None,
                halign="right",
                valign="middle",
                padding=(10, 10),
                font_name=myfont,
            )
            msg_label.bind(size=self.update_label_height)
            msg_label.text_size = (
                self.chat_scroll.width * 0.7,
                None,
            )  # 오른쪽에 더 가까이 위치하도록
            msg_label.color = (0, 0, 0, 1)  # 글씨는 검은색으로 설정
            msg_label.canvas.before.clear()
            with msg_label.canvas.before:
                Color(0.8, 0.8, 0.8, 1)
                Rectangle(
                    pos=msg_label.pos,
                    size=msg_label.size,
                    radius=[(10, 10), (10, 10), (10, 10), (10, 10)],
                )
            user_layout = BoxLayout(
                orientation="horizontal", size_hint_y=None, spacing=5, padding=(50, 0, 0, 0)
            )
            user_layout.add_widget(msg_label)
            user_layout.bind(minimum_height=user_layout.setter("height"))
            self.chat_layout.add_widget(user_layout)
        elif sender == "bot":
            bot_layout = BoxLayout(
                orientation="horizontal", size_hint_y=None, spacing=5, padding=(0, 0, 50, 0)
            )
            msg_label = Label(
                text=f"{CS_Chatbot_name}: {message}\n{current_time}",
                size_hint_y=None,
                halign="left",
                valign="middle",
                padding=(5, 5),
                font_name=myfont,
            )
            msg_label.bind(size=self.update_label_height)
            msg_label.text_size = (self.chat_scroll.width * 0.55, None)
            msg_label.color = (0, 0, 0, 1)  # 글씨는 검은색으로 설정
            msg_label.canvas.before.clear()
            with msg_label.canvas.before:
                Color(0.2, 0.6, 0.86, 1)
                Rectangle(
                    pos=msg_label.pos,
                    size=msg_label.size,
                    radius=[(10, 10), (10, 10), (10, 10), (10, 10)],
                )
            bot_layout.add_widget(msg_label)

            bot_layout.bind(minimum_height=bot_layout.setter("height"))
            self.chat_layout.add_widget(bot_layout)

        self.chat_scroll.scroll_y = 0

    # 메시지 라벨 높이 업데이트
    def update_label_height(self, label, *args):
        label.height = label.texture_size[1] + 20
        label.text_size = (
            (self.chat_scroll.width * 0.7, None)
            if label.text.startswith("나:")
            else (self.chat_scroll.width * 0.55, None)
        )

    # 사용자 입력 텍스트 변경 시 자동 줄바꿈 처리
    def on_text(self, instance, value):
        instance.text_size = (instance.width, None)

    # 뒤로가기 버튼 처리 함수
    def go_back(self, _instance):
        sys.exit()  # 프로그램을 종료하도록 변경


if __name__ == "__main__":
    CSChatbotApp().run()
