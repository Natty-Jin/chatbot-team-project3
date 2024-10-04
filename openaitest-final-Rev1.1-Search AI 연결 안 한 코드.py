import docx
import PyPDF2
import gradio as gr
import os
from openai import AzureOpenAI


# 파일에서 내용을 읽어오는 함수들
def read_txt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def read_docx_file(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def read_pdf_file(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])

def read_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.txt':
        return read_txt_file(file_path)
    elif ext == '.docx':
        return read_docx_file(file_path)
    elif ext == '.pdf':
        return read_pdf_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# 그라운딩 데이터 폴더에서 모든 파일을 읽어와서 시스템 메시지에 추가
def load_grounding_data(folder_path):
    grounding_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.txt', '.docx', '.pdf')):
                grounding_files.append(os.path.join(root, file))

    grounding_data = {}
    for file_path in grounding_files:
        try:
            file_content = read_file(file_path)
            persona_name = os.path.splitext(os.path.basename(file_path))[0]  # 파일 이름을 페르소나 이름으로 사용
            grounding_data[persona_name] = file_content
            print(f"Successfully added content from {file_path}")
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")

    return grounding_data


# 그라운딩 데이터 폴더 경로 설정
grounding_data_folder = 'grounding-data'  # 폴더 경로를 지정하세요.

# Azure OpenAI 설정
endpoint = "https://eueastproject3-team2.openai.azure.com/"
deployment = "project3-team2-gpt-4o"
subscription_key = "a83ed49c38b54298bb690a721a87599b"  # API 키

# Initialize Azure OpenAI client with key-based authentication
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2024-05-01-preview",
)

# GPT 호출 함수
def ask_hanseoyun(prompt, persona, history):
    # 그라운딩 데이터를 시스템 메시지에 포함
    grounding_data = load_grounding_data(grounding_data_folder)

    if persona in grounding_data:
        persona_data = grounding_data[persona]
        system_message = f"너는 {persona}라는 페르소나야. 이 페르소나의 정보는 다음과 같아:\n\n{persona_data}\n\n" \
                         f"**추가**: 마지막 대화의 페르소나가 {persona}였기 때문에 이후 질문도 이 페르소나를 기준으로 대답해줘."
    else:
        system_message = f"페르소나 정보가 없어. 현재 선택된 페르소나는 {persona}이지만, 해당 정보는 불러올 수 없어."

    # GPT와의 대화 설정
    completion = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_message},  # 선택된 페르소나의 데이터 포함
            {"role": "user", "content": prompt},
        ],
        max_tokens=4000,
        temperature=0.3,
        top_p=0.75,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None, 
        stream=False,
    )

    # ChatCompletion 객체를 딕셔너리로 변환하고 content 값 추출
    completion_dict = completion.to_dict()
    content_value = completion_dict["choices"][0]["message"]["content"]

    # history에 사용자의 질문과 AI의 응답을 추가
    history.append((prompt, content_value))

    # history와 빈 입력 필드를 반환
    return history, ""


# Gradio 인터페이스 설정
def get_available_personas():
    # 폴더에서 사용할 수 있는 페르소나 이름 목록을 추출
    grounding_data = load_grounding_data(grounding_data_folder)
    return list(grounding_data.keys())


with gr.Blocks() as demo:
    gr.Markdown("# 2조의 버츄얼 아이돌과 대화")

    available_personas = get_available_personas()  # 페르소나 리스트

    with gr.Row():
        with gr.Column(scale=3):
            persona_dropdown = gr.Dropdown(label="페르소나를 선택하세요", choices=available_personas, value=available_personas[0])
            chatbot = gr.Chatbot()  # 대화형 UI 생성
            with gr.Column():
                prompt = gr.Textbox(
                    label="질문을 입력하세요",
                    placeholder="프롬프트를 입력하세요",
                    scale=5,
                )
                send_button = gr.Button("전송", scale=1)
                clear_button = gr.Button("대화창 지우기", scale=1)

            # 전송 버튼을 submit 방식으로 연결
            prompt.submit(
                fn=ask_hanseoyun, inputs=[prompt, persona_dropdown, chatbot], outputs=[chatbot, prompt]
            )

            # 전송 버튼 클릭 시에도 동일한 함수 호출
            send_button.click(
                fn=ask_hanseoyun, inputs=[prompt, persona_dropdown, chatbot], outputs=[chatbot, prompt]
            )

            # 대화창 지우기 버튼 클릭 시 대화 기록을 지우는 기능
            clear_button.click(lambda: None, None, chatbot, queue=False)

    demo.launch(share=True)
