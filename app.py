import os
import requests

import openai
from flask import Flask, redirect, render_template, request, url_for

from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        search = request.form["search"]
        prompt = request.form["prompt"]

        response = processPromptForYT(prompt, search)
        return redirect(url_for("index", result=response))

    result = request.args.get("result")
    return render_template("index.html", result=result)


def processPromptForYT(prompt, yt_query):
    videos = search_youtube(yt_query)
    #videos = get_video_ids_from_user('UCR68xPzQK7Etq2YfJ6Oe_2A', yt_query)

    response = ""

    for video in videos:
        video_id = video["video_id"]
        video_title = video["title"]
        success, transcript = get_transcript(video["video_id"])

        if not success:
            response += f'\nTransript for the following video is too long - {video_id}'
            continue

        gpt_prompt = prompt + "\n\n" + transcript

        success, answer = ask_gpt3(gpt_prompt, "text-davinci-003")
        if success:

            response += '\n\n' + video_title + f'\nhttps://www.youtube.com/watch?v={video_id}'
            response += '\n' + answer
    
    return response

def search_youtube(query):
    api_key = os.getenv('YOUTUBE_API_KEY')
    url = 'https://www.googleapis.com/youtube/v3/search'

    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'key': api_key,
        'videoDuration': 'short',
        'maxResults': 5,
        'publishedAfter': '2022-01-01T00:00:00Z'
    }

    response = requests.get(url, params=params)
    data = response.json()

    videos = []
    for item in data['items']:
        video = {
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'video_id': item['id']['videoId']
        }
        videos.append(video)

    return videos

## Define a function to get the video_ids from a youTuber user
def get_video_ids_from_user(user, query=None):
    api_key = os.getenv('YOUTUBE_API_KEY')
    url = 'https://www.googleapis.com/youtube/v3/search'

    params = {
        'part': 'snippet',
        'channelId': user,
        'q': query,
        'type': 'video',
        'key': api_key,
        'maxResults': 5
    }

    response = requests.get(url, params=params)
    data = response.json()

    videos = []
    for item in data['items']:
        video = {
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'video_id': item['id']['videoId']
        }
        videos.append(video)

    return videos

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        full_text = ''
        for x in transcript:
            full_text += x['text'] + ' '
        return True, full_text
    except Exception:
        return False, None

def ask_gpt3(prompt, model):
    try:
        completions = openai.Completion.create(
            engine=model,
            prompt=prompt,
            max_tokens=1024,
            n=1,
            stop=None,
            top_p=.5,
        )
        return True, completions.choices[0].text
        # Raise correct more appropraite acception
    except Exception:
        return False, None
