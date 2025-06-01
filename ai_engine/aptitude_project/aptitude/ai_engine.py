import json
import moviepy as mp
import os
import whisper
from pypdf import PdfReader
import requests, base64
from copy import deepcopy
import time
import re

VIDEO_INTERVIEW_FILE = "/content/interview_sample.mp4"
AUDIO_INTERVIEW_FILE = "/content/interview_sample.mp3"

WHISPER_MODEL = whisper.load_model("medium")#,  device="cuda")  # "base", "small", "medium", "large"
LLAMA_INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
LLAMA_ACCESS_TOKEN = "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"

LLAMA_REQUEST_HEADERS = {
    "Authorization": f"Bearer {LLAMA_ACCESS_TOKEN}",
    "Accept": "application/json"
}

PARSE_RESUME_PROMPT = """
Act as a resume parser. parse the given string of pdf resume to a generalized paragraph format explaining all the attributes mentioned in input text. generated information should be in first person point of view.
Do not add up values on your own. always keep the information as original. Do not add up decoration style for example "", **, etc. Do not mention personal contact details if exists. Do not add details reasons and details from the input prompt.
Do not add "NOTE" information to the output.
###
resume_text : {pdf_text}
"""

TEXT_PROCESS_PROMPT = """
Act as a text parser, As the AUDIO_TRANSCRIPTION and RESUME_TEXT belong to the same indiviual, parser and merge the given text to generate a good professional summary from the input AUDIO_TRANSCRIPTION and RESUME_TEXT.
Do not mention comparison between the two texts. Do not add up values on your own. always keep the information as original. Do not add up decoration style for example "", **, etc. Do not mention personal contact details if exists. Do not add details reasons and details from the input prompt.
Do not add "NOTE" information to the output.
###
AUDIO_TRANSCRIPTION : {audio_transcription}
RESUME_TEXT : {resume_text}
"""

MAIN_PROMPT = """
Act as a career guidence instructor. provide detailed information of a career guidence for given USER_INFO and APTITUDE_TEST.
Provide information on 2 options for career paths, along with competitive only if aligned with the given USER_INFO and APTITUDE_TEST.
Provide information on any possible courses for the individual that will help to enhance career opportunites.
generated information should be only for Indian students aligned with Indian Education System/ NEP-based courses/ Indian Institution Competitive Exams.
Do not add up values on your own. always keep the information as original. Do not include any formatting styles such as quotation marks, asterisks, or similar elements.
Do not mention personal contact details if exists. Do not add "NOTE" information to the output.

Generated output should be in JSON format with 3 keys as below.
{"career_path": "", "suggested_courses": "", "competitive_exam": ""}
###
USER_INFO : {user_info}
APTITUDE_TEST : {aptitude_test}
###
"""

class AI_ENGINE:
    def __init__(self, audio_file, aptitude_test_json={}, vid_file="", pdf_file_path=""):
        self.video_interview_file = vid_file
        if not audio_file:
            audio_file = vid_file.split(".")[0] + ".mp3"
        self.audio_interview_file = audio_file.replace("\\", "/")
        self.aptitude_test_json = aptitude_test_json
        self.pdf_file_path = pdf_file_path

        self.audio_transcription = None
        self.resume_text = None
        self.merge_individual_summary = None
        self.career_path = None

    def convert_video_to_audio(self):
      try:
          clip = mp.VideoFileClip(self.video_interview_file)
          clip.audio.write_audiofile(self.audio_interview_file)
          clip.close()
      except Exception as e:
          print(f"Error occurred in convert_video_to_audio: {e}")

    def convert_audio_to_text(self):
        print(f"[+] self.audio_interview_file: {self.audio_interview_file}")
        if os.path.exists(self.audio_interview_file):
            try:
                self.audio_transcription = WHISPER_MODEL.transcribe(self.audio_interview_file)
            except Exception as e:
                print(f"Error occurred in convert_audio_to_text: {e}")
        else:
            print("Faild to locate audio interview file...")

    def get_resume_details(self):
        pdf_reader = PdfReader(self.pdf_file_path)
        self.resume_text = "\n\n".join([page_.extract_text() for page_ in pdf_reader.pages])

        if len(self.resume_text.split(" ")) > 10:
            prompt = PARSE_RESUME_PROMPT.replace("{pdf_text}", self.resume_text)
            self.resume_text = self.llama_api_call(prompt)
        else:
            print("Faild to parse resume text...")

    @staticmethod
    def llama_api_call(prompt, temperature=1, max_tokens=1000, top_p=1, response_format=None):
        results = ""
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": "meta/llama-3.1-405b-instruct",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": 0.00,
            "presence_penalty": 0.00,
            "stream": False,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        try:
            response = requests.post(LLAMA_INVOKE_URL, headers=LLAMA_REQUEST_HEADERS, json=payload)
            if response.status_code == 200:
                comp = response.json()
                results = comp["choices"][0]["message"]["content"]
            else:
                results = response.text
        except Exception as e:
            print(f"Error occurred in llama_api_call: {e}")
        return results

    def process_inputs(self):
        if self.audio_transcription is not None and self.resume_text is not None:
            text_process = TEXT_PROCESS_PROMPT.format(audio_transcription=self.audio_transcription["text"], resume_text=self.resume_text)
            self.merge_individual_summary = self.llama_api_call(text_process)
        elif self.resume_text:
            self.merge_individual_summary = deepcopy(self.resume_text)
        elif self.audio_transcription:
            self.merge_individual_summary = deepcopy(self.audio_transcription)
        else:
            print("Faild to locate audio transcription or resume text...")

    def get_career_path(self):
        if self.merge_individual_summary is not None:
            prompt = MAIN_PROMPT.replace("{user_info}", self.merge_individual_summary).replace("{aptitude_test}", json.dumps(self.aptitude_test_json))
            resp = self.llama_api_call(prompt)
            try:
                match = re.search(r'\{[\s\S]*\}', resp)  # [\s\S] matches newlines too
                if match:
                    json_str = match.group()
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        print("Failed to parse JSON:", e)
                else:
                    print("No JSON found")
                self.career_path = json.loads(data)
            except Exception as e:
                self.career_path = {"career_path": resp}
        else:
            print("Faild to locate merge_individual_summary...")

    def main(self):
        if os.path.exists(self.video_interview_file):
            self.convert_video_to_audio()
        # time.sleep(5)
        self.convert_audio_to_text()
        self.get_resume_details()
        self.process_inputs()
        self.get_career_path()

        if self.career_path is not None:
            for key, value in self.career_path.items():
                print(f"{key}: {value}")
        else:
            print("Faild to generate career_path...")

