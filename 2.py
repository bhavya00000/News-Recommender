import ssl
import nltk

# Create an unverified SSL context
ssl._create_default_https_context = ssl._create_unverified_context

# Now try downloading the resources
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('wordnet')
