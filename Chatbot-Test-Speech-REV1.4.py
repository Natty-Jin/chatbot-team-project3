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
import datetime
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle
from kivy.uix.popup import Popup
from kivy.uix.video import Video
import threading
import PyPDF2
import sys
import uuid
import docx

# API KEY를 환경변수로 관리하기 위한 설정 파일
from dotenv import load_dotenv

# API KEY 정보로드
load_dotenv()

endpoint = os.getenv('AZURE_OPEN_AI_END_POINT')
deployment = os.getenv('AZURE_OPEN_AI_API_KEY')
subscription_key = os.getenv('AZURE_OPEN_AI_DEPLOYMENT_NAME')

# Azure Speech API 설정
SPEECH_ENDPOINT = os.getenv(
    "SPEECH_ENDPOINT", "https://westus2.api.cognitive.microsoft.com"
)
API_VERSION = "2024-04-15-preview"
SUBSCRIPTION_KEY = os.getenv("SUBSCRIPTION_KEY", "1ff2d7a7379b4e349aa1734718de89fc")


# Azure Speech API를 통한 음성 합성 요청 함수
def submit_synthesis(user_message, callback):
    try:
        job_id = str(uuid.uuid4())
        url = f"{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}"
        headers = {
            "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "synthesisConfig": {
                "voice": "en-US-JennyMultilingualNeural",
            },
            "inputKind": "plainText",
            "inputs": [
                {
                    "content": user_message,
                },
            ],
            "avatarConfig": {
                "customized": False,
                "talkingAvatarCharacter": "Lisa",
                "videoFormat": "mp4",
                "videoCodec": "h264",
                "subtitleType": "soft_embedded",
                "backgroundColor": "#FFFFFFFF",
            },
        }

        response = requests.put(url, json=payload, headers=headers)

        if response.status_code < 400:
            Clock.schedule_once(lambda dt: callback(job_id), 0)
        else:
            Clock.schedule_once(
                lambda dt: callback(
                    f"Error: {response.status_code} - Unable to submit synthesis job."
                ),
                0,
            )
    except Exception as ex:  # 예외가 발생한 경우에만 'ex' 변수를 사용합니다
        Clock.schedule_once(
            lambda dt: callback(f"Error: {str(ex)}"), 0
        )  # 예외 발생 시 'ex' 사용


# 음성 합성 결과 조회 함수
def get_synthesis(job_id, callback):
    try:
        url = f"{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}"
        headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY}

        response = requests.get(url, headers=headers)
        if response.status_code < 400:
            status = response.json().get("status")
            if status == "Succeeded":
                video_url = response.json()["outputs"].get("result")  # 동영상 URL 추출
                if video_url:
                    Clock.schedule_once(lambda dt: callback(video_url), 0)
                else:
                    Clock.schedule_once(
                        lambda dt: callback("Error: No video URL found"), 0
                    )
            else:
                Clock.schedule_once(lambda dt: callback(f"Status: {status}"), 0)
        else:
            Clock.schedule_once(
                lambda dt: callback(f"Error: {response.status_code}"), 0
            )
    except Exception as ex:  # 'ex'로 예외 변수 지정
        Clock.schedule_once(lambda dt: callback(f"Error: {str(ex)}"), 0)  # 'ex' 사용


# ******************************* 여기부터는 CS 챗봇 관련 *************************************

# 변환된 폰트 등록
myfont = "SUIT-Regular"
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


# Grounding 데이터를 텍스트로 읽어오는 함수 정의
def load_grounding_data_as_text(folder_path):
    grounding_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith((".txt", ".pdf", ".docx")):
                grounding_files.append(os.path.join(root, file))

    grounding_data_text = ""
    for file_path in grounding_files:
        try:
            file_content = read_file(file_path)  # 파일을 읽어서 텍스트로 변환
            grounding_data_text += f"\n{file_content}\n"
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")

    return grounding_data_text  # 텍스트 형식의 데이터를 반환


# 그라운딩 데이터 로드
grounding_data = load_grounding_data_as_text("Chatbotgrounding-data")


# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": subscription_key,
    }

    system_message = f"""
    너는 고객 지원 챗봇 nepoiA야. 고객의 질문에 친절하고 명확하게 응답해줘야 해.
    전문적인 톤으로 응답하고, 사용자의 질문에 대해 최대 3문장으로 답변해줘. 이모지 절대 쓰지마
    처음대화를 제외하고 안녕하세요!!멘트를 쓰지마세요, 답변 끝에는 감사합니다!!를 써줘
    \n줄바꿈은 {grounding_data}에서 사용자 질문이 달라질 때마다 사용해주세요.
    유저 질문에 대한 답변은 이와 같습니다: {grounding_data}에 맞는 답변을 해주세요
    """

    data = {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message},
        ],
        "max_tokens": 4000,
        "temperature": 0.7,
        "top_p": 0.75,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": None,
        "stream": False,
    }

    url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version=2024-05-01-preview"
    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            Clock.schedule_once(lambda dt: callback(content), 0)
        else:
            error_message = f"Error: {response.status_code} - Unable to fetch response from Azure OpenAI."
            try:
                error_message += f" Response: {response.json()}"
            except Exception as json_error:
                error_message += (
                    f" (Response body could not be parsed: {str(json_error)})"
                )
            Clock.schedule_once(lambda dt: callback(error_message), 0)

    except requests.exceptions.RequestException as e:
        print(f"RequestException occurred: {str(e)}")
        Clock.schedule_once(lambda dt: callback(f"Request error: {str(e)}"), 0)

    except Exception as e:
        print(f"General exception occurred: {str(e)}")
        Clock.schedule_once(lambda dt: callback(f"Unexpected error: {str(e)}"), 0)


