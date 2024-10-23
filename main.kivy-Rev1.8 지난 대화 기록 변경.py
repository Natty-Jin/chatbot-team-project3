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
from kivy.uix.screenmanager import ScreenManager, FadeTransition
import subprocess

# API KEY를 환경변수로 관리하기 위한 설정 파일
from dotenv import load_dotenv

# API KEY 정보로드
load_dotenv()


endpoint = os.getenv('AZURE_OPEN_AI_END_POINT')
deployment = os.getenv('AZURE_OPEN_AI_API_KEY')
subscription_key = os.getenv('AZURE_OPEN_AI_DEPLOYMENT_NAME')


# 변환된  폰트 등록
myfont = "SUIT-Regular"

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


# 대화 기록을 파일에 저장하는 함수
def save_conversation(persona, history):
    filename = f"conversation_{persona}.json"
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=4)


# 대화 기록을 가져오는 함수에 마지막 대화 시간과 내용을 추가
def load_conversation(persona):
    filename = f"conversation_{persona}.json"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as file:
            conversation = json.load(file)
            return conversation
    return []


def save_test_conversation(persona, initial_messages):
    # 기존 대화 내용을 불러오기
    conversation = load_conversation(persona)

    # 만약 기존 대화 내용이 없으면 기본 대화를 추가
    if not conversation:
        conversation = initial_messages

    # 대화 내용을 파일에 저장
    save_conversation(persona, conversation)


# 시작 전에 대화 기록을 테스트용으로 저장 (나중에 제거 가능)
save_test_conversation(
    "Wynter",
    ["Wynter입니다! 기분은 어때요 전 항상 에너지가 넘쳐요!"],
)
save_test_conversation(
    "Erika",
    ["Erika 입니다! 행복한 하루 보내고 있나요 전 독서를 좋아해요."],
)
save_test_conversation(
    "Min",
    [
        "Min입니더! 전 음악을 듣는 걸 좋아해요.",
    ],
)
save_test_conversation(
    "J.K", ["Hey yo J.K입니다! 뭐하고 계신가yo I'm AI에 관심이 많아yo."]
)
save_test_conversation(
    "Luis",
    ["Luis입니다! 저는 별을 관찰하는 것을 좋아해요."],
)
save_test_conversation(
    "NEXA",
    [
        "NEXA입니다! 저는 리그오브레전드 대회 보는 걸 좋아해요!!",
    ],
)


# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, char_name, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": subscription_key,
    }

    # 그라운딩 데이터를 시스템 메시지로 포함
    system_message = f"""너는 {char_name}라는 페르소나야. 그리고 페르소나 정보에 맞는 언어와 말투를 사용해야해, 이모티콘은 절대 사용하지마!
                        사용자가 질문하는 것에 대해서 답변은 사람처럼 해줘야해 사용자의 질문사항의 답변을 최대한 간추려서 2문장까지만 말해줘 이모티콘은 사용하지마
                        이 페르소나의 정보는 다음과 같아 :\n\n{grounding_data}\n\n"""

    data = {
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
            {"role": "user", "content": message},
        ],
            "max_tokens": 4000,  # 응답 길이를 확장하기 위해 설정
            "temperature": 0.7,   # 응답의 창의성 조절 (필요에 따라 조정 가능)
            "top_p":0.75,
            "frequency_penalty":0,
            "presence_penalty":0,
            "stop":None,
            "stream":False,
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

        # Set the background to white as early as possible
        with self.canvas.before:
            Color(1, 1, 1, 1)  # 흰색 배경 설정
            self.rect = Rectangle(size=self.size, pos=self.pos)

        # Make sure to bind size and position as soon as possible
        self.bind(size=self._update_rect, pos=self._update_rect)

        # 나머지 레이아웃 및 위젯 초기화
        main_layout = BoxLayout(orientation="horizontal")

        self.char_select_layout = BoxLayout(orientation="vertical", size_hint=(0.3, 1))

        group_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        group_label = Label(
            text="Eruza",
            font_name=myfont,
            size_hint_x=0.3,
            font_size="20sp",
            color=(0, 0, 0, 1),  # 검은색 텍스트
        )
        group_message = Label(
            text="안녕 우린 Eruza야",
            font_name=myfont,
            size_hint_x=0.7,
            font_size="20sp",
            color=(0, 0, 0, 1),  # 검은색 텍스트
        )
        group_layout.add_widget(group_label)
        group_layout.add_widget(group_message)
        self.char_select_layout.add_widget(group_layout)

        # 각 캐릭터의 마지막 대화 내용을 불러와 표시
        self.char_list = ["Wynter", "Erika", "Min", "J.K", "Luis", "NEXA"]
        self.char_buttons = []

        # 초기 캐릭터 버튼 설정
        self.refresh_char_buttons()

        main_layout.add_widget(self.char_select_layout)
        self.add_widget(main_layout)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def switch_to_profile(self, char_name):
        profile_screen = self.manager.get_screen("profile")
        profile_screen.update_character(char_name)
        profile_screen.save_chat_history()  # 자동으로 대화 기록을 저장하도록 수정
        self.manager.current = "profile"

    def create_char_button_layout(self, char_name):
        conversation = load_conversation(char_name)
        if conversation:
            # 마지막 챗봇의 메시지 찾기
            last_bot_message = next(
                (msg for msg in reversed(conversation) if not msg.startswith("나")),
                None,
            )
            if last_bot_message:
                last_time = last_bot_message.split("):")[0]  # 시간 부분을 추출
                last_message_preview = (
                    last_bot_message[len(last_time) + 3 :][:20]
                    + "..."  # 시간 부분 제외하고 내용만 20자 제한
                    if len(last_bot_message) > len(last_time) + 3 + 20
                    else last_bot_message[len(last_time) + 3 :]
                )
                display_text = f"{last_time}\n{last_message_preview}"
            else:
                display_text = f"{char_name}\n최근 대화 없음"
        else:
            display_text = f"{char_name}\n최근 대화 없음"

        char_button_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=80
        )
        btn_icon = Image(source=f"Icon-data/{char_name}.png", size_hint_x=0.2)
        btn_text = Button(
            text=display_text,
            font_name=myfont,
            size_hint_x=0.7,
            halign="left",
        )
        btn_text.bind(
            on_press=lambda instance, char_name=char_name: self.switch_to_profile(
                char_name
            )
        )

        char_button_layout.add_widget(btn_icon)
        char_button_layout.add_widget(btn_text)

        return char_button_layout

    def go_back(self, _instance):
        # 대화 기록 저장
        profile_screen = self.manager.get_screen("profile")
        profile_screen.save_chat_history()  # 대화 기록 저장 추가

        # MainScreen의 캐릭터 목록을 최신 대화 기준으로 갱신
        main_screen = self.manager.get_screen("main")
        main_screen.refresh_char_buttons()  # 최신 대화 기준으로 캐릭터 버튼 갱신

        # MainScreen으로 돌아가기
        self.manager.current = "main"

    def refresh_char_buttons(self):
        self.char_buttons.clear()
        self.char_select_layout.clear_widgets()

        # 그룹 정보 추가
        group_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        group_label = Label(
            text="Eruza",
            font_name=myfont,
            size_hint_x=0.3,
            font_size="20sp",
            color=(0, 0, 0, 1),  # 검은색 텍스트
        )
        group_message = Label(
            text="안녕 우린 Eruza야",
            font_name=myfont,
            size_hint_x=0.7,
            font_size="20sp",
            color=(0, 0, 0, 1),  # 검은색 텍스트
        )
        group_layout.add_widget(group_label)
        group_layout.add_widget(group_message)
        self.char_select_layout.add_widget(group_layout)

        # 캐릭터를 최근 대화 시간 기준으로 정렬하고 char_list를 업데이트
        self.char_list = sorted(
            self.char_list,
            key=lambda char_name: self.get_last_chat_time(char_name),
            reverse=True,
        )

        for char_name in self.char_list:
            char_button_layout = self.create_char_button_layout(char_name)
            self.char_select_layout.add_widget(char_button_layout)
            self.char_buttons.append(char_button_layout)

    def get_last_chat_time(self, char_name):
        conversation = load_conversation(char_name)
        if conversation:
            # 마지막 메시지가 사용자 또는 챗봇인지 관계없이 가장 최근 시간을 찾음
            last_message = conversation[-1]
            last_time_str = last_message.split("):")[0].split("(")[-1].strip()
            try:
                return datetime.datetime.strptime(last_time_str, "%Y-%m-%d - %H:%M:%S")
            except ValueError:
                return datetime.datetime.min
        return datetime.datetime.min


