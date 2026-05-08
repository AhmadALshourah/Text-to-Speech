from openai import OpenAI
from dotenv import find_dotenv, load_dotenv

_ = load_dotenv(find_dotenv())

clint = OpenAI()

with clint.audio.speech.with_streaming_response.create(
    model="tts-1",
    voice="onyx",
    input= input("write something: ")
) as respone:
    respone.stream_to_file("output.mp3")