# CS 챗봇 화면 (CSChatScreen)
class CSChatScreen(Screen):
    def __init__(self, **kwargs):
        super(CSChatScreen, self).__init__(**kwargs)
        # Grounding 데이터를 불러옴
        self.grounding_data = load_grounding_data_as_text("Chatbotgrounding-data")

        # UI 설정
        layout = FloatLayout()

        with layout.canvas.before:
            Color(1, 1, 1, 1)  # 흰색 배경 설정
            self.rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(
            size=self._update_rect, pos=self._update_rect
        )  # 크기나 위치 변경 시 호출

        chat_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))

        top_layout = BoxLayout(orientation="horizontal", size_hint_y=0.07)
        back_button = Button(
            text="<", size_hint=(0.1, 1), font_size="20sp", font_name=myfont
        )
        back_button.bind(
            on_press=self.go_back
        )  # 뒤로 가기 버튼 동작을 위한 메서드 연결
        self.character_label = Label(
            text="고객 지원 챗봇 nepoiA",
            size_hint=(0.9, 1),
            font_size="24sp",
            font_name=myfont,
            halign="center",
            valign="middle",
            color=(0, 0, 0, 1),
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
            hint_text="메시지를 입력하세요...",
            multiline=True,
            font_name=myfont,
            size_hint_x=0.8,
            input_type="text",
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            hint_text_color=(0.5, 0.5, 0.5, 1),
            write_tab=False,
        )

        Window.bind(on_key_down=self._on_key_down)  # 키보드 입력을 바인딩합니다.

        send_button = Button(text="전송", size_hint=(0.2, 1), font_name=myfont)
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)
        chat_layout.add_widget(input_layout)

        layout.add_widget(chat_layout)
        self.add_widget(layout)

    # _update_rect 메서드 추가
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    # _on_key_down 메서드 추가 (엔터 및 Shift+Enter 처리)
    def _on_key_down(self, _window, key, _scancode, _codepoint, modifiers):
        if key == 13:  # Enter key
            if "shift" in modifiers or "ctrl" in modifiers:  # Shift + Enter -> 줄바꿈
                self.text_input.text += "\n"
            else:
                # 엔터키가 눌렸을 때 메시지를 전송
                if (
                    not hasattr(self, "waiting_for_response")
                    or not self.waiting_for_response
                ):
                    self.send_message(None)
            return True
        return False

    def go_back(self, _instance):
        sys.exit()  # 프로그램을 종료

    def send_message(self, _instance):
        if hasattr(self, "waiting_for_response") and self.waiting_for_response:
            return
        self.waiting_for_response = True
        user_message = self.text_input.text.strip()
        if user_message:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
            self.add_message(f"나 ({timestamp}):\n{user_message}", align="right")
            self.text_input.text = ""
            self.text_input.focus = True

            # GPT 호출 비동기 처리, Grounding 데이터 포함
            threading.Thread(
                target=get_openai_response,
                args=(user_message, self.grounding_data, self.receive_message),
            ).start()

    # *************** Speech *********************
    def receive_message(self, bot_message, job_id=None):
        self.waiting_for_response = False
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        if job_id:
            # 음성 합성 결과를 얻어온 후 웹뷰로 동영상 출력
            get_synthesis(job_id, self.display_video)
        else:
            # job_id가 없을 때는 텍스트 메시지 처리
            self.add_message(
                f"nepoiA ({timestamp}):\n{bot_message}",
                align="left",
                icon_source="chatbot-icon/nepoiA.png",
            )

    def display_video(self, video_url):
        # Kivy의 Video 위젯을 사용하여 동영상을 표시하는 팝업
        if video_url.startswith("http"):
            video = Video(source=video_url)
            popup = Popup(
                title="Synthesized Video", content=video, size_hint=(0.8, 0.8)
            )
            video.state = "play"  # 비디오 재생
            popup.open()
        else:
            self.add_message(f"Error fetching video: {video_url}", align="left")

    # 메시지 추가 함수 수정
    def add_message(self, message, align="left", icon_source=None):
        message_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, padding=(10, 10, 1, 10)
        )

        if icon_source:
            icon = Image(source=icon_source, size_hint=(0.2, None), height=90)
            if align == "left":
                message_layout.add_widget(icon)

        label = Label(
            text=message,
            size_hint_y=None,
            font_name=myfont,
            halign=align,
            valign="middle",
            text_size=(self.width * 0.7, None),
            color=(0, 0, 0, 1),
        )

        label.bind(texture_size=label.setter("size"))
        label.bind(size=self._update_message_height)

        if align == "left":
            message_layout.add_widget(label)
            message_layout.add_widget(Label(size_hint_x=0.2))
        else:
            message_layout.add_widget(Label(size_hint_x=0.2))
            message_layout.add_widget(label)

        self.message_layout.add_widget(message_layout)
        self.message_layout.height += message_layout.height + 20

        Clock.schedule_once(
            lambda dt: self.scroll_view.scroll_to(message_layout), 0.001
        )

    def _update_message_height(self, instance, size):
        instance.parent.height = size[1] + 20


# ChatApp 실행
class ChatApp(App):
    def build(self):
        sm = ScreenManager()
        chat_screen = CSChatScreen(name="chat")
        sm.add_widget(chat_screen)
        return sm


if __name__ == "__main__":
    ChatApp().run()
