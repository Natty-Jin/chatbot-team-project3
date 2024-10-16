from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, Screen

# NanumGothic 폰트 등록
LabelBase.register(name='NanumGothic', fn_regular='NanumGothic.ttf')

# 메인 화면에서 캐릭터를 선택하는 화면 (MainScreen)
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        main_layout = BoxLayout(orientation="horizontal")

        # 좌측에 캐릭터 선택 영역 추가
        char_select_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1))

        # 그룹 이름과 메시지 추가 (Eruza)
        group_layout = BoxLayout(orientation="horizontal", size_hint_y=0.1)
        group_label = Label(text="Eruza", font_name='NanumGothic', size_hint_x=0.3, font_size="20sp")
        group_message = Label(text="안녕 우린 Eruza야", font_name='NanumGothic', size_hint_x=0.7, font_size="20sp")
        group_layout.add_widget(group_label)
        group_layout.add_widget(group_message)
        char_select_layout.add_widget(group_layout)

        # 캐릭터 버튼 추가
        char_buttons = [
            ("Wynter", "최근 대화내용"),
            ("Erika", "최근 대화내용"),
            ("Min", "최근 대화내용"),
            ("J.K", "최근 대화내용"),
            ("Luis", "최근 대화내용"),
            ("NEXA", "최근 대화내용"),
        ]

        for char_name, greeting in char_buttons:
            char_button_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=80)
            btn_icon = Button(text=f"{char_name}\nicon", size_hint_x=0.3, font_name='NanumGothic')

            # 각 버튼에 해당 캐릭터 이름을 대화 화면으로 넘기는 기능 추가
            btn_icon.bind(on_press=lambda instance, char_name=char_name: self.switch_to_chat(char_name))

            btn_text = Label(text=f"{char_name}\n{greeting}", font_name='NanumGothic', size_hint_x=0.7, halign='left')
            char_button_layout.add_widget(btn_icon)
            char_button_layout.add_widget(btn_text)
            char_select_layout.add_widget(char_button_layout)

        # 메인 레이아웃에 추가
        main_layout.add_widget(char_select_layout)
        self.add_widget(main_layout)

    def switch_to_chat(self, char_name):
        # ScreenManager를 통해 ChatScreen으로 이동하며, 선택된 캐릭터 이름을 전달
        chat_screen = self.manager.get_screen('chat')
        chat_screen.update_character(char_name)
        self.manager.current = 'chat'


# 대화 화면 (ChatScreen)
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)

        # 우측 대화 화면
        chat_layout = BoxLayout(orientation='vertical')

        # 최상단에 뒤로 가기 버튼과 캐릭터 이름 표시
        top_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        back_button = Button(text="<", size_hint=(0.1, 1), font_size="20sp", font_name='NanumGothic')
        back_button.bind(on_press=self.go_back)
        self.character_label = Label(text="캐릭터를 선택하세요", size_hint=(0.9, 1), font_size="24sp", font_name='NanumGothic')

        top_layout.add_widget(back_button)
        top_layout.add_widget(self.character_label)
        chat_layout.add_widget(top_layout)

        # 메시지 스크롤 뷰
        scroll_view = ScrollView(size_hint=(1, 0.8))
        self.message_layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=10, spacing=10)
        self.message_layout.bind(minimum_height=self.message_layout.setter('height'))
        scroll_view.add_widget(self.message_layout)
        chat_layout.add_widget(scroll_view)

        # 텍스트 입력 및 전송 버튼
        input_layout = BoxLayout(size_hint=(1, 0.1))
        self.text_input = TextInput(hint_text="메시지를 입력하세요...", multiline=False, font_name='NanumGothic')
        send_button = Button(text="전송", size_hint=(0.2, 1), font_name='NanumGothic')
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)
        chat_layout.add_widget(input_layout)

        self.add_widget(chat_layout)

    def update_character(self, char_name):
        # 선택된 캐릭터의 이름을 상단에 표시
        self.character_label.text = char_name

    def go_back(self, instance):
        # 뒤로 가기 버튼을 클릭하면 MainScreen으로 돌아감
        self.manager.current = 'main'

    def send_message(self, instance):
        # 유저가 입력한 메시지 전송
        message = self.text_input.text
        if message:
            self.add_message(f"나: {message}")
            self.text_input.text = ""

    def add_message(self, message):
        # 대화 창에 메시지 추가
        label = Label(text=message, size_hint_y=None, height=40, font_name='NanumGothic', halign='left', valign='middle')
        label.bind(texture_size=label.setter('size'))
        self.message_layout.add_widget(label)


class TestApp(App):
    def build(self):
        sm = ScreenManager()

        # MainScreen과 ChatScreen을 추가
        main_screen = MainScreen(name='main')
        chat_screen = ChatScreen(name='chat')

        sm.add_widget(main_screen)
        sm.add_widget(chat_screen)

        return sm

# 앱 실행
if __name__ == "__main__":
    TestApp().run()
