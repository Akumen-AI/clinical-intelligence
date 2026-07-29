import sys
import os
import google.genai as genai
from app.config import settings

def test():
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        for model in client.models.list():
            print(model.name)
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test()
