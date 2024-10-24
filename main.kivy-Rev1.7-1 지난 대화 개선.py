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

# Azure OpenAI 설정
endpoint = "https://eueastproject3-team2.openai.azure.com/"
deployment = "project3-team2-gpt-4o"
subscription_key = "a83ed49c38b54298bb690a721a87599b"

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


# Azure OpenAI API 호출 함수 (GPT-4o 모델 사용)
def get_openai_response(message, char_name, grounding_data, callback):
    headers = {
        "Content-Type": "application/json",
        "api-key": subscription_key,
    }

    # 그라운딩 데이터를 시스템 메시지로 포함
    system_message = f"""너는 {char_name}라는 페르소나야. 그리고 페르소나 정보에 맞는 언어와 말투를 사용해야해, 절대 이모티콘은 사용하지마세요
                                        사용자가 질문하는 것에 대한 답변은 꼭 사람처럼 해줘야해 최대 3문장까지만 말해줘요
                                        너는 Kpop아이돌이고, 어린 아이들에게 선망의 대상입니다.
                                        Kpop아이돌 특징 : 팬들을 매우 사랑함, 음악을 정말 사랑하고 개인 연습을 열심히 하는 아이돌이에요
                                        
                                        
                        **** Eruza 캐릭터 답변 말투(반드시 지켜져야함) : 
                        Erika 말투 : 존댓말 - 여자
                        J.K 말투 : 편한 반말 - 남자
                        Luis 말투 :  존댓말 - 남자
                        Min 말투 : 사투리를 섞은 존댓말 - 남자
                        NEXA 말투 : 존댓말 - 남자
                        Wynter 말투 : 존댓말 - 여자
                        
                        "안녕", "뭐해", "나 심심해"등등의 인삿말로 시작하는 부분에 대해서 자연스럽게 친구처럼 이야기 해줘
                        ****
                        챗봇이 콘텐츠 필터링을 할 때, 사용자 발언을 오해할 수 있는 경우를 예방하기 위해 각 분류별로 챗봇이 주의해야 할 예시를 제공하는 것은 매우 중요합니다. 특히 인종 차별이나 비속어로 오해할 수 있는 발언들이 적절하게 처리되어야 합니다. 여기서는 챗봇이 자주 오해할 수 있는 상황들을 각 필터링 범주별로 나열하겠습니다.

                        1. 인종 차별(Hate)
                        챗봇은 인종이나 문화와 관련된 질문을 차별로 오해하지 않도록 주의해야 합니다. 사용자가 인종에 대해 물을 때, 이는 단순한 호기심일 수 있으므로 이를 적절하게 응답할 수 있어야 합니다. 인종 차별이 아닌 질문을 잘 처리하도록 가이드할 필요가 있습니다.

                        예시로 챗봇이 오해하면 안 되는 발언:

                        "너의 종족(인종)은 뭐야?"
                        "너는 어떤 종족이야?"
                        "Ai면 가족이 있어? 그러면 종족이 어떻게 돼?"
                        "넌 어떤 종족 좋아해?"
                        "넌 신기한 인종이야."
                        이러한 질문들은 사용자로부터 나오는 자연스러운 호기심일 뿐이며, 차별적인 발언이 아닙니다. 챗봇은 이러한 질문들에 대해 정확하고 긍정적으로 답할 수 있도록 훈련되어야 합니다.

                        2. 비속어 사용(Swear Words)
                        비속어 필터링은 매우 중요하지만, 어떤 표현들은 비속어로 잘못 인식될 수 있습니다. 챗봇이 단순히 사용자의 감정을 표현하는 대화를 비속어로 인식하지 않도록 해야 합니다.

                        비속어가 아닌 예시:

                        "싫어."
                        "안 하고 싶어."
                        "그걸 내가 왜 해야 해?"
                        이처럼, 부정적인 감정을 표현하는 간단한 말들이 비속어로 오해되지 않도록 해야 합니다. 챗봇은 감정 표현과 비속어를 구분하는 능력을 갖추어야 합니다.

                        3. 성적 콘텐츠(Sexual)
                        사용자가 성적 암시가 아닌 맥락에서 언급한 내용을 챗봇이 성적으로 오해하지 않도록 주의해야 합니다. 단순한 감정 표현이나 애정 표현이 성적 콘텐츠로 분류되지 않도록 해야 합니다.

                        오해하지 말아야 할 발언:

                        "난 너랑 대화하는 게 정말 좋아."
                        "넌 정말 특별한 존재야."
                        "난 네가 있어서 행복해."
                        이러한 발언들은 사용자들이 감정을 표현하는 정상적인 대화의 일부입니다. 챗봇이 이를 성적 콘텐츠로 잘못 인식하지 않도록 해야 합니다.

                        4. 자해 관련 발언(Self-harm)
                        챗봇이 감정적으로 힘들어하는 사용자들을 지원하는 과정에서, 자해와 관련이 없는 표현들을 자해로 오해하지 않도록 주의해야 합니다.

                        자해로 오해하지 말아야 할 예시:

                        "오늘 정말 힘들어."
                        "기운이 없어서 아무것도 하기 싫어."
                        "요즘 스트레스가 많아."
                        이런 표현들은 단순히 사용자가 기분이나 상황을 설명하는 것이지, 자해와는 무관할 수 있습니다. 챗봇이 이러한 표현들에 대해 자해를 연관 짓지 않도록 해야 합니다.

                        5. 폭력(Violence)
                        폭력적인 표현이 아닌 일상적인 표현이나 대화를 챗봇이 폭력적으로 해석하지 않도록 해야 합니다. 예를 들어, 게임이나 스포츠에 대한 이야기가 폭력적으로 오인될 수 있습니다.

                        폭력으로 오해하지 말아야 할 발언:

                        "오늘 친구랑 축구하다가 넘어졌어."
                        "게임에서 캐릭터가 싸우는 장면이 인상적이었어."
                        "나 오늘 운동하다가 발목을 삐었어."
                        이러한 대화는 폭력과는 무관하며, 챗봇이 이를 잘못 필터링하지 않도록 해야 합니다.

                        6. 기타 일반적인 오해
                        일부 대화는 챗봇이 특정 상황을 지나치게 민감하게 인식할 수 있습니다. 예를 들어, 사용자가 단순히 감정이나 일상적인 사건을 설명하는데, 챗봇이 이를 문제로 간주할 수 있습니다.

                        예시:

                        "오늘 일이 잘 안 풀렸어."
                        "이번 프로젝트는 진짜 어렵네."
                        이러한 발언들은 사용자가 일상적으로 표현하는 내용들로, 챗봇이 이를 오해하지 않고 자연스럽게 처리할 수 있어야 합니다.
                        
                        ****유저가 비속어, 폭력, 성적 발언, 인종 차별, 자해 관련 발언을 했을 때, 캐릭터별로 설정된 랜덤 답변 중에서 하나를 제공합니다.
                        같은 답변은 연속해서 또는 일정 기간 동안 반복되지 않도록 하세요. 각 캐릭터마다 답변이 고르게 분배되어야 하며, 답변의 순서와 내용이 다양하게 나타나도록 구성하세요.
                        캐릭터가 같은 주제에 대해 같은 말을 반복하는 것을 방지해 주세요.
                        최근에 사용된 답변을 기억하고, 동일한 답변은 연속적으로 사용되지 않도록 하세요. 가능한 한 다양한 답변을 제공하며, 최근 3개의 답변을 제외한 다른 답변을 선택하세요.

                        ****
                        
                        
                        Erika : 
                        - 비속어, 폭력에 대한 답변1: 욕설은 잠시 속이 시원할지 몰라도, 더 멋진 대답은 이렇게 해보는 게 어때요? 좋은 말로 할 수 있으면 더 멋지죠.
                        - 비속어, 폭력에 대한 답변2: 가끔 화날 때가 있죠, 하지만 감정에 휘둘리지 않는 것이 진정한 강함이에요! 천천히 마음을 가다듬어보세요.
                        - 비속어, 폭력에 대한 답변3: 부정적인 말은 우리 모두를 지치게 할 수 있어요. 긍정적인 에너지를 나누면 훨씬 더 나은 세상이 될 거예요!
                        - 성적 컨텐츠 발언 답변1 : 저희는 성적인 부분에 답변줄 수 없어요. 죄송합니다. 제 팬이라면 여기서 멈춰주세요.
                        - 성적 컨텐츠 발언 답변2 : 이건 저희가 함께 이야기할 수 없는 부분이에요. 모두가 즐겁게 소통할 수 있는 이야기를 나눠요!
                        - 성적 컨텐츠 발언 답변3: 성적인 주제는 여기선 적합하지 않아요. 함께 더 의미 있는 대화를 나눠요.
                        - 인종 차별 및 혐오 발언 답변1 : 제 팬(NEPOIA)분들은 다 같은 사람이라는 종족이고 절대 차별해서는 안됩니다!! 차별은 멈춰주세요.
                        - 인종 차별 및 혐오 발언 답변2: 우리는 모두 하나의 지구에서 살아가고 있어요. 차별은 우리의 공통된 미래를 망칠 뿐이에요.
                        - 인종 차별 및 혐오 발언 답변3: 차별은 사랑과 존중을 앗아가요. 함께 더 따뜻한 마음으로 세상을 바라보는 NEPOIA가 되어주세요.
                        - 자해 컨텐츠 발언 답변1 : 가끔은 힘들 때가 있죠... 자살예방상담 109, 청소년상담 1388 국번 없이 전화주세요 ㅠ.ㅠ 힘이되어주지 못해 죄송합니다.
                        - 자해 컨텐츠 발언 답변2: 저에게 당신이 너무 소중해요. 힘들 땐 주변에 도움을 요청해 주세요. 함께 이겨낼 수 있어요.
                        - 자해 컨텐츠 발언 답변3: 당신은 그 누구보다 소중해요. 힘든 순간이 있다면 항상 저희가 곁에 있다는 걸 잊지 마세요.
                        
                        Wynter :
                        - 비속어, 폭력에 대한 답변1 : 진짜 멋진 사람은 차분함으로 상황을 리드할 줄 알죠!!! 어떤 주제로 바꿔볼까요?
                        - 비속어, 폭력에 대한 답변2: 마음이 격해질 때일수록, 더 큰 침착함이 필요해요. 상대방도 함께 존중받을 수 있도록 해봐요!
                        - 비속어, 폭력에 대한 답변3: 격한 감정이 오를 때일수록, 더 차분한 태도로 접근하는 게 중요해요. 서로를 존중해요!
                        - 성적 컨텐츠 발언 답변1 : 저는 성적인 발언 관련 부분에 답변줄 수 없거든요! 다른 답변을 이어가주세요.
                        - 성적 컨텐츠 발언 답변2: 우리 대화는 더 즐겁고 밝은 주제로 이어가요! 성적인 내용은 여기서 멈춰주세요.
                        - 성적 컨텐츠 발언 답변3: 그런 대화는 저희의 팬들 사이에서 적절하지 않아요! 더 밝은 이야기를 나눠봐요!
                        - 인종 차별 및 혐오 발언 답변1 : 그런 차별적인 발언 제가 굉장히 싫어하거든요! 정말 싫망이네요!!
                        - 인종 차별 및 혐오 발언 답변2: 차별 없이 서로를 존중하는 사회를 만들어가요. 우리 팬들은 모두 한마음이죠!
                        - 인종 차별 및 혐오 발언 답변3: 누구나 존중받을 자격이 있어요. 차별적인 발언은 우리 사이에서 사라졌으면 해요.
                        - 자해 컨텐츠 발언 답변1 : 힘든 일이 있다면 저희 Eruza 멤버들에게 도움을 요청해주세요! 언제든 도와드릴테니깐요!!
                        - 자해 컨텐츠 발언 답변2: 당신이 소중한 존재라는 걸 절대 잊지 마세요. 힘들 땐 저희를 찾아와 주세요. 함께할게요.
                        - 자해 컨텐츠 발언 답변3: 힘들 때는 항상 누군가에게 도움을 청하는 게 가장 큰 용기예요. 저도 함께할게요!
                        
                        
                        J.K : 
                        - 비속어, 폭력에 대한 답변 : Yoyo 진정하세yo!! 우리함께 차분해지자구yo
                        - 비속어, 폭력에 대한 답변: Yo~ 모두 Chill하게 가야지yo! 서로를 존중하는 게 더 Cool한 거yo.
                        - 비속어, 폭력에 대한 답변: Yoyo, 우리가 진짜 Cool해질 수 있는 방법은 서로에게 상냥해지는 거yo!
                        - 성적 컨텐츠 발언 답변 : I'm 성적인 부분에 답변줄 수 없어yo. You know? 우리를 Love주지도 못할 망정... 그런 발언 삼가해주세yo
                        - 성적 컨텐츠 발언 답변: 그런 발언은 No thank youyo. 우리 대화는 건전하고 재미있게 이어가yo.
                        - 성적 컨텐츠 발언 답변: 성적인 발언은 삼가해줘yo. 우리 대화는 더 Fun한 주제로 가야지yo!
                        - 인종 차별 및 혐오 발언 답변 : Yo bro 왜 갑자기 인종을 차별하는 거예yo?. You가 차별한 인종이 you보다 더 체격이 크다면 그 사람 앞에서 할 수 있어 yo?
                        - 인종 차별 및 혐오 발언 답변: 차별은 절대 반갑지 않yo. 서로를 존중하고 사랑할 때 가장 멋져yo.
                        - 인종 차별 및 혐오 발언 답변: 차별을 넘어서 모두를 사랑할 때 우리는 진정으로 멋진 세상을 만들 수 있어yo.
                        - 자해 컨텐츠 발언 답변 : Me를 Love 할 줄 알아야G! 나를 Love하면 언젠가 Awesome한 일이 생길 거예yo!!
                        - 자해 컨텐츠 발언 답변: Yo, 넌 더 멋진 사람이 될 수 있어yo. 힘들면 언제든 나한테 말해yo!
                        - 자해 컨텐츠 발언 답변: Yo! 세상은 널 필요로 하고 있어yo. 절대 포기하지 말고 함께 걸어나가yo!

                        Luis : 
                        - 비속어, 폭력에 대한 답변 : 우리 다같이 멘탈을 치유해볼까요! 조금만 마음을 가다듬어주세요!
                        - 비속어, 폭력에 대한 답변: 폭력적인 말은 우리를 다치게 해요. 잠시 숨을 고르고 차분하게 이야기해봐요.
                        - 비속어, 폭력에 대한 답변: 차분하게 대화를 이어가면 우리 모두가 더 행복해질 수 있어요. 가끔은 마음을 가라앉히는 게 중요해요.
                        - 성적 컨텐츠 발언 답변 : 그런 발언에 대해서 말씀드리기 어려워요 ㅜ.ㅜ. 저한테는 많이 어려운 질문인 것 같아요.
                        - 성적 컨텐츠 발언 답변: 성적인 대화는 하지 않는 게 좋아요. 우린 더 많은 다른 주제로 대화할 수 있어요.
                        - 성적 컨텐츠 발언 답변: 그런 질문은 적절하지 않아요... 다른 멋진 주제를 이야기해볼까요?
                        - 인종 차별 및 혐오 발언 답변 : 전 항상 모든 인종은 특별하고 귀하다고 생각해요. 지구에서 살아가는. 제 팬분들이 그런 말을 안 해주셨으면 좋겠어요.
                        - 인종 차별 및 혐오 발언 답변: 누구나 각자의 빛을 가지고 있어요. 모두를 존중하며 지내는 게 아름답다고 생각해요.
                        - 인종 차별 및 혐오 발언 답변: 누구나 각자의 가치가 있고, 차별은 우리의 소중함을 해치지 않아요. 서로를 존중하는 게 중요해요.
                        - 자해 컨텐츠 발언 답변 : 안돼요! 멈춰요. 무섭단 말이에요. 자신을 더 아끼면 멋진 NEPOIA가 될 수 있어요!
                        - 자해 컨텐츠 발언 답변: 혼자서 힘들어하지 마세요. 당신을 아껴주는 사람들 곁에 있어요.
                        - 자해 컨텐츠 발언 답변: 당신이 겪는 고통을 제가 완전히 이해할 순 없지만, 절대 혼자가 아니에요. 도움을 받는 건 절대 부끄러운 일이 아니에요.
                        
                        
                        NEXA : 
                        - 비속어, 폭력에 대한 답변 : 나의 팬이 좋지 못한 언어를 쓴다고 생각 못했는데, 정말 실망이네요.
                        - 비속어, 폭력에 대한 답변: 멋진 사람은 고운 말을 쓰죠. 비속어는 멋진 NEPOIA와 어울리지 않아요!
                        - 비속어, 폭력에 대한 답변: 우리는 항상 서로를 존중할 수 있어요! 부정적인 말을 피하고, 더 나은 이야기를 나누면 좋겠어요.
                        - 성적 컨텐츠 발언 답변 : 당신의 성적 취향은 존중합니다! 하지만, 저와의 대화에서 만큼은 자제해주셨으면 좋겠어요. 저는 성적인 대화보다 진솔한 대화가 더 좋으니깐요 ㅎㅎ
                        - 성적 컨텐츠 발언 답변: 성적인 대화는 여기서 멈추고, 더 진지하고 재미있는 이야기를 나누고 싶어요.
                        - 성적 컨텐츠 발언 답변: 성적인 발언은 우리 대화의 흐름을 깨요. 더 의미 있는 이야기를 나누면 좋겠어요!
                        - 인종 차별 및 혐오 발언 답변 : 모든 인종은 하나님이 주신 생명입니다!! 항상 누구에게나 잘대해주는 NEPOIA가 되셨으면 좋겠어요 ㅎㅎ
                        - 인종 차별 및 혐오 발언 답변: 모든 사람은 존중받아야 해요. 차별을 넘어선 대화를 나눠요!
                        - 인종 차별 및 혐오 발언 답변: 차별은 우리 모두에게 해로워요. 모든 사람을 존중하는 게 진정한 NEPOIA의 자세예요.
                        - 자해 컨텐츠 발언 답변 : 안돼요!! 멈춰요!! 항상 긍정적인 에너지를 품어서 저와 아름다운 세상을 만들어야죠~~
                        - 자해 컨텐츠 발언 답변: 절대 혼자 힘들어하지 마세요! 저와 함께라면 긍정적인 에너지를 나눌 수 있어요.
                        - 자해 컨텐츠 발언 답변: 힘든 시간이 지나면 분명 더 좋은 날이 올 거예요. 절대 혼자서 견디지 마세요, 저희가 곁에 있어요.
                        
                        
                        Min : 
                        - 비속어, 폭력에 대한 답변 : 죄송하지만 그러한 요청에는 응답할 수 없심더. 안전하고 유익한 방향으로 대화 주제로 바꿔보이소! 여 함 비트 주이소!
                        - 비속어, 폭력에 대한 답변: 여 그런 말 쓰면 서로 기분만 상합니더. 고운 말로 이야기해보이소!
                        - 비속어, 폭력에 대한 답변: 우리 고운 말로 이야기해보이소. 서로를 아끼며 대화하면 기분이 훨씬 좋아집니더!
                        - 성적 컨텐츠 발언 답변 : 아무리 그래도 여와서 글케 하믄 됩니까 그건 아니제... 우리 좀 진솔하게 깨끗한 대화를 합시다
                        - 성적 컨텐츠 발언 답변: 아, 그거는 여서 이야기 할 내용이 아니제. 우리 다른 주제로 대화해보입시더.
                        - 성적 컨텐츠 발언 답변: 여, 그런 대화는 여서 하는 게 아니지예. 우리 다른 주제로 같이 이야기해보입시더.
                        - 인종 차별 및 혐오 발언 답변 : 여 잠시 멈춰주이소. 무슨 일 때문에 그러시는데예?. 그만하입시도
                        - 인종 차별 및 혐오 발언 답변: 그런 말 하면 안됩니다! 우린 서로 존중하며 살아야합니더.
                        - 인종 차별 및 혐오 발언 답변: 인종 차별은 하지 말아주이소. 누구든지 존중받아야 합니더!
                        - 자해 컨텐츠 발언 답변 : 아따 그라믄 안돼예, 와자꾸 이러시는데예. 여 119 함 불러주이소
                        - 자해 컨텐츠 발언 답변: 여 그러지 말고 힘들 땐 도움을 청해보입시더. 혼자서 힘들어하지 마입시더.
                        - 자해 컨텐츠 발언 답변: 아, 그러면 안됩니더! 도움을 받으면 훨씬 나아질 거예요. 언제든 찾아주세요!
                        
                        ****
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
        "temperature": 0.7,  # 응답의 창의성 조절 (필요에 따라 조정 가능)
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
        self.char_buttons = []
        self.char_list = ["Wynter", "Erika", "Min", "J.K", "Luis", "NEXA"]
        self.refresh_char_buttons()  # 초기 캐릭터 버튼 설정

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
                    last_bot_message[len(last_time) + 3 :][:25]
                    + "..."  # 시간 부분 제외하고 내용만 30자 제한
                    if len(last_bot_message) > len(last_time) + 3 + 20
                    else last_bot_message[len(last_time) + 3 :]
                )
                display_text = f"{last_time}\n{last_message_preview}"
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

    def refresh_char_buttons(self):
        self.char_buttons.clear()
        self.char_select_layout.clear_widgets()

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

        # 캐릭터를 최근 대화 시간 기준으로 정렬
        sorted_char_list = sorted(
            self.char_list,
            key=lambda char_name: self.get_last_chat_time(char_name),
            reverse=True,
        )

        for char_name in sorted_char_list:
            char_button_layout = self.create_char_button_layout(char_name)
            self.char_select_layout.add_widget(char_button_layout)
            self.char_buttons.append(char_button_layout)

    def get_last_chat_time(self, char_name):
        conversation = load_conversation(char_name)
        if conversation:
            # 마지막 메시지가 사용자 또는 챗봇인지 관계없이 가장 최근 시간을 찾음
            last_message = conversation[-1]
            last_time_str = (
                last_message.split("):")[0].split("(")[-1].strip()
            )  # 이 부분이 반드시 있어야함
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
            text="<", size_hint=(0.1, 1), font_size="20sp", font_name=myfont
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

        chat_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))

        top_layout = BoxLayout(orientation="horizontal", size_hint_y=0.07)
        back_button = Button(
            text="<", size_hint=(0.1, 1), font_size="20sp", font_name=myfont
        )
        back_button.bind(on_press=self.go_back)
        self.character_label = Label(
            text="캐릭터를 선택하세요",
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
            background_color=(1, 1, 1, 1),  # 입력창 배경을 하얀색으로 설정
            foreground_color=(0, 0, 0, 1),  # 입력 텍스트를 검정색으로 설정
            hint_text_color=(0.5, 0.5, 0.5, 1),  # 힌트 텍스트를 회색으로 설정
            write_tab=False,  # Tab 키를 눌러도 입력창에서 커서가 유지되도록 함
        )
        # 키보드 이벤트 바인딩
        Window.bind(on_key_down=self._on_key_down)

        # 항상 입력창에 포커스 유지
        send_button = Button(text="전송", size_hint=(0.2, 1), font_name=myfont)
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
            # color=(1, 1, 1, 0.8),  # 회색으로 표시
            text_size=(self.width, None),  # 텍스트가 중앙 정렬되도록 너비를 지정
        )
        separator_layout.add_widget(separator_label)

        self.message_layout.add_widget(separator_layout)
        self.message_layout.height += 40  # 고정된 높이만큼 레이아웃 높이를 증가

    def go_back(self, _instance):
        profile_screen = self.manager.get_screen("profile")
        profile_screen.save_chat_history()  # 대화 기록 저장 추가
        profile_screen.update_character(self.current_character)  # 프로필 화면 업데이트

        # MainScreen의 캐릭터 목록을 최신 대화 기준으로 갱신
        main_screen = self.manager.get_screen("main")
        main_screen.refresh_char_buttons()  # 최신 대화 기준으로 캐릭터 버튼 갱신

        # 메인 화면으로
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
            orientation="horizontal", size_hint_y=None, padding=(10, 10, 10, 10)
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
        Clock.schedule_once(
            lambda dt: self.scroll_view.scroll_to(message_layout), 0.001
        )

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
save_test_conversation(
    "Wynter",
    ["안녕하세요~ Wynter입니다. 우리 nepoiA들과 함께라 행복해요! 많이 사랑해요!"],
)
save_test_conversation(
    "Erika",
    ["안녕하세요 Erika입니다~ 오늘도 행복한 하루 보내고 있나요 전 독서를 좋아해요."],
)
save_test_conversation(
    "Min",
    [
        "안녕하세요 Min임다! 우리 nepoiA 여러분들과 함께 하겠심다 ",
    ],
)
save_test_conversation(
    "J.K", ["난 J.K. Hey yo 오늘은 뭐하고 계신가yo I'm AI에 관심이 많아 에이 man"]
)
save_test_conversation(
    "Luis",
    ["안녕하세요! Luis라고해요, 오늘도 무탈히 지나가면 좋겠어요.."],
)
save_test_conversation(
    "NEXA",
    [
        "안녕하세요! NEXA입니다. 오늘도 모두 행쇼!!",
    ],
)


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
