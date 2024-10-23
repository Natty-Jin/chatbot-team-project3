import time
import threading
from jnius import autoclass
from kivy.logger import Logger

# 안드로이드 네이티브 클래스
PythonService = autoclass('org.kivy.android.PythonService')
Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')
AlarmManager = autoclass('android.app.AlarmManager')
PendingIntent = autoclass('android.app.PendingIntent')
VERSION = autoclass('android.os.Build$VERSION')
Build = autoclass('android.os.Build')

def set_system_alarm():
    try:
        Logger.info('MyService: Setting system alarm...')
 
        service = PythonService.mService
        context = service.getApplicationContext()
 
        # AlarmClock 인텐트를 사용하여 시스템 알람 설정
        AlarmClock = autoclass('android.provider.AlarmClock')
        intent = Intent(AlarmClock.ACTION_SET_ALARM)
 
        # 알람 설정 시간 (현재 시간으로부터 1분 후로 설정)
        trigger_time = time.localtime(time.time() + 5)  # 1분 후
        hour = trigger_time.tm_hour
        minute = trigger_time.tm_min
 
        # 인텐트에 알람 시간 및 기타 설정 추가
        intent.putExtra(AlarmClock.EXTRA_HOUR, hour)
        intent.putExtra(AlarmClock.EXTRA_MINUTES, minute)
        intent.putExtra(AlarmClock.EXTRA_MESSAGE, '설정된 시간이 되었습니다!')
        intent.putExtra(AlarmClock.EXTRA_SKIP_UI, True)  # 알람 앱의 UI를 표시하지 않음
 
        # 새로운 태스크로 시작
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
 
        # 인텐트를 사용하여 알람 설정
        context.startActivity(intent)
 
        Logger.info('MyService: System alarm set for {}:{}'.format(hour, minute))
    except Exception as e:
        Logger.error('MyService: Exception in set_system_alarm:')
        import traceback
        Logger.error('MyService: {}'.format(traceback.format_exc()))
 
def alarm_loop():
    try:
        while True:
            set_system_alarm()
            time.sleep(5)  # 1시간마다 알람 설정
    except Exception as e:
        Logger.error('MyService: Exception in alarm_loop:')
        import traceback
        Logger.error('MyService: {}'.format(traceback.format_exc()))
 
def main():
    Logger.info('MyService: Service started')
 
    # 서비스 객체 가져오기
    service = PythonService.mService
 
    # 포그라운드 서비스용 알림 채널 생성
    channel_id = 'foreground_service_channel'
    channel_name = 'Foreground Service Channel'
    notification_manager = service.getSystemService(Context.NOTIFICATION_SERVICE)
 
    if VERSION.SDK_INT >= 26:
        importance = notification_manager.IMPORTANCE_LOW
        notification_channel = autoclass('android.app.NotificationChannel')(channel_id, channel_name, importance)
        notification_manager.createNotificationChannel(notification_channel)
 
    # 포그라운드 서비스 알림 빌드
    NotificationCompatBuilder = autoclass('androidx.core.app.NotificationCompat$Builder')
    builder = NotificationCompatBuilder(service, channel_id)
    builder.setSmallIcon(service.getApplicationInfo().icon)
    builder.setContentTitle('서비스 실행 중')
    builder.setContentText('백그라운드 서비스가 실행 중입니다.')
    builder.setOngoing(True)
 
    # 포그라운드 서비스 시작
    service.startForeground(1, builder.build())
 
    # 알람 루프를 별도의 스레드에서 실행
    threading.Thread(target=alarm_loop).start()
 
if __name__ == '__main__':
    main()