import requests
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import ssl
import sqlite3
from flask_cors import CORS
import hashlib
from datetime import datetime

# Enable SSL verification bypass
ssl._create_default_https_context = ssl._create_unverified_context

# Download NLTK resources (uncomment if not already downloaded)
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')

# Constants
NEWS_APIS = [
    {
        'name': 'newsapi',
        'url': 'https://newsapi.org/v2/top-headlines?',
        'key_param': 'apiKey',
        'key': '2bb8b3db5aa248228b5b197119330502'
    },
    {
        'name': 'gnews',
        'url': 'https://gnews.io/api/v4/search?q=example',
        'key_param': 'token',
        'key': '0fe8122323c7cd7c58ad72b1e7083a07'
    },
    # {
    #     'name': 'newsdata',
    #     'url': 'https://newsdata.io/api/1/latest?',
    #     'key_param': 'apikey',
    #     'key': 'pub_557631579157fd31fd591e8d033145dddec16'
    # },
    {
        'name': 'guardian',
        'url': 'https://content.guardianapis.com/search?',
        'key_param': 'api-key',
        'key': 'fd9c0066-0043-4b5d-b213-1e455b28fd87'
    },
    {
        'name': 'currents',
        'url': 'https://api.currentsapi.services/v1/latest-news?',
        'key_param': 'apiKey',
        'key': 'kAT0mG6klj8ISIZ466thZPTBM9OInU_hgTD1ZXofFOpN39ZC'
    }
]

