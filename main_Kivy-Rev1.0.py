from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout


class TestApp(App):
    def build(self):
        # 메인 레이아웃은 세로(Box) 레이아웃
        main_layout = BoxLayout(orientation="vertical")

        # 상단에 라벨 추가
        eruza_label = Label(text="hello world", size_hint=(1, 0.3), font_size="30sp")
        main_layout.add_widget(eruza_label)

        return main_layout


# 앱 실행
if __name__ == "__main__":
    TestApp().run()
