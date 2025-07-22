import pandas as pd
import numpy as np
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation, NMF
import spacy
import logging
import re
import string
from collections import Counter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize NLTK downloads
try:
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception as e:
    logging.error(f"Error downloading NLTK data: {str(e)}")

# Initialize spaCy
try:
    nlp = spacy.load('en_core_web_sm')
except Exception as e:
    logging.error(f"Error loading spaCy model: {str(e)}")
    logging.info("Attempting to download spaCy model...")
    try:
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load('en_core_web_sm')
    except Exception as e2:
        logging.error(f"Failed to download spaCy model: {str(e2)}")
        # Fallback to a minimal NLP pipeline if spaCy fails
        class MinimalNLP:
            def __call__(self, text):
                return text
        nlp = MinimalNLP()

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

def preprocess_text(text):
    """
    Preprocess text for analysis:
    - Convert to lowercase
    - Remove punctuation
    - Remove numbers
    - Remove stopwords
    - Lemmatize words
    
    Args:
        text (str): Input text
        
    Returns:
        str: Preprocessed text
    """
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove numbers
    text = re.sub(r'\d+', '', text)
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]
    
    # Lemmatize
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    
    return ' '.join(tokens)

def analyze_sentiment(data):
    """
    Analyze sentiment of review texts.
    
    Args:
        data (pd.DataFrame): DataFrame containing review data
        
    Returns:
        pd.DataFrame: DataFrame with sentiment analysis results
    """
    if 'review_text' not in data.columns:
        logging.error("No review_text column found in data")
        return data
    
    logging.info("Performing sentiment analysis...")
    
    # Create a copy to avoid modifying the original
    result = data.copy()
    
    # Initialize sentiment columns
    result['sentiment_score'] = np.nan
    result['sentiment'] = ''
    
    # Analyze sentiment for each review
    for i, row in result.iterrows():
        if not isinstance(row['review_text'], str):
            continue
            
        # Get sentiment scores
        sentiment = sia.polarity_scores(row['review_text'])
        
        # Store compound score
        result.at[i, 'sentiment_score'] = sentiment['compound']
        
        # Determine sentiment category
        if sentiment['compound'] >= 0.05:
            result.at[i, 'sentiment'] = 'positive'
        elif sentiment['compound'] <= -0.05:
            result.at[i, 'sentiment'] = 'negative'
        else:
            result.at[i, 'sentiment'] = 'neutral'
    
    # Fill any missing values
    result['sentiment_score'] = result['sentiment_score'].fillna(0)
    result['sentiment'] = result['sentiment'].fillna('neutral')
    
    logging.info("Sentiment analysis complete")
    return result

def extract_named_entities(text):
    """
    Extract named entities from text using spaCy.
    
    Args:
        text (str): Input text
        
    Returns:
        dict: Dictionary of entity types and values
    """
    if not isinstance(text, str):
        return {}
    
    try:
        doc = nlp(text)
        entities = {}
        
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            entities[ent.label_].append(ent.text)
        
        return entities
    except Exception as e:
        logging.error(f"Error extracting entities: {str(e)}")
        return {}

