from pymongo import MongoClient, UpdateOne
import json

CLIENT = MongoClient("mongodb://localhost:27017/")
APTI_QUESTIONS = CLIENT["apti_questions"]

QUESTIONS_DATA = json.load(open("aptitude_test_json.json"))

def insert_questions_to_db():
    questions = QUESTIONS_DATA["questions"]
    bulk_ops = []
    for question in questions:
        bulk_ops.append(UpdateOne({"id": question["id"]}, {"$set": question}, upsert=True))
    APTI_QUESTIONS["apti_questions"].bulk_write(bulk_ops)

if __name__ == "__main__":
    insert_questions_to_db()