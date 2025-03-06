from kivy.uix.image import Image  # 이미지를 표시하기 위해 Image 위젯을 추가
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
import threading
import os
import docx
import PyPDF2
import json
import pdfplumber
import datetime


# Azure OpenAI 설정
endpoint = "https://eueastproject3-team2.openai.azure.com/"
deployment = "project3-team2-gpt-4o"
subscription_key = "a83ed49c38b54298bb690a721a87599b"

# NanumGothic 폰트 등록
LabelBase.register(name="NanumGothic", fn_regular="NanumGothic.ttf")


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
            # print(f"Successfully added content from {file_path}") # 터미널에서 PDF로 읽히니깐 테스트 아니면 사용 금지
            # print(f"Content of {persona_name}: {file_content}")  # 읽은 데이터를 로그로 출력하여 확인
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")

    return grounding_data


# 대화 기록을 파일에 저장하는 함수
def save_conversation(persona, history):
    filename = f"conversation_{persona}.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=4)


# 파일에서 대화 기록을 불러오는 함수
def load_conversation(persona):
    filename = f"conversation_{persona}.json"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    return []


# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, char_name, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": subscription_key,
    }

    # 그라운딩 데이터를 시스템 메시지로 포함
    system_message = f"너는 {char_name}라는 페르소나야. 너는 이모티콘을 쓰지 않아. 이 페르소나의 정보는 다음과 같아:\n\n{grounding_data}\n\n"
    # print(f"System message: {system_message}")  # 시스템 메시지 출력

    data = {
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },  # 시스템 메시지에 그라운딩 데이터 포함
            {"role": "user", "content": message},
        ]
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


# 메인 화면에서 캐릭터를 선택하는 화면 (MainScreen)
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        main_layout = BoxLayout(orientation="horizontal")

        char_select_layout = BoxLayout(orientation="vertical", size_hint=(0.3, 1))

        group_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        group_label = Label(
            text="Eruza", font_name="NanumGothic", size_hint_x=0.3, font_size="20sp"
        )
        group_message = Label(
            text="안녕 우린 Eruza야",
            font_name="NanumGothic",
            size_hint_x=0.7,
            font_size="20sp",
        )
        group_layout.add_widget(group_label)
        group_layout.add_widget(group_message)
        char_select_layout.add_widget(group_layout)

        # 캐릭터 버튼과 해당 아이콘 연결
        self.char_buttons = [
            ("Wynter", "최근 대화내용"),
            ("Erika", "최근 대화내용"),
            ("Min", "최근 대화내용"),
            ("J.K", "최근 대화내용"),
            ("Luis", "최근 대화내용"),
            ("NEXA", "최근 대화내용"),
        ]

        for char_name, greeting in self.char_buttons:
            char_button_layout = BoxLayout(
                orientation="horizontal", size_hint_y=None, height=80
            )

            # 아이콘 경로 정의
            icon_path = os.path.join("Icon-data", char_name, "Luis.png")

            # 이미지 경로 및 존재 여부를 터미널에 출력
            print(f"Checking icon for {char_name} at {icon_path}")
            if os.path.exists(icon_path):
                print(f"Image found for {char_name} at {icon_path}")
                btn_icon = Image(source=icon_path, size_hint_x=0.3)
            else:
                print(f"Image not found for {char_name}")
                # 이미지가 없을 경우 기본 텍스트 버튼을 표시
                btn_icon = Button(
                    text=f"{char_name}\nicon", size_hint_x=0.3, font_name="NanumGothic"
                )

            # 버튼을 누르면 해당 캐릭터의 채팅 화면으로 전환
            btn_icon.bind(
                on_press=lambda instance, char_name=char_name: self.switch_to_chat(
                    char_name
                )
            )
            btn_text = Label(
                text=f"{char_name}\n{greeting}",
                font_name="NanumGothic",
                size_hint_x=0.7,
                halign="left",
            )
            char_button_layout.add_widget(btn_icon)
            char_button_layout.add_widget(btn_text)
            char_select_layout.add_widget(char_button_layout)

        main_layout.add_widget(char_select_layout)
        self.add_widget(main_layout)

    def switch_to_chat(self, char_name):
        chat_screen = self.manager.get_screen("chat")
        chat_screen.update_character(char_name)
        self.manager.current = "chat"


