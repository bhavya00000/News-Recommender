import streamlit as st
import requests
import time
import hashlib

# Function to create a unique key for each article
def create_unique_key(article, prefix):
    unique_string = f"{article['title']}_{article['id']}"
    return f"{prefix}_{hashlib.md5(unique_string.encode()).hexdigest()}"

# Streamlit app
st.title("Personalized News Recommendation System")

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = []
if 'displayed_article_ids' not in st.session_state:
    st.session_state.displayed_article_ids = set()

# User Input
user_id = st.text_input("Enter your user ID:")
if user_id:
    st.session_state.user_id = user_id

# Function to fetch recommendations
def fetch_recommendations():
    try:
        response = requests.get(f'http://127.0.0.1:5000/recommend?user_id={st.session_state.user_id}&page={st.session_state.page}&page_size=10')
        if response.status_code == 200:
            new_recommendations = response.json().get('recommendations', [])
            # Filter out articles that have already been displayed
            new_recommendations = [article for article in new_recommendations if article['id'] not in st.session_state.displayed_article_ids]
            st.session_state.recommendations.extend(new_recommendations)
            # Update the set of displayed article IDs
            st.session_state.displayed_article_ids.update(article['id'] for article in new_recommendations)
        else:
            st.error(f"Error fetching recommendations. Status code: {response.status_code}")
    except requests.RequestException as e:
        st.error(f"Error connecting to the recommendation server: {str(e)}")

# Function to load more articles
def load_more_articles():
    st.session_state.page += 1
    fetch_recommendations()

# Fetch initial recommendations or default articles
if st.session_state.user_id and not st.session_state.recommendations:
    fetch_recommendations()
elif not st.session_state.recommendations:
    # Fetch default articles if user is not logged in
    try:
        response = requests.get('http://127.0.0.1:5000/articles?page=1&page_size=10')
        if response.status_code == 200:
            st.session_state.recommendations = response.json()
        else:
            st.error(f"Error fetching default articles. Status code: {response.status_code}")
    except requests.RequestException as e:
        st.error(f"Error connecting to the server: {str(e)}")

# Display Articles
st.subheader("Recommended Articles" if st.session_state.user_id else "Latest News")
for index, article in enumerate(st.session_state.recommendations):
    with st.expander(f"**{article['title']}**"):
        st.write(f"**Source:** {article.get('author', 'Unknown')}")
        st.write(f"**Category:** {article.get('category', 'N/A')}")
        st.write(f"**Description:** {article['description']}")
        if article.get('image'):
            try:
                st.image(article['image'], use_column_width=True)
            except Exception as e:
                st.warning(f"Unable to load image for this article: {str(e)}")
        
        if st.session_state.user_id:
            col1, col2 = st.columns(2)
            with col1:
                like_key = create_unique_key(article, f"like_{index}")
                if st.button(f"👍 Like", key=like_key):
                    try:
                        response = requests.post('http://127.0.0.1:5000/interact', 
                                                 json={'user_id': st.session_state.user_id, 
                                                       'article_id': article['id'], 
                                                       'interaction': 'like'})
                        if response.status_code == 200:
                            st.success(f"You liked '{article['title']}'!")
                        else:
                            st.error(f"Error liking the article. Status code: {response.status_code}")
                    except requests.RequestException as e:
                        st.error(f"Error connecting to the server: {str(e)}")
            with col2:
                dislike_key = create_unique_key(article, f"dislike_{index}")
                if st.button(f"👎 Dislike", key=dislike_key):
                    try:
                        response = requests.post('http://127.0.0.1:5000/interact', 
                                                 json={'user_id': st.session_state.user_id, 
                                                       'article_id': article['id'], 
                                                       'interaction': 'dislike'})
                        if response.status_code == 200:
                            st.success(f"You disliked '{article['title']}'!")
                        else:
                            st.error(f"Error disliking the article. Status code: {response.status_code}")
                    except requests.RequestException as e:
                        st.error(f"Error connecting to the server: {str(e)}")
        
        st.markdown(f"[Read full article]({article['url']})")

# Load more button
if st.button('Load More Articles'):
    load_more_articles()

# Auto-refresh
if st.checkbox('Enable auto-refresh'):
    st.write('Auto-refreshing every 5 minutes...')
    time.sleep(300)
    st.experimental_rerun()