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
from kivy.core.window import Window
import threading
import docx
import PyPDF2
import json
import datetime
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle
import sys  # 프로그램 종료를 위해 sys 모듈 추가


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


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.current_CS_Chatbot = "nopoiA"
        grounding_data_folder = (
            "Chatbotgrounding-data\nepoiA.pdf"  # 폴더 경로를 여기에 지정하세요
        )
        self.grounding_data = load_grounding_data(grounding_data_folder)

        # UI 레이아웃 설정
        layout = FloatLayout()

        with layout.canvas.before:
            Color(1, 1, 1, 1)  # 흰색 배경 설정
            self.rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=self._update_rect, pos=self._update_rect)

        chat_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))

        top_layout = BoxLayout(orientation="horizontal", size_hint_y=0.07)
        back_button = Button(
            text="<",
            size_hint=(0.1, 1),
            font_size="20sp",
            font_name=myfont,
        )
        back_button.bind(on_press=self.go_back)  # 프로그램 종료로 변경
        self.CS_Chatbot_label = Label(
            size_hint=(0.9, 1),
            font_size="24sp",
            font_name=myfont,
            halign="center",
            valign="middle",
            color=(0, 0, 0, 1),  # 글자색을 검정색으로 설정
        )

        top_layout.add_widget(back_button)
        top_layout.add_widget(self.CS_Chatbot_label)
        chat_layout.add_widget(top_layout)

        self.scroll_view = ScrollView(size_hint=(1, 0.75))
        self.message_layout = BoxLayout(
            orientation="vertical", size_hint_y=None, padding=10, spacing=10
        )
        self.message_layout.bind(minimum_height=self.message_layout.setter("height"))
        self.scroll_view.add_widget(self.message_layout)
        chat_layout.add_widget(self.scroll_view)

        input_layout = BoxLayout(size_hint=(1, 0.1))
        self.text_input = TextInput(
            hint_text="메시지를 입력하세요...",
            multiline=True,
            font_name=myfont,
            size_hint_x=0.8,
            input_type="text",
            background_color=(1, 1, 1, 1),  # 입력창 배경을 하얀색으로 설정
            foreground_color=(0, 0, 0, 1),  # 입력 텍스트를 검정색으로 설정
            hint_text_color=(0.5, 0.5, 0.5, 1),  # 힌트 텍스트를 회색으로 설정
            write_tab=False,  # Tab 키를 눌러도 입력창에서 커서가 유지되도록 함
        )
        # 키보드 이벤트 바인딩
        Window.bind(on_key_down=self._on_key_down)

        self.send_button = Button(
            text="전송",
            size_hint=(0.2, 1),
            font_name=myfont,
        )
        self.send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(self.send_button)
        chat_layout.add_widget(input_layout)

        layout.add_widget(chat_layout)
        self.add_widget(layout)

        # 초기 환영 메시지 추가
        Clock.schedule_once(
            lambda dt: self.add_message(
                "nepoiA",
                "안녕하세요! 저는 버추얼 아이돌 그룹 nepoiA를 대표하는 CS 챗봇입니다! \n어디서 도움을 드릴 것일까요?",
                align="left",
                icon_source=f"chatbot-icon/{CS_Chatbot_name}.png",
            )
        )

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _on_key_down(self, _window, key, _scancode, _codepoint, modifiers):
        if key == 13:  # Enter key
            if "shift" in modifiers or "ctrl" in modifiers:
                # Shift 또는 Ctrl + Enter -> 줄바꿈 추가
                self.text_input.text += "\n"
            else:
                # Enter만 눌렀을 때 -> 메시지 전송
                self.send_message(None)
            return True
        return False

    def go_back(self, _instance):
        sys.exit()  # 프로그램을 종료하도록 변경

    def send_message(self, _instance):
        user_message = self.text_input.text
        if user_message:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
            self.add_message(
                "나",
                f"({timestamp})\n{user_message}",
                align="right",
            )

            self.text_input.text = ""
            self.text_input.focus = True
            self.send_button.disabled = True  # 전송 버튼 비활성화

            # GPT 호출 비동기 처리
            grounding_data = self.grounding_data.get(self.current_CS_Chatbot, "")
            threading.Thread(
                target=get_openai_response,
                args=(
                    user_message,
                    self.current_CS_Chatbot,
                    grounding_data,
                    self.receive_message,
                ),
            ).start()

    def receive_message(self, bot_message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        self.add_message(
            "nepoiA",
            f"({timestamp}): \n{bot_message}",
            align="left",
            icon_source=f"chatbot-icon/{CS_Chatbot_name}.png",
        )
        self.send_button.disabled = False  # 챗봇 응답 후 전송 버튼 활성화

    def add_message(self, sender, message, align="left", icon_source=None):
        message_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            padding=(10, 10, 10, 10),
            spacing=10,
        )

        if align == "left":
            message_layout.padding = [20, 5, 60, 5]
        else:
            message_layout.padding = [60, 5, 20, 5]

        if icon_source:
            icon = Image(source=icon_source, size_hint=(None, None), size=(90, 90))
            if align == "left":
                message_layout.add_widget(icon)

        label = Label(
            text=f"{sender}: {message}",
            markup=True,
            size_hint_y=None,
            font_name=myfont,
            halign=align,
            valign="top",
            text_size=(self.scroll_view.width * 0.7, None),  # 텍스트 너비 조정
            color=(0, 0, 0, 1),  # 글자색을 검정색으로 설정
        )
        label.bind(size=label.setter("text_size"))
        label.bind(texture_size=label.setter("size"))
        label.bind(size=self._update_message_height)

        if align == "left":
            message_layout.add_widget(label)
            message_layout.add_widget(Label(size_hint_x=0.1))
        else:
            message_layout.add_widget(Label(size_hint_x=0.1))
            message_layout.add_widget(label)

        message_layout.height = (
            label.height + 20
        )  # 레이블 높이에 맞춰 레이아웃 높이 조정
        self.message_layout.add_widget(message_layout)
        self.message_layout.height = sum(
            [child.height for child in self.message_layout.children]
        ) + 30 * len(self.message_layout.children)

        # 새 메시지가 추가될 때마다 아래로 스크롤
        Clock.schedule_once(lambda dt: self.scroll_view.scroll_to(message_layout), 0.01)

    def _update_message_height(self, instance, size):
        instance.parent.height = size[1] + 20


class ChatApp(App):
    def build(self):
        sm = ScreenManager()
        chat_screen = ChatScreen(name="chat")
        sm.add_widget(chat_screen)
        return sm


if __name__ == "__main__":
    ChatApp().run()