# Flask app
app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect('user_interactions.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            user_id TEXT,
            article_id TEXT,
            interaction TEXT,
            category TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT,
            category TEXT,
            preference INTEGER,
            UNIQUE(user_id, category)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Helper functions
def generate_id(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()

def fetch_news():
    all_articles = []
    for api in NEWS_APIS:
        params = {api['key_param']: api['key']}
        
        if api['name'] == 'newsapi':
            params['country'] = 'in'
        elif api['name'] == 'gnews':
            params['country'] = 'in'
            params['lang'] = 'en'
        elif api['name'] == 'newsdata':
            params['country'] = 'in'
        elif api['name'] == 'guardian':
            params['q'] = 'india'
        elif api['name'] == 'currents':
            params['country'] = 'in'

        try:
            response = requests.get(api['url'], params=params)
            response.raise_for_status()
            data = response.json()
            
            if api['name'] == 'newsapi':
                articles = parse_newsapi(data)
            elif api['name'] == 'gnews':
                articles = parse_gnews(data)
            elif api['name'] == 'newsdata':
                articles = parse_newsdata(data)
            elif api['name'] == 'guardian':
                articles = parse_guardian(data)
            elif api['name'] == 'currents':
                articles = parse_currents(data)
            
            all_articles.extend(articles)
        except requests.RequestException as e:
            print(f"Error fetching data from {api['name']}: {str(e)}")
    
    return all_articles

# Parser functions
def parse_newsapi(data):
    articles = []
    for article in data.get('articles', []):
        articles.append({
            'id': generate_id(article.get('title', ''), article.get('url', '')),
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('url', ''),
            'author': article.get('author', 'Unknown'),
            'image': article.get('urlToImage', ''),
            'published': article.get('publishedAt', ''),
            'category': 'General',
            'source': 'NewsAPI'
        })
    return articles

def parse_gnews(data):
    articles = []
    for article in data.get('articles', []):
        articles.append({
            'id': generate_id(article.get('title', ''), article.get('url', '')),
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('url', ''),
            'author': article.get('source', {}).get('name', 'Unknown'),
            'image': article.get('image', ''),
            'published': article.get('publishedAt', ''),
            'category': 'General',
            'source': 'GNews'
        })
    return articles

def parse_newsdata(data):
    articles = []
    for article in data.get('results', []):
        articles.append({
            'id': generate_id(article.get('title', ''), article.get('link', '')),
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('link', ''),
            # 'author': article.get('creator', ['Unknown'])[0],
            'image': article.get('image_url', ''),
            'published': article.get('pubDate', ''),
            'category': article.get('category', ['General'])[0],
            'source': 'NewsData'
        })
    return articles

def parse_guardian(data):
    articles = []
    for article in data.get('response', {}).get('results', []):
        articles.append({
            'id': generate_id(article.get('webTitle', ''), article.get('webUrl', '')),
            'title': article.get('webTitle', ''),
            'description': article.get('fields', {}).get('trailText', ''),
            'url': article.get('webUrl', ''),
            'author': 'The Guardian',
            'image': article.get('fields', {}).get('thumbnail', ''),
            'published': article.get('webPublicationDate', ''),
            'category': article.get('sectionName', 'General'),
            'source': 'The Guardian'
        })
    return articles

def parse_currents(data):
    articles = []
    for article in data.get('news', []):
        articles.append({
            'id': article.get('id', generate_id(article.get('title', ''), article.get('url', ''))),
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('url', ''),
            'author': article.get('author', 'Unknown'),
            'image': article.get('image', ''),
            'published': article.get('published', ''),
            'category': article.get('category', ['General'])[0],
            'source': 'Currents API'
        })
    return articles

# Text preprocessing
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

def preprocess_text(text):
    if text is None:
        return ''
    words = word_tokenize(text.lower())
    words = [lemmatizer.lemmatize(word) for word in words if word.isalpha()]
    words = [word for word in words if word not in stop_words]
    return ' '.join(words)

# Global variables
articles = []

# Initialize articles
def init_articles():
    global articles
    articles = fetch_news()
    for article in articles:
        article['preprocessed'] = preprocess_text(article['description'])

init_articles()

# User preference functions
def update_user_preferences(user_id, category, interaction):
    conn = sqlite3.connect('user_interactions.db')
    c = conn.cursor()
    
    preference = 1 if interaction == 'like' else -1
    c.execute('''
        INSERT OR REPLACE INTO user_preferences (user_id, category, preference)
        VALUES (?, ?, COALESCE(
            (SELECT preference FROM user_preferences WHERE user_id = ? AND category = ?) + ?,
            ?
        ))
    ''', (user_id, category, user_id, category, preference, preference))
    
    conn.commit()
    conn.close()

def get_user_preferences(user_id):
    conn = sqlite3.connect('user_interactions.db')
    c = conn.cursor()
    
    c.execute('SELECT category, preference FROM user_preferences WHERE user_id = ?', (user_id,))
    preferences = dict(c.fetchall())
    
    conn.close()
    return preferences

# Recommendation function
def category_based_recommendation(user_id):
    user_preferences = get_user_preferences(user_id)
    
    if not user_preferences:
        return list(range(len(articles)))
    
    article_scores = []
    for i, article in enumerate(articles):
        category_score = user_preferences.get(article['category'], 0)
        article_scores.append((i, category_score))
    
    sorted_articles = sorted(article_scores, key=lambda x: x[1], reverse=True)
    
    return [i for i, _ in sorted_articles]

# Flask routes
@app.route('/articles', methods=['GET'])
def get_articles():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    
    if end >= len(articles):
        init_articles()
    
    return jsonify(articles[start:end])

@app.route('/interact', methods=['POST'])
def interact_with_article():
    data = request.json
    user_id = data.get('user_id')
    article_id = data.get('article_id')
    interaction = data.get('interaction')
    
    article = next((a for a in articles if a['id'] == article_id), None)
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    
    category = article['category']

    conn = sqlite3.connect('user_interactions.db')
    c = conn.cursor()
    c.execute('INSERT INTO interactions (user_id, article_id, interaction, category) VALUES (?, ?, ?, ?)', 
              (user_id, article_id, interaction, category))
    conn.commit()
    conn.close()
    
    update_user_preferences(user_id, category, interaction)
    
    return jsonify({'message': f'Article {interaction}d successfully!'})

@app.route('/recommend', methods=['GET'])
def recommend():
    user_id = request.args.get('user_id')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))

    try:
        recommendations = category_based_recommendation(user_id)
        start = (page - 1) * page_size
        end = start + page_size
        
        if end >= len(articles):
            init_articles()
            recommendations = category_based_recommendation(user_id)
        
        recommended_articles = [articles[i] for i in recommendations[start:end]]
        return jsonify({'recommendations': recommended_articles})
    except Exception as e:
        print("Error during recommendation:", e)
        return jsonify({'error': 'An error occurred during the recommendation process.'}), 500

if __name__ == '__main__':
    app.run(debug=True)
