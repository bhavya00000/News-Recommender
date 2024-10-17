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

# Enable SSL verification bypass
ssl._create_default_https_context = ssl._create_unverified_context

# Download NLTK resources
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')

# Constants
API_KEY = 'kAT0mG6klj8ISIZ466thZPTBM9OInU_hgTD1ZXofFOpN39ZC'  # Replace with your API key
NEWS_APIS = [
    {'name': 'currents', 'url': 'https://api.currentsapi.services/v1/latest-news?country=in'},
    # Add more APIs here
]


# Flask app
app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect('user_interactions.db')
    c = conn.cursor()
    
    # Create the interactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            user_id TEXT,
            article_id TEXT,
            interaction TEXT,
            category TEXT
        )
    ''')
    
    # Create the user preferences table
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

# Fetch news articles from Currents API
def fetch_news(api_key):
    all_articles = []
    for api in NEWS_APIS:
        url = f"{api['url']}&apiKey={api_key}"
        response = requests.get(url)
        data = response.json()
        
        if api['name'] == 'currents':
            articles = parse_currents_api(data)
        # Add more parsers for other APIs here
        
        all_articles.extend(articles)
    
    return all_articles

def parse_currents_api(data):
    articles = []
    for article in data['news']:
        image_url = ''
        if article.get('image'):
            try:
                response = requests.head(article['image'], timeout=5)
                if response.status_code == 200:
                    image_url = article['image']
            except requests.RequestException:
                # If there's any error (timeout, connection error, etc.), we'll just use an empty string
                pass

        articles.append({
            'id': article['id'],
            'title': article['title'],
            'description': article['description'],
            'url': article['url'],
            'author': article.get('author', 'Unknown'),
            'image': image_url,
            'published': article['published'],
            'category': article['category'][0] if article['category'] else 'General',
        })
    return articles

# Preprocess text
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
    articles = fetch_news(API_KEY)
    for article in articles:
        article['preprocessed'] = preprocess_text(article['description'])

init_articles()

# Update user preferences
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

# Get user preferences
def get_user_preferences(user_id):
    conn = sqlite3.connect('user_interactions.db')
    c = conn.cursor()
    
    c.execute('SELECT category, preference FROM user_preferences WHERE user_id = ?', (user_id,))
    preferences = dict(c.fetchall())
    
    conn.close()
    return preferences

# Define category-based recommendation function
def category_based_recommendation(user_id):
    user_preferences = get_user_preferences(user_id)
    
    if not user_preferences:
        return list(range(len(articles)))  # Return all articles if user has no preferences
    
    # Score articles based on user preferences
    article_scores = []
    for i, article in enumerate(articles):
        category_score = user_preferences.get(article['category'], 0)
        article_scores.append((i, category_score))
    
    # Sort articles by score, with highest scores first
    sorted_articles = sorted(article_scores, key=lambda x: x[1], reverse=True)
    
    return [i for i, _ in sorted_articles]

@app.route('/articles', methods=['GET'])
def get_articles():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    
    # Fetch new articles if we're running out
    if end >= len(articles):
        init_articles()
    
    return jsonify(articles[start:end])

@app.route('/interact', methods=['POST'])
def interact_with_article():
    data = request.json
    user_id = data.get('user_id')
    article_id = data.get('article_id')
    interaction = data.get('interaction')  # 'like' or 'dislike'
    
    # Find the article and its category
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
    
    # Update user preferences
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
        
        # Fetch new articles if we're running out
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