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


# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, char_name, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": subscription_key,
    }

    # 그라운딩 데이터를 시스템 메시지로 포함
    system_message = f"""너는 {char_name}라는 페르소나야. 그리고 페르소나 정보에 맞는 언어와 말투를 사용해야해, 이모티콘은 절대 쓰지 않아
                        이 페르소나의 정보는 다음과 같아 :\n\n{grounding_data}\n\n"""

    data = {
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
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

        # 각 캐릭터의 마지막 대화 내용을 불러와 표시
        self.char_buttons = []
        char_list = ["Wynter", "Erika", "Min", "J.K", "Luis", "NEXA"]
        for char_name in char_list:
            conversation = load_conversation(char_name)
            if conversation:
                last_message = conversation[-1]
                last_time = last_message.split("): ")[0]  # 시간 부분을 추출
                last_message_preview = (
                    last_message[len(last_time) + 3:][:30] + "..."  # 시간 부분 제외하고 내용만 30자 제한
                    if len(last_message) > len(last_time) + 3 + 20
                    else last_message[len(last_time) + 3:]
                )
                display_text = f"{last_time}\n{last_message_preview}"
            else:
                display_text = f"{char_name}\n최근 대화 없음"

            # 버튼에 내용을 설정
            char_button_layout = BoxLayout(
                orientation="horizontal", size_hint_y=None, height=80
            )
            btn_icon = Image(
                source=f"Icon-data/{char_name}.png", size_hint_x=0.3
            )
            btn_text = Button(
                text=display_text,
                font_name="NanumGothic",
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
            char_select_layout.add_widget(char_button_layout)
            self.char_buttons.append((char_name, btn_icon, btn_text))

        main_layout.add_widget(char_select_layout)
        self.add_widget(main_layout)

    def switch_to_profile(self, char_name):
        profile_screen = self.manager.get_screen("profile")
        profile_screen.update_character(char_name)
        profile_screen.save_chat_history()  # 자동으로 대화 기록을 저장하도록 수정
        self.manager.current = "profile"


# 프로필 화면 (ProfileScreen)
class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super(ProfileScreen, self).__init__(**kwargs)
        self.current_character = None

        layout = BoxLayout(orientation="vertical")

        # 상단 뒤로가기 버튼 추가
        back_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        back_button = Button(
            text="<", size_hint=(0.1, 1), font_size="20sp", font_name="NanumGothic"
        )
        back_button.bind(on_press=self.go_back)
        self.character_label = Label(
            text="",  # 상단 캐릭터 프로필 제목 제거
            size_hint=(0.9, 1),
            font_size="24sp",
            font_name="NanumGothic",
            halign="center",
            valign="middle",
        )

        back_layout.add_widget(back_button)
        back_layout.add_widget(self.character_label)
        layout.add_widget(back_layout)

        # 캐릭터 프로필 이미지와 이름
        self.profile_image_layout = BoxLayout(orientation="vertical", size_hint=(1, 0.7))
        self.profile_image = Image(size_hint=(1, 0.8))
        self.profile_name = Label(font_name="NanumGothic", font_size="24sp", size_hint=(1, 0.2), halign="center")
        self.profile_image_layout.add_widget(self.profile_image)
        self.profile_image_layout.add_widget(self.profile_name)
        layout.add_widget(self.profile_image_layout)

        # 대화하기 버튼
        self.chat_button = Button(
            text="대화하기", size_hint=(0.5, 0.1), font_name="NanumGothic", font_size="20sp"
        )
        self.chat_button.pos_hint = {"center_x": 0.5}
        self.chat_button.bind(on_press=self.start_chat)
        layout.add_widget(self.chat_button)

        self.add_widget(layout)

    def update_character(self, char_name):
        self.current_character = char_name
        self.profile_image.source = f"Icon-data/{char_name}.png"  # 실제 이미지 파일 경로로 대체 필요
        self.profile_name.text = f"{char_name}"

    def save_chat_history(self):
        chat_screen = self.manager.get_screen("chat")
        if self.current_character in chat_screen.chat_history:
            save_conversation(self.current_character, chat_screen.chat_history[self.current_character])

    def start_chat(self, instance):
        chat_screen = self.manager.get_screen("chat")
        chat_screen.update_character(self.current_character)
        self.manager.current = "chat"

    def go_back(self, instance):
        self.save_chat_history()  # 뒤로가기 전에 대화 기록을 저장하도록 수정
        self.manager.current = "main"


# 대화 화면 (ChatScreen)
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.chat_history = {}
        self.current_character = None
        self.grounding_data = load_grounding_data("grounding-data")

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
            hint_text="메시지를 입력하세요...", multiline=True, font_name="NanumGothic", size_hint_x=0.8, input_type="text"
        )
        self.text_input.input_filter = lambda text, from_undo: text if text.isalnum() or text.isspace() else None  # 한국어 키보드 기본 적용
        Window.bind(on_key_down=self._on_key_down)
        send_button = Button(text="전송", size_hint=(0.2, 1), font_name="NanumGothic")
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)
        chat_layout.add_widget(input_layout)

        self.add_widget(chat_layout)

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if key == 13:  # Enter key
            if 'shift' in modifiers:
                self.text_input.text += "\n"
            else:
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
            # 메시지 길이가 40자를 초과할 경우 줄바꿈 추가
            formatted_message = "\n".join([message[i:i + 50] for i in range(0, len(message), 50)])
            # 메시지의 발신자를 식별하여 정렬 위치를 지정
            if message.startswith("나"):
                self.add_message(formatted_message.replace("\\n", "\n"), align="right", icon_source=f"Icon-data/{char_name}.png")
            else:
                self.add_message(formatted_message.replace("\\n", "\n"), align="left", icon_source=f"Icon-data/{char_name}.png")

        # 지난 대화 기록 구분선을 추가
        self.add_separator("지난 대화 기록")


    def add_separator(self, text):
        separator_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=80
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

        self.message_layout.add_widget(separator_layout)
        self.message_layout.height += 40  # 고정된 높이만큼 레이아웃 높이를 증가

    def go_back(self, _instance):
        profile_screen = self.manager.get_screen("profile")
        profile_screen.save_chat_history()  # 대화 기록 저장 추가
        self.manager.current = "profile"

    def send_message(self, _instance):
        user_message = self.text_input.text
        if user_message:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
            self.add_message(f"나 ({timestamp}): \n {user_message}", align="right", icon_source=f"Icon-data/{self.current_character}.png")

            # 대화 기록에 추가
            if self.current_character not in self.chat_history:
                self.chat_history[self.current_character] = []
            self.chat_history[self.current_character].append(f"나 ({timestamp}): \n {user_message}")

            # 대화 기록 저장
            save_conversation(self.current_character, self.chat_history[self.current_character])

            self.text_input.text = ""
            self.text_input.focus = True

            # GPT 호출 비동기 처리
            grounding_data = self.grounding_data.get(self.current_character, "")
            threading.Thread(
                target=get_openai_response,
                args=(user_message, self.current_character, grounding_data, self.receive_message),
            ).start()

    def receive_message(self, bot_message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
        self.add_message(f"{self.current_character} ({timestamp}): \n {bot_message}", align="left", icon_source=f"Icon-data/{self.current_character}.png")
        self.chat_history[self.current_character].append(f"{self.current_character} ({timestamp}): \n {bot_message}")

        # 대화 기록 저장
        save_conversation(self.current_character, self.chat_history[self.current_character])

    def add_message(self, message, align="left", icon_source=None):
        message_layout = BoxLayout(
            orientation="horizontal", size_hint_y=None, padding=(10, 10, 10, 10)
        )

        icon = None
        if icon_source:
            icon = Image(source=icon_source, size_hint=(0.1, None), height=40)
            message_layout.add_widget(icon) if align == "left" else None

        label = Label(
            text=message,
            size_hint_y=None,
            font_name="NanumGothic",
            halign=align,
            valign="middle",
            text_size=(self.width * 0.7, None),
        )

        label.bind(texture_size=label.setter("size"))
        label.bind(size=self._update_message_height)

        if align == "left":
            if icon:
                message_layout.add_widget(icon)
            message_layout.add_widget(label)
            message_layout.add_widget(Label(size_hint_x=0.2))
        else:
            message_layout.add_widget(Label(size_hint_x=0.2))
            message_layout.add_widget(label)

        self.message_layout.add_widget(message_layout)
        self.message_layout.height += message_layout.height + 20

        # 메시지가 추가될 때마다 스크롤을 최하단으로 이동
        Clock.schedule_once(lambda dt: self.scroll_view.scroll_to(message_layout), 0.1)

    def _update_message_height(self, instance, size):
        instance.parent.height = size[1] + 20


def save_test_conversation(persona, initial_messages):
    # 기존 대화 내용을 불러오기
    conversation = load_conversation(persona)

    # 만약 기존 대화 내용이 없으면 기본 대화를 추가
    if not conversation:
        conversation = initial_messages

    # 대화 내용을 파일에 저장
    save_conversation(persona, conversation)


# 시작 전에 대화 기록을 테스트용으로 저장 (나중에 제거 가능)
save_test_conversation("Wynter", ["안녕하세요 ~ Wynter입니다! 오늘 기분은 어때요?", "전 항상 에너지가 넘쳐요!"])
save_test_conversation("Erika", ["안녕하세요 ~ Erika 입니다! 오늘도 행복한 하루 보내고 있나요?", "전 독서를 좋아해요."])
save_test_conversation("Min", ["안녕하세요 Min입니더! 오늘은 어떤 모험이 기다리고 있을까예?", "전 음악을 듣는 걸 좋아해요."])
save_test_conversation("J.K", ["Hey yo J.K입니다! 오늘은 뭐하고 계신가yo?", "I'm AI에 관심이 많아yo."])
save_test_conversation("Luis", ["안녕하세요! 오늘도 밝은 하루가 되길 바라요.", "별을 관찰하는 것을 좋아해요."])
save_test_conversation("NEXA", ["안녕하세요! 오늘도 멋진 하루 보내세요!", "저는 리그오브레전드 대회 보는 걸 좋아해요!!"])


class TestApp(App):
    def build(self):
        sm = ScreenManager()
        main_screen = MainScreen(name="main")
        profile_screen = ProfileScreen(name="profile")
        chat_screen = ChatScreen(name="chat")
        sm.add_widget(main_screen)
        sm.add_widget(profile_screen)
        sm.add_widget(chat_screen)
        return sm


if __name__ == "__main__":
    TestApp().run()
