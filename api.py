# import torch
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from fastapi import FastAPI, Query, Body, Request,HTTPException
import pandas as pd
import requests
# import joblib
# import pickle
from fastapi.middleware.cors import CORSMiddleware
# import time,os,sys
import scrapy.crawler as crawler
from scrapy.utils.log import configure_logging
from multiprocessing import Process, Queue
from twisted.internet import reactor
import mysql.connector
from starlette.responses import RedirectResponse
# from transformers import AutoTokenizer, AutoModelForSequenceClassification
# tokenizer = AutoTokenizer.from_pretrained("hassan4830/xlm-roberta-base-finetuned-urdu")
# model = AutoModelForSequenceClassification.from_pretrained("hassan4830/xlm-roberta-base-finetuned-urdu")
# from transformers import TextClassificationPipeline
# pipe = TextClassificationPipeline(model=model, tokenizer=tokenizer, return_all_scores=True)
# from transformers import pipeline as pipe
import threading



api_key = "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"
API_URL = "https://api-inference.huggingface.co/models/hassan4830/xlm-roberta-base-finetuned-urdu"
headers = {"Authorization": f"Bearer {api_key}"}

app = FastAPI()


origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:80",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database = mysql.connector.connect(
    # CLEARDB_DATABASE_URL="mysql://bfbcd75e35b3e7:6723b52d@us-cdbr-east-06.cleardb.net/heroku_dad179f033fe9f3?reconnect=true",
    host="us-cdbr-east-06.cleardb.net",
    user="bfbcd75e35b3e7",
    password="6723b52d",
    database="heroku_dad179f033fe9f3"
)


# with open('models/new_classi.pkl', 'rb') as f:
#     loaded_model = joblib.load(f)
    
# vectorizer = pickle.load(open('models/C2vector.pkl', 'rb'))

@app.get("/")
def read_root():
    # return {"Assalam o Alikum! Syed": "API is Working Fine"}
    response = RedirectResponse(url='/docs')
    return response

def f(q,spider):
    try:
        settings = get_project_settings()
        runner = crawler.CrawlerRunner(settings)
        deferred = runner.crawl(spider)
        deferred.addBoth(lambda _: reactor.stop())
        reactor.run()
        q.put(None)
    except Exception as e:
        q.put(e)

def run_spider(spider):
    q = Queue()
    p = Process(target=f, args=(q,spider))
    p.start()
    result = q.get()
    p.join()

    if result is not None:
        raise result
    else:
        return True


@app.get("/scraper/{channel}")
async def scrapper(channel:str):
    run_spider(channel)

    scrapped_data = pd.read_csv(f"{channel}.csv")
    scrapped_data = scrapped_data.fillna(' ')
    return scrapped_data


@app.get("/classify/{channel}")
async def perform_sentiment_analysis(channel:str):
    sid_obj = SentimentIntensityAnalyzer()
    sentiments = []
    scrapped_data = pd.read_csv(f"{channel}.csv")
    details = scrapped_data['Details']

    for detail in details:
        sentiment_dict = sid_obj.polarity_scores(detail)
        negative = sentiment_dict['neg']
        neutral = sentiment_dict['neu']
        positive = sentiment_dict['pos']
        compound = sentiment_dict['compound']

        if sentiment_dict['compound'] >= 0.05:
            overall_sentiment = "Positive"

        elif sentiment_dict['compound'] <= - 0.05:
            overall_sentiment = "Negative"

        else:
            overall_sentiment = "Neutral"
        sentiments.append(overall_sentiment)

    return  sentiments


@app.get("/classify-urdu/{channel}")
async def perform_urdu_sentiment_analysis(channel:str):
    sentiments = []
    scrapped_data = pd.read_csv(f"{channel}.csv")
    details = scrapped_data['Details']

    for detail in details:
        output = query({
            "inputs": f"{detail}",
        })
        sentiments.append(output)

    insert_urdu_into_db(channel, details, sentiments)
    response = RedirectResponse(url='https://sheltered-beyond-10396.herokuapp.com/user/charts')
    return response


def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    response = response.json()
    identified_label = str(response[0][0].values())
    if 'LABEL_0' in identified_label :
        return "negative"
    else:
        return "positive"


# @app.get("/get-results-urdu/{channel}")
# async def get_results_urdu(channel:str):
#     run_spider(channel)
#     scrapped_data = pd.read_csv(f"{channel}.csv")
#     scrapped_data = scrapped_data.fillna(' ')
#     sentiments = []
#     details = scrapped_data['Details']

#     for detail in details:
#         output = pipe(detail)
#         identified_label = output[0][0].values()
#         if output[0][0]["score"] > output[0][1]["score"]:
#             sentiment =  "negative"
#         else:
#             sentiment =  "positive"
#         sentiments.append(sentiment)
        

#     insert_urdu_into_db(channel, details, sentiments)
#     response = RedirectResponse(url='https://sheltered-beyond-10396.herokuapp.com/user/charts')
#     return response


@app.get("/get-results-english/{channel}")
async def get_results_english(channel:str):
    try:
        run_spider(channel)
    except:
        threading.Thread(target=run_spider, args=(channel,)).start()
    scrapped_data = pd.read_csv(f"{channel}.csv")
    scrapped_data = scrapped_data.fillna(' ')

    sid_obj = SentimentIntensityAnalyzer()
    sentiments = []
    details = scrapped_data['Details']

    for detail in details:
        sentiment_dict = sid_obj.polarity_scores(detail)
        if sentiment_dict['compound'] >= 0.05:
            overall_sentiment = "Positive"

        elif sentiment_dict['compound'] <= - 0.05:
            overall_sentiment = "Negative"

        else:
            overall_sentiment = "Neutral"
        sentiments.append(overall_sentiment)

    insert_into_db(channel,details,sentiments)
    response = RedirectResponse(url='https://sheltered-beyond-10396.herokuapp.com/user/charts')
    return response

# @app.get("/v2/get-results-english/{channel}")
# async def get_results_english(channel:str):
#     run_spider(channel)
#     scrapped_data = pd.read_csv(f"{channel}.csv")
#     scrapped_data = scrapped_data.fillna(' ')

#     sentiments = []
#     details = scrapped_data['Details']
#     detail = vectorizer.transform(details)
#     vectorized_item = detail.toarray()
#     prediction = loaded_model.predict(vectorized_item)

#     for item in prediction:
#         if item > 0:
#             overall_sentiment = "Positive"

#         elif item < 0:
#             overall_sentiment = "Negative"

#         else:
#             overall_sentiment = "Neutral"
#         sentiments.append(overall_sentiment)

#     insert_into_db(channel,details,sentiments)
#     response = RedirectResponse(url='https://sheltered-beyond-10396.herokuapp.com/user/charts')
#     return response 


def insert_into_db(channel, scrapped_data, sentiments):
    database.reconnect()
    db_cursor = database.cursor()

    sql = "INSERT INTO sentiment_results (channel, scraped_data, sentiments) VALUES (%s, %s, %s)"

    for index,news in enumerate(sentiments):
        val = [channel, scrapped_data.values[index], news]
        db_cursor.execute(sql, val)

    database.commit()
    
def insert_urdu_into_db(channel, scrapped_data, sentiments):
    database.reconnect()
    db_cursor = database.cursor()

    sql = "INSERT INTO sentiment_results_urdus (channel, scraped_data, sentiments) VALUES (%s, %s, %s)"

    for index,news in enumerate(sentiments):
        val = [channel, scrapped_data.values[index], news]
        db_cursor.execute(sql, val)

    database.commit()