# 프로필 화면 (ProfileScreen)
class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super(ProfileScreen, self).__init__(**kwargs)
        self.current_character = None

        # Set the background to white
        with self.canvas.before:
            Color(1, 1, 1, 1)  # 흰색 배경 설정
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        layout = BoxLayout(orientation="vertical")

        # 상단 뒤로가기 버튼 추가
        back_layout = BoxLayout(orientation="horizontal", size_hint_y=0.07)
        back_button = Button(
            text="<",
            size_hint=(0.1, 1),
            font_size="20sp",
            font_name=myfont,
        )
        back_button.bind(on_press=self.go_back)
        self.character_label = Label(
            text="",
            size_hint=(0.9, 1),
            font_size="24sp",
            font_name=myfont,
            halign="center",
            valign="middle",
            color=(0, 0, 0, 1),  # 글자색을 검정색으로 설정
        )

        back_layout.add_widget(back_button)
        back_layout.add_widget(self.character_label)
        layout.add_widget(back_layout)

        # 캐릭터 프로필 이미지와 이름
        self.profile_image_layout = BoxLayout(
            orientation="vertical", size_hint=(1, 0.7)
        )
        self.profile_image = Image(size_hint=(1, 0.8))
        self.profile_name = Label(
            font_name=myfont,
            font_size="24sp",
            size_hint=(1, 0.2),
            halign="center",
            color=(0, 0, 0, 1),  # 글자색을 검정색으로 설정
        )
        self.profile_image_layout.add_widget(self.profile_image)
        self.profile_image_layout.add_widget(self.profile_name)
        layout.add_widget(self.profile_image_layout)

        # 대화하기 버튼
        self.chat_button = Button(
            text="대화하기",
            size_hint=(0.5, 0.1),
            font_name=myfont,
            font_size="20sp",
        )
        self.chat_button.pos_hint = {"center_x": 0.5}
        self.chat_button.bind(on_press=self.start_chat)
        layout.add_widget(self.chat_button)

        self.add_widget(layout)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def update_character(self, char_name):
        self.current_character = char_name
        self.profile_image.source = (
            f"Icon-data/{char_name}.png"  # 실제 이미지 파일 경로로 대체 필요
        )
        self.profile_name.text = f"{char_name}"

    def save_chat_history(self):
        chat_screen = self.manager.get_screen("chat")
        if self.current_character in chat_screen.chat_history:
            save_conversation(
                self.current_character, chat_screen.chat_history[self.current_character]
            )

    def start_chat(self, _instance):
        chat_screen = self.manager.get_screen("chat")
        chat_screen.update_character(self.current_character)
        chat_screen.text_input.focus = True  # 입력창에 자동 포커스 설정

        # 일정 시간 후 스크롤 뷰 업데이트 - 첫 화면 대화하기 누를 시, 이전 대화기록 바로 업데이트 시키는 방법 선택함....
        Clock.schedule_once(
            lambda dt: chat_screen.update_character(self.current_character), 0.1
        )
        self.manager.current = "chat"

    def go_back(self, _instance):
        self.save_chat_history()  # 뒤로가기 전에 대화 기록을 저장하도록 수정
        self.manager.current = "main"


# from alarm_with_message import main as start_alarm_service  #알람 기능 추가


