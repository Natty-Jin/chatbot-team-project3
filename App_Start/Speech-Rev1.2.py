import os
import threading
import azure.cognitiveservices.speech as speechsdk
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label

# Azure 음성 서비스 설정
speech_key = os.environ.get('SPEECH_KEY')
speech_region = os.environ.get('SPEECH_REGION')
if not speech_key or not speech_region:
    raise ValueError("환경 변수 'SPEECH_KEY'와 'SPEECH_REGION'을 올바르게 설정해 주세요.")
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

# 한국어 음성 설정
speech_config.speech_synthesis_voice_name = 'ko-KR-HyunsuNeural'

# 음성 합성기
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

class SpeechApp(App):
    def build(self):
        # 레이아웃
        layout = BoxLayout(orientation='vertical')

        # 입력 및 출력 위젯
        self.input_text = TextInput(hint_text='텍스트를 입력하세요...', size_hint=(1, 0.6), multiline=True, font_size='20sp', padding=(10, 10))
        self.speak_button = Button(text='말하기', size_hint=(1, 0.2), on_press=self.speak_text, font_size='20sp')
        self.status_label = Label(text='상태: 대기 중...', size_hint=(1, 0.2), font_size='18sp')

        # 레이아웃에 위젯 추가
        layout.add_widget(self.input_text)
        layout.add_widget(self.speak_button)
        layout.add_widget(self.status_label)

        return layout

    def speak_text(self, instance):
        text = self.input_text.text
        if text:
            # UI 블로킹을 피하기 위해 새로운 스레드에서 음성 합성 시작
            threading.Thread(target=self.synthesize_speech, args=(text,)).start()

    def synthesize_speech(self, text):
        self.update_status('스피치 생성 중...')
        try:
            # 음성 합성 수행
            result = speech_synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                self.update_status('스피치가 성공적으로 생성되었습니다.')
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                self.update_status('스피치 생성이 취소되었습니다: {}'.format(cancellation_details.reason))
                if cancellation_details.reason == speechsdk.CancellationReason.Error and cancellation_details.error_details:
                    self.update_status('에러 세부사항: {}'.format(cancellation_details.error_details))
        except Exception as e:
            self.update_status('오류 발생: {}'.format(e))

    def update_status(self, status_text):
        # 메인 스레드에서 상태 레이블 업데이트
        self.status_label.text = '상태: ' + status_text

if __name__ == '__main__':
    SpeechApp().run()