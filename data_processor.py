import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_scraped_data(reviews, platform):
    """
    Process scraped review data into a consistent format.
    
    Args:
        reviews (list): List of dictionaries containing review data
        platform (str): E-commerce platform
        
    Returns:
        pd.DataFrame: Processed DataFrame with structured review data
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(reviews)
        
        # Ensure required columns exist
        required_columns = ['review_text', 'rating', 'date', 'platform']
        for col in required_columns:
            if col not in df.columns:
                if col == 'review_text':
                    df[col] = ''
                elif col == 'rating':
                    df[col] = np.nan
                elif col == 'date':
                    df[col] = None
                elif col == 'platform':
                    df[col] = platform
        
        # Clean review text
        df['review_text'] = df['review_text'].astype(str).apply(clean_text)
        
        # Remove empty reviews
        df = df[df['review_text'].str.strip() != '']
        
        # Normalize ratings to 1-5 scale if needed
        if 'rating' in df.columns:
            df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
            
            # Check if ratings are on a different scale and normalize
            max_rating = df['rating'].max()
            if max_rating and max_rating != 5:
                if max_rating == 10:  # 10-point scale
                    df['rating'] = df['rating'] / 2
                elif max_rating == 100:  # 100-point scale
                    df['rating'] = df['rating'] / 20
        
        # Ensure date column is datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        logging.info(f"Processed {len(df)} reviews from {platform}")
        return df
    
    except Exception as e:
        logging.error(f"Error processing scraped data: {str(e)}")
        # Return empty DataFrame with required columns
        return pd.DataFrame(columns=['review_text', 'rating', 'date', 'platform'])

def clean_text(text):
    """
    Clean and normalize review text.
    
    Args:
        text (str): Raw review text
        
    Returns:
        str: Cleaned text
    """
    if not isinstance(text, str):
        return ""
    
    # Replace newlines with spaces
    text = re.sub(r'\n+', ' ', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    
    # Remove non-ASCII characters (optional)
    # text = re.sub(r'[^\x00-\x7F]+', '', text)
    
    return text.strip()

def analyze_temporal_trends(data):
    """
    Analyze trends over time from review data.
    
    Args:
        data (pd.DataFrame): DataFrame containing review data with dates
        
    Returns:
        pd.DataFrame: DataFrame with temporal analysis
    """
    if 'date' not in data.columns or 'sentiment_score' not in data.columns:
        logging.error("Required columns not found in data for temporal analysis")
        return pd.DataFrame()
    
    # Create a copy to avoid modifying the original
    df = data.copy()
    
    # Ensure date is datetime
    if not pd.api.types.is_datetime64_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Drop rows with missing dates
    df = df.dropna(subset=['date'])
    
    if df.empty:
        logging.error("No valid dates in data for temporal analysis")
        return pd.DataFrame()
    
    # Sort by date
    df = df.sort_values('date')
    
    # Calculate rolling averages
    window_sizes = {
        '7d': 7,
        '30d': 30,
        '90d': 90
    }
    
    # Group by date to aggregate multiple reviews per day
    daily = df.groupby(df['date'].dt.date).agg({
        'sentiment_score': 'mean',
        'review_text': 'count'
    }).reset_index()
    
    daily.columns = ['date', 'sentiment_score', 'review_count']
    
    # Convert back to datetime
    daily['date'] = pd.to_datetime(daily['date'])
    
    # Calculate rolling averages
    for window_name, days in window_sizes.items():
        daily[f'sentiment_{window_name}'] = daily['sentiment_score'].rolling(
            window=days, min_periods=1).mean()
        daily[f'volume_{window_name}'] = daily['review_count'].rolling(
            window=days, min_periods=1).mean()
    
    # Calculate month and year for easier grouping
    daily['month'] = daily['date'].dt.to_period('M')
    daily['week'] = daily['date'].dt.isocalendar().week
    daily['year'] = daily['date'].dt.year
    
    # Aggregate by month
    monthly = daily.groupby(['year', 'month']).agg({
        'sentiment_score': 'mean',
        'review_count': 'sum'
    }).reset_index()
    
    # Convert month period to datetime for plotting
    monthly['date'] = monthly['month'].dt.to_timestamp()
    
    # Aggregate by week
    weekly = daily.groupby(['year', 'week']).agg({
        'sentiment_score': 'mean',
        'review_count': 'sum'
    }).reset_index()
    
    # Create a proper date for the start of each week
    weekly['date'] = pd.to_datetime(weekly['year'].astype(str) + '-W' + 
                                    weekly['week'].astype(str) + '-1', 
                                    format='%Y-W%W-%w')
    
    # Return detailed daily data for visualization
    result = {
        'daily': daily,
        'weekly': weekly,
        'monthly': monthly
    }
    
    return result

def prepare_comparison_data(analyzed_data, products):
    """
    Prepare data for product comparison.
    
    Args:
        analyzed_data (dict): Dictionary of DataFrames with analyzed data
        products (list): List of product names to compare
        
    Returns:
        dict: Dictionary with comparison data
    """
    if not analyzed_data or not products or len(products) < 2:
        logging.error("Insufficient data for comparison")
        return {}
    
    # Extract metrics for each product
    metrics = []
    
    for product in products:
        if product not in analyzed_data:
            logging.warning(f"Product {product} not found in analyzed data")
            continue
            
        data = analyzed_data[product]
        
        # Calculate metrics
        metrics.append({
            'product': product,
            'review_count': len(data),
            'avg_sentiment': data['sentiment_score'].mean(),
            'positive_pct': (data['sentiment'] == 'positive').mean() * 100,
            'negative_pct': (data['sentiment'] == 'negative').mean() * 100,
            'neutral_pct': (data['sentiment'] == 'neutral').mean() * 100,
            'avg_rating': data['rating'].mean() if 'rating' in data.columns else np.nan
        })
    
    # Extract topics for each product
    topics = {}
    
    for product in products:
        if product not in analyzed_data:
            continue
            
        data = analyzed_data[product]
        
        if 'topic' in data.columns:
            topic_counts = data['topic'].value_counts().head(5).to_dict()
            topics[product] = topic_counts
    
    # Combine all into a comparison result
    comparison = {
        'metrics': pd.DataFrame(metrics),
        'topics': topics
    }
    
    return comparison

def generate_insights(data):
    """
    Generate insights from analyzed data.
    
    Args:
        data (pd.DataFrame): DataFrame with analyzed review data
        
    Returns:
        dict: Dictionary of insights
    """
    insights = {}
    
    try:
        # Overall sentiment
        insights['avg_sentiment'] = data['sentiment_score'].mean()
        insights['positive_pct'] = (data['sentiment'] == 'positive').mean() * 100
        insights['negative_pct'] = (data['sentiment'] == 'negative').mean() * 100
        insights['neutral_pct'] = (data['sentiment'] == 'neutral').mean() * 100
        
        # Rating statistics if available
        if 'rating' in data.columns:
            insights['avg_rating'] = data['rating'].mean()
            insights['rating_distribution'] = data['rating'].value_counts().sort_index().to_dict()
        
        # Most common topics
        if 'topic' in data.columns:
            insights['top_topics'] = data['topic'].value_counts().head(5).to_dict()
        
        # Temporal insights if dates are available
        if 'date' in data.columns:
            # Get most recent 30 days vs previous 30 days
            now = data['date'].max()
            thirty_days_ago = now - timedelta(days=30)
            sixty_days_ago = now - timedelta(days=60)
            
            recent = data[data['date'] >= thirty_days_ago]
            previous = data[(data['date'] < thirty_days_ago) & (data['date'] >= sixty_days_ago)]
            
            if not recent.empty and not previous.empty:
                insights['recent_vs_previous'] = {
                    'sentiment_change': recent['sentiment_score'].mean() - previous['sentiment_score'].mean(),
                    'volume_change': len(recent) - len(previous),
                    'recent_avg_sentiment': recent['sentiment_score'].mean(),
                    'previous_avg_sentiment': previous['sentiment_score'].mean()
                }
                
                if 'rating' in data.columns:
                    insights['recent_vs_previous']['rating_change'] = recent['rating'].mean() - previous['rating'].mean()
                    insights['recent_vs_previous']['recent_avg_rating'] = recent['rating'].mean()
                    insights['recent_vs_previous']['previous_avg_rating'] = previous['rating'].mean()
        
        # Extract potentially notable reviews
        if not data.empty:
            # Most positive reviews
            insights['most_positive'] = data.nlargest(3, 'sentiment_score')[['review_text', 'sentiment_score']].to_dict('records')
            
            # Most negative reviews
            insights['most_negative'] = data.nsmallest(3, 'sentiment_score')[['review_text', 'sentiment_score']].to_dict('records')
            
            # Most recent reviews
            if 'date' in data.columns:
                insights['most_recent'] = data.nlargest(3, 'date')[['review_text', 'sentiment_score', 'date']].to_dict('records')
        
    except Exception as e:
        logging.error(f"Error generating insights: {str(e)}")
    
    return insights
