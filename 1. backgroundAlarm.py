from kivy.app import App
from kivy.uix.button import Button
from jnius import autoclass
 
class TestApp(App):
    def build(self):
        button = Button(text="Start Background Service")
        button.bind(on_press=self.start_service)
        return button
 
    def start_service(self, instance):
        SERVICE_NAME = 'org.test.mykivyapp.ServiceMyservice'
        service = autoclass(SERVICE_NAME)
        mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
        service.start(mActivity, '')
        print("Service Started")
 
if __name__ == '__main__':
    TestApp().run()
 