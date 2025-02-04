# 버츄얼 아이돌 CS 챗봇 내용 설명

해당 프로젝트는 버츄얼 아이돌은 Microsoft AI School 4기 내부적으로 발표하기 위한 기준으로 만들어졌으며, 버츄얼 아이돌 캐릭터로 팬미팅을 한다는 조건으로 만들어지게 되었습니다.
팬미팅 대상은, Microsoft 임/직원, Elixirr 임/직원, AI School 4기 동기생들을 대상으로 합니다.
CS 챗봇은 버츄얼 아이돌을 팬들과 팬덤에게 커뮤니티 형성을 하기 위한 "CS 챗봇"이라는 프로그램을 만들게 되었습니다.

# 프로젝트 진행 사유

AI를 활용하여 재미 요소를 붙이고자, "버츄얼 아이돌"이라는 계획을 세우게 되었고 시장조사 당시 한국과 일본에서 가상의 여자친구, 남자친구 챗봇이 인기 있었다는 소식에 매료되어
버츄얼 아이돌의 매력을 알리고자 진행하게 되었습니다. 또한 Microsoft가 Unity를 인수하여 기술 조화를 이루려는 것을 참작하여 Microsoft Azure Cognitive Service와 Unity를 활용한 프로젝트를 진행하게 되었습니다.

### CS 챗봇 생성 부가 설명

※ Unity와 Blender, Vroid Studio를 활용한 모델링 작업은 다른 프로젝트 구성원이 진행하여 파일에 존재 하지 않음을 인지 부탁드립니다.
프로젝트 구성원 6명이 각 버츄얼 아이돌 캐릭터를 맡았고 캐릭터는 Blender, vroid Studio로 모델링하여
미디어파이프를 통해 각 캐릭터의 손가락이나 몸짓을 인식하게 끔하여 캐릭터의 생동감을 표현했습니다.

## 주요 기능

1. AI 대화 생성 (Auzre Service GPT-4o): 사용자의 입력에 대한 AI 응답 생성
   ![스크린샷 2024-10-18 163128](https://github.com/user-attachments/assets/508a98bc-e936-4d05-8837-c41d69aa2d05)
   
   - 통합앱 내부 사진
     
   ![image](https://github.com/user-attachments/assets/2aadc430-718d-4d65-a5bb-c5b0aeb70672)

2. 텍스트-음성 변환(Azure TTS) SSML형식: 텍스트 답변을 음성으로 변환
 
 ![스크린샷 2024-10-25 150749](https://github.com/user-attachments/assets/a5b78e07-da8a-4704-a0ec-717e1e1d377c)

4. 텍스트-음성 아바타(Azure 3D Avatar): 아나운서 타입의 한국어 지원가능 캐릭터가 팝업 형식으로 나타나 AI 음성을 생성
 
  ![스크린샷 2024-10-25 160644](https://github.com/user-attachments/assets/da134c0f-488c-49d9-8261-4e340d9a6ad6)

6. 컨텐츠 필터링(Microsoft AI 6대 윤리원칙 기준 적용): 악의적인 사용자가 성적발언,욕설, 불법, 인종차별, 가상 답변(할루시네이션), Jail break 막기 위함

  ![스크린샷 2024-10-24 235930](https://github.com/user-attachments/assets/9f3efa1c-a375-4e53-8881-20941b11168e)


## 설치 방법

1. 필요한 패키지 설치 :
 ```
  pip install -r requirements.txt'하여 설치에 필요한 패키지를 실행한다.
 ```
2. '.env'파일을 생성하고 다음 환경 변수를 설정:
   - AZURE_OPEN_AI_END_POINT
   - AZURE_OPENAI_ENDPOINT
   - AZURE_OPEN_AI_API_name
   - AZURE_OPEN_AI_API_KEY
   - AZURE_OPEN_AI_DEPLOYMENT_NAME
   - SPEECH_ENDPOINT
   - SUBSCRIPTION_KEY
   

## 사용 방법

1. 'main.kivy-Rev1.8 지난 대화 기록 변경.py'파일을 열어 실행합니다.
2. Kivy 프로그램이 실행될 때 6명의 캐릭터(Wynter, Erika, Min, J.K, Luis, Nexa)의 네모난 대화창을 누릅니다.
   - 성격, 하고싶은 것, 좋아하는 것에 대한 내용을 적는다.
   - 캐릭터가 답변을 주면, 대화를 이어 나간다.
   - 버츄얼 아이돌의 라이브 팬미팅 때 했던 이야기를 주고 받으며 이야기를 이어나간다.
3. 'Chatbot-Test-Speech-REV1.6 최종버전.py'파일을 열어 실행합니다.
   - 챗봇과 대화를 하기 위한 문의사항을 남깁니다.
     
     - ![image](https://github.com/user-attachments/assets/f6d33dc0-bded-475d-b089-ab584b7ab959)
       
   - CS chatbot은 다운로드 받은 어플리케이션을 탈퇴하는 방법 또는 에러 현상에 대해 문의하면 답변을 받을 수 있습니다.
   - CS Chatbot에게 질문 후, 10초 내외로 3D Avatar가 생성되며 chatbot의 답변을 읽어줍니다.
     
     - ![스크린샷 2024-10-25 160644](https://github.com/user-attachments/assets/da134c0f-488c-49d9-8261-4e340d9a6ad6)

## 주의사항

- 프로젝트는 Azure AI 서비스를 사용하므로, 관련 API키와 엔드포인트가 필요합니다.
- CS 챗봇 사용 시 3D Avatar가 생성되는 부분은 비용이 많이 소모되니 이점 참고 부탁드립니다.


##문의

질문 또는 이슈가 있다면 문의 부탁드립니다.