# 대화 화면 (ChatScreen)
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.chat_history = {}
        self.current_character = None
        self.grounding_data = load_grounding_data(
            "grounding-data"
        )  # Load personas on app start

        chat_layout = BoxLayout(orientation="vertical")

        top_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        back_button = Button(
            text="<", size_hint=(0.1, 1), font_size="20sp", font_name="NanumGothic"
        )
        back_button.bind(on_press=self.go_back)
        self.character_label = Label(
            text="캐릭터를 선택하세요",
            size_hint=(0.9, 1),
            font_size="24sp",
            font_name="NanumGothic",
            halign="center",
            valign="middle",
        )

        top_layout.add_widget(back_button)
        top_layout.add_widget(self.character_label)
        chat_layout.add_widget(top_layout)

        self.scroll_view = ScrollView(size_hint=(1, 0.8))
        self.message_layout = BoxLayout(
            orientation="vertical", size_hint_y=None, padding=10, spacing=10
        )
        self.message_layout.bind(minimum_height=self.message_layout.setter("height"))
        self.scroll_view.add_widget(self.message_layout)
        chat_layout.add_widget(self.scroll_view)

        input_layout = BoxLayout(size_hint=(1, 0.1))
        self.text_input = TextInput(
            hint_text="메시지를 입력하세요...", multiline=False, font_name="NanumGothic"
        )
        self.text_input.bind(
            on_text_validate=self.send_message
        )  # 이곳에서 instance 전달
        send_button = Button(text="전송", size_hint=(0.2, 1), font_name="NanumGothic")
        send_button.bind(on_press=self.send_message)  # on_press로 instance 전달
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)
        chat_layout.add_widget(input_layout)

        self.add_widget(chat_layout)

    def update_character(self, char_name):
        self.character_label.text = char_name
        self.current_character = char_name

        # 대화 기록을 지우고 새 대화를 시작하기 전에 대화 내용 불러오기
        self.message_layout.clear_widgets()

        # 기존 대화 내용을 불러와서 추가
        if char_name in self.chat_history:
            for message in self.chat_history[char_name]:
                self.add_message(message)

            # 모든 대화 메시지를 추가한 후에 '지난 대화 기록' 구분선을 하단에 추가
            self.add_separator("지난 대화 기록")

    def add_separator(self, text):
        separator_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=40
        )
        separator_label = Label(
            text=text,
            size_hint=(1, None),
            font_name="NanumGothic",
            font_size="18sp",
            halign="center",
            valign="middle",
            color=(1, 1, 1, 0.8),  # 회색으로 표시
            text_size=(self.width, None),  # 텍스트가 중앙 정렬되도록 너비를 지정
        )
        separator_layout.add_widget(separator_label)

        # 위젯들 간의 간격을 추가하기 위한 spacing 설정
        self.message_layout.spacing = 50  # 위젯들 간의 간격을 50으로 설정

        self.message_layout.add_widget(separator_layout)
        self.message_layout.height += 40  # 고정된 높이만큼 레이아웃 높이를 증가

        # 구분선이 추가된 후 스크롤이 하단으로 이동하도록 설정
        self.scroll_view.scroll_to(separator_layout)

    def go_back(self, instance):
        self.manager.current = "main"

    def send_message(self, instance):  # 클래스 내부에 있어야 함
        user_message = self.text_input.text
        if user_message:
            self.add_message(f"나: {user_message}", align="right")
            if self.current_character not in self.chat_history:
                self.chat_history[self.current_character] = []
            self.chat_history[self.current_character].append(f"나: {user_message}")

            self.text_input.text = ""
            self.text_input.focus = True  # 전송 후 입력창에 바로 포커스 유지

            # 페르소나에 따른 그라운딩 데이터 적용
            grounding_data = self.grounding_data.get(self.current_character, "")

            # GPT 호출을 비동기로 처리
            threading.Thread(
                target=get_openai_response,
                args=(
                    user_message,
                    self.current_character,
                    grounding_data,
                    self.receive_message,
                ),  # grounding_data 전달
            ).start()

    def receive_message(self, bot_message):  # self로 호출
        self.add_message(f"{self.current_character}: {bot_message}", align="left")
        self.chat_history[self.current_character].append(
            f"{self.current_character}: {bot_message}"
        )

    def add_message(self, message, align="left"):
        # 왼쪽과 오른쪽 정렬에 따라 BoxLayout을 달리 설정
        message_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, padding=10
        )

        if align == "left":
            label = Label(
                text=message,
                size_hint=(0.8, None),
                font_name="NanumGothic",
                halign="left",
                valign="middle",
                text_size=(self.width * 0.75, None),
            )
            message_layout.add_widget(label)
            message_layout.add_widget(Label(size_hint_x=0.2))  # 오른쪽에 빈 공간 추가
        else:
            message_layout.add_widget(Label(size_hint_x=0.2))  # 왼쪽에 빈 공간 추가
            label = Label(
                text=message,
                size_hint=(0.8, None),
                font_name="NanumGothic",
                halign="right",
                valign="middle",
                text_size=(self.width * 0.75, None),
            )
            message_layout.add_widget(label)

        label.bind(size=self.update_text_size)
        label.bind(texture_size=label.setter("size"))
        self.message_layout.add_widget(message_layout)

        self.message_layout.height += label.texture_size[1]

        self.scroll_view.scroll_to(label)

    def update_text_size(self, instance, value):
        instance.text_size = (
            self.width * 0.75,
            None,
        )  # 너비의 75%를 사용하여 텍스트 크기를 조정


class TestApp(App):
    def build(self):
        sm = ScreenManager()
        main_screen = MainScreen(name="main")
        chat_screen = ChatScreen(name="chat")
        sm.add_widget(main_screen)
        sm.add_widget(chat_screen)
        return sm


if __name__ == "__main__":
    TestApp().run()
