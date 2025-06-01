from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Question, Option
from .serializers import QuestionSerializer
import json
from .forms import UploadForm
import tempfile, os
from .ai_engine import AI_ENGINE
from django.conf import settings
from django.utils.text import slugify
from datetime import datetime
from pymongo import MongoClient
import json
from .forms import AptitudeTestForm
from django.http import JsonResponse

CLIENT = MongoClient("mongodb://localhost:27017/")
USER_RESPONSES = CLIENT["user_reponses"]["user_responses"]
USER_RESPONSES = CLIENT["apti_question"]["apti_question"]

QUESTIONS_DATA = {"quewstions": list(USER_RESPONSES.find({}, {"_id": 0}, sort=[("id", 1)]))}

UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


from django.views.decorators.http import require_http_methods
from .forms import UploadForm
from pymongo import MongoClient

# assuming you have the following in your views.py
CLIENT = MongoClient("mongodb://localhost:27017/")
USER_RESPONSES = CLIENT["user_reponses"]["user_responses"]

class AptitudeTestView(APIView):
    def get(self, request):
        try:
            for item in QUESTIONS_DATA.get('questions', []):
                question_text = item.get('text')
                options_dict = item.get('options', {})

                # Prevent duplicates by checking if question exists
                question, created = Question.objects.get_or_create(text=question_text)

                # If question was just created, add its options
                if created:
                    for key, opt_text in options_dict.items():
                        Option.objects.create(question=question, key=key, text=opt_text)

            questions = Question.objects.all()
            serializer = QuestionSerializer(questions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except FileNotFoundError:
            return Response({"error": "Question file not found"}, status=status.HTTP_404_NOT_FOUND)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format"}, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request):
        data = request.data
        # Simulate calling AI engine or processing logic
        return Response({"message": "Processed successfully", "data": data})



def test_form_view(request):
    if request.method == 'POST':
        form = AptitudeTestForm(request.POST, request.FILES)
        print(form.is_valid())
        print("Form errors:", form.errors)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            video = form.cleaned_data['video_file']
            pdf = form.cleaned_data['pdf_file']

            # Collect question responses
            questions_data = []
            for key in request.POST:
                if key.startswith("question_"):
                    qid = int(key.split("_")[1])
                    selected = request.POST[key]
                    questions_data.append({"id": qid, "selectedOption": selected})

            # Save files
            video_filename = f"{slugify(video.name.rsplit('.', 1)[0])}_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
            video_path = os.path.join(UPLOAD_DIR, video_filename)
            with open(video_path, 'wb+') as destination:
                for chunk in video.chunks():
                    destination.write(chunk)

            pdf_filename = f"{slugify(pdf.name.rsplit('.', 1)[0])}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
            with open(pdf_path, 'wb+') as destination:
                for chunk in pdf.chunks():
                    destination.write(chunk)


            for qdx, ques in enumerate(questions_data):
                if qdx >= len(QUESTIONS_DATA["questions"]):
                    break
                ques.update(QUESTIONS_DATA["questions"][qdx])

            # Save to MongoDB
            USER_RESPONSES.insert_one({
                "name": name,
                "email": email,
                "questions": questions_data,
                "video_path": video_path,
                "pdf_path": pdf_path,
                "timestamp": datetime.utcnow()
            })

            # Call AI_ENGINE
            engine = AI_ENGINE(
                audio_file="",  # Modify if you plan to extract audio
                aptitude_test_json={"questions": questions_data},
                vid_file=video_path,
                pdf_file_path=pdf_path
            )
            engine.main()
            result = engine.career_path

            # Cleanup
            os.unlink(video_path)
            os.unlink(pdf_path)

            return JsonResponse({
                "submitted": True,
                "result": result
            })
    else:
        form = AptitudeTestForm()

    return render(request, 'aptitude/test_form.html', {
        "questions": Question.objects.all(),
        "form": form
    })



def dashboard_view(request):
    result = None
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.cleaned_data['video_file']
            pdf = form.cleaned_data['pdf_file']

            video_filename = f"{slugify(video.name.rsplit('.', 1)[0])}_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
            video_path = os.path.join(UPLOAD_DIR, video_filename)
            with open(video_path, 'wb+') as destination:
                for chunk in video.chunks():
                    destination.write(chunk)

            pdf_filename = f"{slugify(pdf.name.rsplit('.', 1)[0])}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
            with open(pdf_path, 'wb+') as destination:
                for chunk in pdf.chunks():
                    destination.write(chunk)

            engine = AI_ENGINE(audio_file="", aptitude_test_json={}, vid_file=video_path, pdf_file_path=pdf_path)
            engine.main()
            result = engine.career_path

            os.unlink(video_path)
            os.unlink(pdf_path)
    else:
        form = UploadForm()

    return render(request, 'aptitude/dashboard.html', {'form': form, 'result': result})