# 대화 화면 (ChatScreen)
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.chat_history = {}
        self.current_character = None
        self.grounding_data = load_grounding_data("grounding-data")

        # FloatLayout으로 변경하여 배경을 설정할 수 있도록 함
        layout = FloatLayout()

        with layout.canvas.before:
            Color(1, 1, 1, 1)  # 흰색 배경 설정
            self.rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=self._update_rect, pos=self._update_rect)

        chat_layout = BoxLayout(orientation="vertical")

        top_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        back_button = Button(
            text="<",
            size_hint=(0.1, 1),
            font_size="20sp",
            font_name=myfont,
        )
        back_button.bind(on_press=self.go_back)
        self.character_label = Label(
            size_hint=(0.9, 1),
            font_size="24sp",
            font_name=myfont,
            halign="center",
            valign="middle",
            color=(0, 0, 0, 1),  # 글자색을 검정색으로 설정
        )

        top_layout.add_widget(back_button)
        top_layout.add_widget(self.character_label)
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
        Window.bind(on_key_down=self._on_key_down)

        # 항상 입력창에 포커스 유지
        send_button = Button(
            text="전송",
            size_hint=(0.2, 1),
            font_name=myfont,
        )
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)
        chat_layout.add_widget(input_layout)

        layout.add_widget(chat_layout)
        self.add_widget(layout)

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
                if (
                    not hasattr(self, "waiting_for_response")
                    or not self.waiting_for_response
                ):
                    self.send_message(None)
            return True
        return False

    def update_character(self, char_name):
        self.character_label.text = char_name
        self.current_character = char_name

        # 대화 기록 불러오기
        self.message_layout.clear_widgets()
        conversation = load_conversation(char_name)
        self.chat_history[char_name] = conversation

        for message in conversation:
            # 메시지의 발신자를 식별하여 정렬 위치를 지정
            if message.startswith("나"):
                self.add_message(
                    message,
                    align="right",
                    icon_source=f"Icon-data/{char_name}.png",
                )
            else:
                self.add_message(
                    message,
                    align="left",
                    icon_source=f"Icon-data/{char_name}.png",
                )

        # 지난 대화 기록 구분선을 추가
        self.add_separator("지난 대화 기록")

        # 최신 대화 목록 정렬을 위해 MainScreen의 캐릭터 버튼 갱신
        main_screen = self.manager.get_screen("main")
        main_screen.refresh_char_buttons()

    # 여기 변수는 지나 대화 기록이라는 글씨의 구분선임 건드리지마
    def add_separator(self, text):
        separator_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=80
        )
        separator_label = Label(
            text=text,
            size_hint=(1, None),
            font_name=myfont,
            font_size="18sp",
            halign="center",
            valign="middle",
            color=(0, 0, 0, 0.9),  # 검은색으로 표시
            text_size=(self.width * 0.9, None),  # 텍스트가 중앙 정렬되도록 너비를 지정
        )
        separator_layout.add_widget(separator_label)

        self.message_layout.add_widget(separator_layout)
        self.message_layout.height += 40  # 고정된 높이만큼 레이아웃 높이를 증가

    def go_back(self, _instance):
        # 대화 기록 저장
        profile_screen = self.manager.get_screen("profile")
        profile_screen.save_chat_history()  # 대화 기록 저장 추가

        # MainScreen의 캐릭터 목록을 최신 대화 기준으로 갱신
        main_screen = self.manager.get_screen("main")
        main_screen.refresh_char_buttons()  # 최신 대화 기준으로 캐릭터 버튼 갱신

        # MainScreen으로 돌아가기
        self.manager.current = "main"

    def send_message(self, _instance):
        if (
            hasattr(self, "waiting_for_response") and self.waiting_for_response
        ):  # 챗봇 응답 기다리게 하기 추가함
            return
        self.waiting_for_response = True
        user_message = self.text_input.text
        if user_message:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
            self.add_message(
                f"나 ({timestamp}): \n {user_message}",
                align="right",
                icon_source=f"Icon-data/{self.current_character}.png",
                # font_name=myfont,
            )

            # 대화 기록에 추가
            if self.current_character not in self.chat_history:
                self.chat_history[self.current_character] = []
            self.chat_history[self.current_character].append(
                f"나 ({timestamp}): \n {user_message}"
            )

            # 대화 기록 저장
            save_conversation(
                self.current_character, self.chat_history[self.current_character]
            )

            self.text_input.text = ""
            self.text_input.focus = True

            # GPT 호출 비동기 처리
            grounding_data = self.grounding_data.get(self.current_character, "")
            threading.Thread(
                target=get_openai_response,
                args=(
                    user_message,
                    self.current_character,
                    grounding_data,
                    self.receive_message,
                ),
            ).start()

            # 캐릭터 버튼 새로고침
            main_screen = self.manager.get_screen("main")
            main_screen.refresh_char_buttons()

    def receive_message(self, bot_message):
        self.waiting_for_response = (
            False  # 챗봇이 응답할 때까지 사용자 질문 못하게 막았음
        )
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        self.add_message(
            f"{self.current_character} ({timestamp}): \n {bot_message}",
            align="left",
            icon_source=f"Icon-data/{self.current_character}.png",
            # font_name=myfont,
        )
        self.chat_history[self.current_character].append(
            f"{self.current_character} ({timestamp}): \n {bot_message}"
        )

        # 대화 기록 저장
        save_conversation(
            self.current_character, self.chat_history[self.current_character]
        )


    def add_message(self, message, align="left", icon_source=None):
        message_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, padding=[10, 5], spacing=10
        )

        if icon_source:
            # 매번 새로운 Image 객체 생성
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
            color=(0, 0, 0, 1),  # 글자색을 검정색으로 설정
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

        # 메시지가 추가될 때마다 스크롤을 최하단으로 이동 0.001로 한 사유는 지난 대화 기록이라는 글자가 잘 안 보임
        Clock.schedule_once(lambda dt: self.scroll_view.scroll_to(message_layout), 0.05)

    def _update_message_height(self, instance, size):
        instance.parent.height = size[1] + 20


class TestApp(App):
    def build(self):
        sm = ScreenManager(
            transition=FadeTransition(duration=0.3)
        )  # 페이드 전환 애니메이션 적용 스크린 전환 애니메이션 적용 - 자연스러움 추가
        main_screen = MainScreen(name="main")
        profile_screen = ProfileScreen(name="profile")
        chat_screen = ChatScreen(name="chat")
        sm.add_widget(main_screen)
        sm.add_widget(profile_screen)
        sm.add_widget(chat_screen)
        return sm


if __name__ == "__main__":
    TestApp().run()
