from pymongo import MongoClient, UpdateOne
import json

CLIENT = MongoClient("mongodb://localhost:27017/")
DATABASE_CLIENT = CLIENT["CAREER_RECOMMENDATION"]

QUESTIONS_DATA = json.load(open("aptitude_test_json.json"))


def insert_questions_to_db():
    questions = QUESTIONS_DATA["questions"]
    bulk_ops = []
    for question in questions:
        bulk_ops.append(UpdateOne({"id": question["id"]}, {"$set": question}, upsert=True))
    DATABASE_CLIENT["aptitude_question"].bulk_write(bulk_ops)


if __name__ == "__main__":
    insert_questions_to_db()