def extract_topics(data, num_topics=5, method='lda'):
    """
    Extract topics from review texts.
    
    Args:
        data (pd.DataFrame): DataFrame containing review data
        num_topics (int): Number of topics to extract
        method (str): Topic modeling method ('lda' or 'nmf')
        
    Returns:
        pd.DataFrame: DataFrame with topic information
    """
    if 'review_text' not in data.columns:
        logging.error("No review_text column found in data")
        return data
    
    logging.info(f"Extracting topics using {method.upper()}...")
    
    # Create a copy to avoid modifying the original
    result = data.copy()
    
    try:
        # Preprocess the texts
        preprocessed_texts = [preprocess_text(text) for text in result['review_text']]
        
        # Remove empty strings
        valid_indices = [i for i, text in enumerate(preprocessed_texts) if text.strip()]
        valid_texts = [preprocessed_texts[i] for i in valid_indices]
        
        if len(valid_texts) == 0:
            logging.warning("No valid texts for topic modeling")
            result['topic'] = 'unknown'
            return result
        
        # Create document-term matrix
        vectorizer = CountVectorizer(max_df=0.95, min_df=2, max_features=1000)
        dtm = vectorizer.fit_transform(valid_texts)
        
        # Get feature names (words)
        feature_names = vectorizer.get_feature_names_out()
        
        # Apply topic modeling
        if method.lower() == 'nmf':
            model = NMF(n_components=num_topics, random_state=42)
        else:  # default to LDA
            model = LatentDirichletAllocation(n_components=num_topics, random_state=42)
        
        # Fit the model
        model.fit(dtm)
        
        # Get top words for each topic
        topic_words = {}
        for topic_idx, topic in enumerate(model.components_):
            top_words_idx = topic.argsort()[:-11:-1]  # Get indices of top 10 words
            top_words = [feature_names[i] for i in top_words_idx]
            topic_words[topic_idx] = ' '.join(top_words)
        
        # Transform the documents to get topic distributions
        doc_topic_dist = model.transform(dtm)
        
        # Assign the most prevalent topic to each document
        topics = doc_topic_dist.argmax(axis=1)
        
        # Initialize topic column with 'unknown'
        result['topic'] = 'unknown'
        
        # Assign topics to valid documents
        for i, doc_idx in enumerate(valid_indices):
            topic_idx = topics[i]
            result.at[doc_idx, 'topic'] = topic_words[topic_idx]
        
        # Create topic_keywords column with the keywords for each topic
        result['topic_keywords'] = result['topic'].apply(lambda x: x if x != 'unknown' else '')
        
        # Create a more descriptive topic label
        def create_topic_label(keywords):
            if not keywords:
                return 'unknown'
            words = keywords.split()[:3]  # Use first 3 words
            return ' '.join(words)
        
        result['topic'] = result['topic_keywords'].apply(create_topic_label)
        
        logging.info("Topic extraction complete")
        return result
        
    except Exception as e:
        logging.error(f"Error in topic extraction: {str(e)}")
        result['topic'] = 'unknown'
        return result

def extract_key_phrases(text):
    """
    Extract key phrases from text.
    
    Args:
        text (str): Input text
        
    Returns:
        list: List of key phrases
    """
    if not isinstance(text, str) or not text.strip():
        return []
    
    try:
        doc = nlp(text)
        
        # Extract noun phrases
        noun_phrases = []
        for chunk in doc.noun_chunks:
            noun_phrases.append(chunk.text)
        
        # Extract noun phrases with adjectives
        phrases = []
        for token in doc:
            if token.pos_ == "ADJ":
                for child in token.children:
                    if child.pos_ == "NOUN":
                        phrases.append(token.text + " " + child.text)
        
        return list(set(noun_phrases + phrases))
    except Exception as e:
        logging.error(f"Error extracting key phrases: {str(e)}")
        return []

def extract_aspects(data):
    """
    Extract product aspects and associated sentiments.
    
    Args:
        data (pd.DataFrame): DataFrame containing review data
        
    Returns:
        pd.DataFrame: DataFrame with aspect information
    """
    if 'review_text' not in data.columns:
        logging.error("No review_text column found in data")
        return data
    
    logging.info("Extracting product aspects...")
    
    # Create a copy to avoid modifying the original
    result = data.copy()
    
    try:
        # Initialize aspects column
        result['aspects'] = None
        
        for i, row in result.iterrows():
            if not isinstance(row['review_text'], str):
                continue
                
            # Process the text with spaCy
            doc = nlp(row['review_text'])
            
            aspects = {}
            
            # Extract noun phrases and associated adjectives
            for chunk in doc.noun_chunks:
                # Check if the chunk contains a noun
                has_noun = any(token.pos_ == "NOUN" for token in chunk)
                
                if has_noun:
                    # Get the chunk text and clean it
                    aspect = chunk.text.lower().strip()
                    
                    # Find adjectives that may describe this noun chunk
                    adjectives = []
                    for token in doc:
                        if token.pos_ == "ADJ" and any(child.text == chunk.root.text for child in token.children):
                            adjectives.append(token.text.lower())
                    
                    if aspect and aspect not in aspects:
                        aspects[aspect] = adjectives
            
            result.at[i, 'aspects'] = aspects if aspects else None
        
        logging.info("Aspect extraction complete")
        return result
        
    except Exception as e:
        logging.error(f"Error in aspect extraction: {str(e)}")
        return result
