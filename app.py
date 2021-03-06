from flask import Flask, render_template
import flask
import pickle
import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import pandas as pd
import numpy as np
import praw
from textblob import TextBlob
import sys
import xgboost

app = Flask(__name__)
def Subjectivity(text):
    return TextBlob(text).sentiment.subjectivity
def Polarity(text):
    return TextBlob(text).sentiment.polarity
def word_count(text):
    wordList = re.sub("[^\w]", " ", text).split()
    return len(wordList)
def clean_message(text):
    text = re.sub(r'[^\w\s]', '', text)
    l_text = " ".join(word for word in text.lower().split() if word not in ENGLISH_STOP_WORDS)
    return l_text
     
# for sentimental analsysis
with open('senti.pkl', "rb") as f:
    senti = pickle.load(f)
    
#One hot encoding
with open('encoding.pkl', "rb") as f:
    enc = pickle.load(f)

#Model Loading
filename = 'xgb.pkl'
xgb = pickle.load(open(filename, 'rb'))


# To get information for the Reddit url
def extract_data(url):
    data = {}
    reddit = praw.Reddit(client_id='4T9G7xV5eOUCSg',
                         client_secret='FhsUszOtYyW7IM3XpD7n9FavD3EFaQ',
                         user_agent='Preet')
    sub_data = reddit.submission(url=str(url))
    data['Title'] = [str(sub_data.title)]
    data['upvote_ratio']=sub_data.upvote_ratio
    data['Gilded'] = [sub_data.gilded]
    data['word_count'] = word_count(sub_data.title)
    data['Over_18'] = [sub_data.over_18]
    data['Number_of_Comments'] = [sub_data.num_comments]
    data['Subjectivity'] = Subjectivity(sub_data.title)
    data['Polarity'] = Polarity(sub_data.title)
    scores = senti.polarity_scores(sub_data.title)
    data['Compound'] = scores['compound']
    data['neg'] = scores['neg']
    data['neu'] = scores['neu']
    data['pos'] = scores['pos']
    df = pd.DataFrame(data)
    return df

@app.route('/')
def home():
    return render_template('Index.html')

@app.route('/predict', methods=['POST'])
def predict():
    url = str(flask.request.form['url'])
    data = extract_data(url)
    Title = clean_message(data['Title'])
    
    # Converting word2vector
    df_word_token = pd.read_csv('word_token_final.csv')
    print('df_word_token loaded')
    sys.stdout.flush()
    test_title = []
    for word in Title.split():
        if word in df_word_token.columns:
            test_title.append(df_word_token[word])
    max_len = 300
    test_title = test_title + [0] * (max_len - len(test_title))
    embed_mat = np.array(pd.read_csv('embedded_final.csv', sep=' '))
    vectors = []
    for n in test_title:
        vectors.append(embedded_final[n])
    vectors = [item for sublist in vectors for item in sublist]
    arr = np.array(vectors)
    final_vector = np.mean(arr, axis=0)
    df_test_body = pd.DataFrame(np.array(final_vector)).T
    
    #one hot encoding with column names
    categories = ['Over_18']
    test_encoded = enc.transform(data[categories])
    col_names = [False, True]
    test_ohe = pd.DataFrame(test_encoded.todense(), columns=col_names)
    
    
    data.drop(["Title", 'Over_18'], axis=1, inplace=True)
    data.reset_index(inplace=True, drop=True)
    X_test = pd.concat([data, df_test_body, test_ohe], axis=1)
    
    
    #  Predict with XGBoosting Regressor
    score = xgb.predict(X_test)
    output=round(score[0],2)
    
    return render_template('Index.html', prediction_text="Predicted score for the given Reddit post is: {}".format(output))
    return render_template("Index.html")

if __name__ == "__main__":
    app.run(debug=True)
