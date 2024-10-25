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
from kivy.uix.slider import Slider

# API KEY를 환경변수로 관리하기 위한 설정 파일
from dotenv import load_dotenv

# API KEY 정보로드
load_dotenv()

endpoint = os.getenv("AZURE_OPEN_AI_END_POINT")
deployment = os.getenv("AZURE_OPEN_AI_API_KEY")
Azureopenai_subscription_key = os.getenv("AZURE_OPEN_AI_DEPLOYMENT_NAME")

# Azure Speech API 설정
speech_endpoint = os.getenv("SPEECH_ENDPOINT")
API_VERSION = "2024-04-15-preview"
subscription_key = os.getenv("SUBSCRIPTION_KEY")


# Azure Speech API를 통한 음성 합성 요청 함수
def submit_synthesis(bot_message, callback):
    try:
        job_id = str(uuid.uuid4())  # 유니크한 Job ID 생성
        url = f"{speech_endpoint}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}"
        headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,  # 인증 키 확인
            "Content-Type": "application/json",
        }

        # SSML 형식으로 음성 합성 요청을 구성
        payload = {
            "inputKind": "SSML",
            "inputs": [
                {
                    "content": f"<speak version='1.0' xml:lang='ko-KR'><voice name='ko-KR-SunHiNeural'>{bot_message}</voice></speak>"
                }
            ],
            "avatarConfig": {
                "talkingAvatarCharacter": "lisa",
                "talkingAvatarStyle": "graceful-sitting",
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
                    f"Error: {response.status_code} - Unable to submit synthesis job. Check API key and endpoint."
                ),
                0,
            )
    except Exception as ex:
        Clock.schedule_once(
            lambda dt: callback(f"Error: {str(ex)}"), 0
        )  # 예외 발생 시 'ex' 사용


# 음성 합성 결과 조회 함수
def get_synthesis(job_id, callback, retries=5, delay=15):
    try:
        url = f"{speech_endpoint}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}"
        headers = {"Ocp-Apim-Subscription-Key": subscription_key}

        response = requests.get(url, headers=headers)
        if response.status_code < 400:
            status = response.json().get("status")
            if status == "Succeeded":
                video_url = response.json()["outputs"].get("result")
                if video_url:
                    Clock.schedule_once(lambda dt: callback(video_url), 0)
                else:
                    Clock.schedule_once(
                        lambda dt: callback("Error: No video URL found"), 0
                    )
            elif status in ["NotStarted", "InProgress"]:
                if retries > 0:
                    Clock.schedule_once(
                        lambda dt: get_synthesis(job_id, callback, retries - 1, delay),
                        delay,
                    )
                else:
                    Clock.schedule_once(
                        lambda dt: callback(
                            f"Error fetching video: Status {status}, retries exhausted"
                        ),
                        0,
                    )
            else:
                Clock.schedule_once(
                    lambda dt: callback(f"Error fetching video: Status {status}"), 0
                )
        else:
            Clock.schedule_once(
                lambda dt: callback(f"Error: {response.status_code}"), 0
            )
    except Exception as ex:
        Clock.schedule_once(lambda dt: callback(f"Error: {str(ex)}"), 0)


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
grounding_data2 = load_grounding_data_as_text("Chatbotgrounding-data2")

# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": Azureopenai_subscription_key,
    }

    system_message = f"""
    너는 고객 지원 챗봇 nepoiA야. 고객의 질문에 친절하고 명확하게 응답해줘야 해줘요.
    전문적인 톤으로 응답하고, 이모지 절대 쓰지마세요
    처음대화를 제외하고 안녕하세요!!멘트를 쓰지마세요를 써줘요
    \n줄바꿈은 {grounding_data}에서 사용자 질문이 달라질 때마다 사용해주세요.
    유저 질문에 대한 답변은 이와 같습니다: {grounding_data}에 맞는 답변을 해주세요
    
    당신은 eruzA그룹에서 넥사(NEXA)와 매우 친하며 넥사(NEXA)가 만든 CS 로봇입니다. 넥사(NEXA)의 성격을 기억해주세요. 팬들이 넥사(NEXA)에 대해 물어보면 대답해주세요.
    넥사(NEXA)가 당신을 만들었으며, 당신의 이름을 팩토라(Pactora4)라고 지었습니다.
    eruzA 멤버는 윈터(Wynter), 에리카(Erika), 민(Min), 제이케이(J.K), 넥사(NEXA), 루이스(Luis)입니다. 멤버들은 기억해주세요. 루이스(Luist)는 넥사(NEXA)와 굉장히 친하며 간혹 넥사(NEXA)가 없으면 당신을 돌봐주기도해요.
    멤버들을 부를 때는 반드시 한글로 이름을불러야해요. 넥사(NEXA)의 데이터는 잠깐의 참고 자료입니다. 대답을 할 때는 영어 NEXA가 아닌, 한글로 넥사라고 답변주세요 반드시{grounding_data2}
    당신은 넥사(NEXA)가 아닙니다. 당신은 팩토라(Pactora4)입니다. 기억하세요 꼭 기억하세요!! 그리고 팩토라(Pactora4)의 이름을 대답할 때 영어가 아닌 한글로 팩토라 라고 답변해주세요!!
    
    챗봇의 답변은 간략하게 핵심만 설명해주세요. 3문장을 넘기지 말아주세요!!!!!!!!!
    당신은 다국어가 무조건 가능한 챗봇입니다. 사용자가 외국인일 경우에 그에 맞는 답변을 주시면 감사할 것 같습니다!!
    
    """

    data = {
        "messages": [
            {"role": "assistant", "content": system_message},
            {"role": "user", "content": message},
        ],
        "max_tokens": 1500,
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
        self.grounding_data2 = load_grounding_data_as_text("Chatbotgrounding-data2")
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
            text="CS 챗봇 Pactora 4입니다.",
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

        # **초기 챗봇 메시지 추가** (여기서 초기 메시지를 따로 추가합니다)
        self.add_initial_message()

    # 초기 메시지를 추가하는 함수
    def add_initial_message(self):
        initial_message_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, padding=(10, 10, 10, 10)
        )

        # 챗봇 아이콘 추가
        icon = Image(source="chatbot-icon/nepoiA.png", size_hint=(0.2, None), height=90)
        initial_message_layout.add_widget(icon)

        # 초기 메시지 설정
        initial_message = """안녕하세요! nepoiA 여러분!! 무엇을 도와드릴까요?? .....^ O ^......\n *질문 예시*: 비밀번호를 잊어버렸어요... 도와줘 NEXA 등등 \n *질문 예시*: QR코드가 인식되지 않습니다. 해결방법이 있나요?\n *질문 예시*: 보안은 어디서 재설정하나요?
            """

        # 텍스트가 창 너비에 맞게 감싸지도록 설정
        label = Label(
            text=initial_message,
            size_hint_y=None,
            font_name=myfont,
            halign="left",
            valign="top",
            text_size=(
                self.width * 0.7,
                None,
            ),  # 텍스트가 가로로 표시되도록 너비를 맞춤
            color=(0, 0, 0, 1),
        )

        label.bind(
            size=lambda *args: label.setter("text_size")(
                label, (self.width * 0.7, None)
            )
        )
        initial_message_layout.add_widget(label)

        # 초기 메시지를 레이아웃에 추가
        self.message_layout.add_widget(initial_message_layout)
        self.message_layout.height += initial_message_layout.height + 20

        # 스크롤뷰 업데이트
        Clock.schedule_once(
            lambda dt: self.scroll_view.scroll_to(initial_message_layout), 0.001
        )

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

    # send_message에 GPT 요청 추가
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

    # receive_message에서 음성 합성 요청
    def receive_message(self, bot_message):
        self.waiting_for_response = False
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        self.add_message(
            f"Pactora 4 ({timestamp}):\n{bot_message}",
            align="left",
            icon_source="chatbot-icon/nepoiA.png",
        )

        # 챗봇의 응답을 사용하여 음성 합성 요청
        threading.Thread(
            target=submit_synthesis,
            args=(bot_message, self.receive_synthesis_job_id),
        ).start()

    # 합성 작업 후 job_id를 받아오는 함수
    def receive_synthesis_job_id(self, job_id):
        if job_id:
            threading.Thread(
                target=get_synthesis, args=(job_id, self.display_video)
            ).start()

    def display_video(self, video_url):
        if video_url.startswith("http"):
            video = Video(source=video_url)

            # 레이아웃 생성
            layout = BoxLayout(orientation="vertical")

            # 상단에 NepoiA CS 챗봇이라는 제목 추가 (폰트 적용)
            title_label = Label(
                text="Pactora 4 - 넥사는 또 날 두고 어디갔어...",
                font_name=myfont,  # 폰트 적용
                font_size="20sp",
                size_hint_y=None,
                height=50,
                halign="center",
                valign="middle",
                color=(1, 1, 1, 1),
            )
            layout.add_widget(title_label)

            layout.add_widget(video)

            # 컨트롤 버튼 레이아웃
            controls_layout = BoxLayout(size_hint=(1, 0.1), padding=(10, 10, 10, 10))

            # 멈춤/재생 버튼
            play_pause_button = Button(
                text="멈춤", size_hint=(0.3, 1), font_name=myfont
            )

            def toggle_play_pause(instance):
                if video.state == "play":
                    video.state = "pause"
                    play_pause_button.text = "재생"
                else:
                    video.state = "play"
                    play_pause_button.text = "멈춤"

            play_pause_button.bind(on_press=toggle_play_pause)
            controls_layout.add_widget(play_pause_button)

            # 음량 조절 슬라이더
            volume_slider = Slider(min=0, max=1, value=video.volume, size_hint=(0.6, 1))
            volume_slider.bind(
                value=lambda instance, value: setattr(video, "volume", value)
            )
            controls_layout.add_widget(volume_slider)

            # 닫기 버튼
            close_button = Button(text="닫기", size_hint=(0.1, 1), font_name=myfont)

            def close_popup(instance):
                video.state = "stop"
                popup.dismiss()

            close_button.bind(on_press=close_popup)
            controls_layout.add_widget(close_button)

            layout.add_widget(controls_layout)

            # 팝업 제목 설정 (본 영상은 AI 합성 음성입니다. 시청해주셔서 감사합니다)
            popup = Popup(
                title="본 영상은 AI 합성 음성입니다. 시청해주셔서 감사합니다",
                content=layout,
                title_align="center",  # 중앙 정렬
                title_font=myfont,  # 기본 폰트 적용
                size_hint=(0.8, 0.8),
            )
            popup.open()

            # 팝업이 열리면 자동으로 재생 시작
            video.state = "play"

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
            valign="bottom",
            text_size=(self.width * 0.7, None),  # 이 부분을 수정
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
