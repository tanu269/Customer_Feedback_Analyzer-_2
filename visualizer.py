import pandas as pd
import numpy as np
from plotly import graph_objects as go
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from io import BytesIO
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def plot_sentiment_distribution(data):
    """
    Create a pie chart showing the distribution of sentiments.
    
    Args:
        data (pd.DataFrame): DataFrame with sentiment analysis results
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    if 'sentiment' not in data.columns:
        logging.error("No sentiment column found in data")
        return go.Figure()
    
    # Count sentiments
    sentiment_counts = data['sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['sentiment', 'count']
    
    # Set colors for sentiments
    colors = {
        'positive': '#4CAF50',  # Green
        'neutral': '#FFC107',   # Amber
        'negative': '#F44336'   # Red
    }
    
    # Create pie chart
    fig = px.pie(
        sentiment_counts, 
        values='count', 
        names='sentiment',
        title='Sentiment Distribution',
        color='sentiment',
        color_discrete_map=colors
    )
    
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(
        legend_title_text='Sentiment',
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def plot_rating_distribution(data):
    """
    Create a histogram of ratings.
    
    Args:
        data (pd.DataFrame): DataFrame with rating data
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    if 'rating' not in data.columns:
        logging.error("No rating column found in data")
        return go.Figure()
    
    # Handle non-numeric ratings
    if not pd.api.types.is_numeric_dtype(data['rating']):
        logging.error("Ratings are not numeric")
        return go.Figure()
    
    # Create histogram
    fig = px.histogram(
        data,
        x='rating',
        nbins=10,
        title='Rating Distribution',
        labels={'rating': 'Rating', 'count': 'Count'},
        color_discrete_sequence=['#1976D2']  # Blue
    )
    
    fig.update_layout(
        xaxis=dict(
            tickmode='linear',
            dtick=1
        ),
        bargap=0.1,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def plot_sentiment_over_time(data, time_unit='month'):
    """
    Create a line chart showing sentiment trends over time.
    
    Args:
        data (pd.DataFrame): DataFrame with temporal sentiment data
        time_unit (str): Time unit for aggregation ('day', 'week', 'month')
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    if 'date' not in data.columns or 'sentiment_score' not in data.columns:
        logging.error("Required columns not found in data")
        return go.Figure()
    
    # Create a copy to avoid modifying the original
    df = data.copy()
    
    # Make sure date is datetime
    if not pd.api.types.is_datetime64_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Drop rows with missing dates
    df = df.dropna(subset=['date'])
    
    if df.empty:
        logging.error("No valid dates in data")
        return go.Figure()
    
    # Group by time unit
    if time_unit == 'day':
        df['time_period'] = df['date'].dt.date
    elif time_unit == 'week':
        df['time_period'] = df['date'].dt.isocalendar().week
        df['year'] = df['date'].dt.isocalendar().year
        # Create a proper date for the start of each week
        df['time_period'] = pd.to_datetime(df['year'].astype(str) + '-W' + 
                                          df['time_period'].astype(str) + '-1', 
                                          format='%Y-W%W-%w')
    else:  # Default to month
        df['time_period'] = df['date'].dt.to_period('M').dt.to_timestamp()
    
    # Aggregate data
    grouped = df.groupby('time_period').agg({
        'sentiment_score': 'mean',
        'review_text': 'count'
    }).reset_index()
    
    grouped.columns = ['time_period', 'avg_sentiment', 'review_count']
    
    # Calculate positive percentage if sentiment column exists
    if 'sentiment' in df.columns:
        positive_counts = df[df['sentiment'] == 'positive'].groupby('time_period').size()
        total_counts = df.groupby('time_period').size()
        positive_pct = (positive_counts / total_counts * 100).fillna(0)
        
        # Join with grouped data
        positive_pct_df = positive_pct.reset_index()
        positive_pct_df.columns = ['time_period', 'positive_pct']
        grouped = pd.merge(grouped, positive_pct_df, on='time_period', how='left')
        grouped['positive_pct'] = grouped['positive_pct'].fillna(0)
    else:
        grouped['positive_pct'] = 0
    
    # Create figure with secondary Y axis
    fig = go.Figure()
    
    # Add average sentiment line
    fig.add_trace(
        go.Scatter(
            x=grouped['time_period'],
            y=grouped['avg_sentiment'],
            name='Average Sentiment',
            line=dict(color='#1976D2', width=3)  # Blue
        )
    )
    
    # Add positive percentage line
    if 'positive_pct' in grouped.columns and grouped['positive_pct'].sum() > 0:
        fig.add_trace(
            go.Scatter(
                x=grouped['time_period'],
                y=grouped['positive_pct'],
                name='Positive Percentage',
                line=dict(color='#4CAF50', width=3),  # Green
                yaxis='y2'
            )
        )
    
    # Add review count as bar chart
    fig.add_trace(
        go.Bar(
            x=grouped['time_period'],
            y=grouped['review_count'],
            name='Review Count',
            marker_color='rgba(200, 200, 200, 0.6)',
            yaxis='y3'
        )
    )
    
    # Set up layout with multiple Y axes
    fig.update_layout(
        title=f'Sentiment Trends Over Time (by {time_unit})',
        xaxis=dict(title='Time Period'),
        yaxis=dict(
            title='Average Sentiment',
            titlefont=dict(color='#1976D2'),
            tickfont=dict(color='#1976D2')
        ),
        yaxis2=dict(
            title='Positive %',
            titlefont=dict(color='#4CAF50'),
            tickfont=dict(color='#4CAF50'),
            anchor='x',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        yaxis3=dict(
            title='Review Count',
            titlefont=dict(color='#9E9E9E'),
            tickfont=dict(color='#9E9E9E'),
            anchor='free',
            overlaying='y',
            side='right',
            position=0.95
        ),
        legend=dict(x=0.01, y=0.99),
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def plot_topic_distribution(data):
    """
    Create a bar chart showing the distribution of topics.
    
    Args:
        data (pd.DataFrame): DataFrame with topic data
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    if 'topic' not in data.columns:
        logging.error("No topic column found in data")
        return go.Figure()
    
    # Count topics
    topic_counts = data['topic'].value_counts().reset_index()
    topic_counts.columns = ['topic', 'count']
    
    # Limit to top 10 topics
    if len(topic_counts) > 10:
        topic_counts = topic_counts.head(10)
    
    # Create color scale
    colorscale = px.colors.qualitative.Plotly
    
    # Create bar chart
    fig = px.bar(
        topic_counts, 
        x='count', 
        y='topic',
        title='Topic Distribution',
        labels={'count': 'Number of Reviews', 'topic': 'Topic'},
        orientation='h',
        color='topic',
        color_discrete_sequence=colorscale
    )
    
    fig.update_layout(
        showlegend=False,
        margin=dict(t=50, b=50, l=200, r=50)
    )
    
    return fig

def plot_product_comparison(comparison_data):
    """
    Create visualizations comparing products.
    
    Args:
        comparison_data (dict): Dictionary containing comparison metrics
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    if not comparison_data or 'metrics' not in comparison_data:
        logging.error("No comparison metrics found in data")
        return go.Figure()
    
    metrics = comparison_data['metrics']
    
    # Select key metrics for radar chart
    radar_metrics = metrics[['product', 'avg_sentiment', 'positive_pct', 'avg_rating']].copy()
    
    # Normalize metrics to 0-1 scale for radar chart
    for col in ['avg_sentiment', 'positive_pct', 'avg_rating']:
        if col in radar_metrics.columns:
            # Skip if column is all NaN
            if radar_metrics[col].isna().all():
                radar_metrics[col] = 0
                continue
                
            # Convert sentiment from [-1, 1] to [0, 1]
            if col == 'avg_sentiment':
                radar_metrics[col] = (radar_metrics[col] + 1) / 2
            
            # Convert percentage to 0-1
            if col == 'positive_pct':
                radar_metrics[col] = radar_metrics[col] / 100
                
            # Normalize ratings (assuming 1-5 scale)
            if col == 'avg_rating':
                radar_metrics[col] = radar_metrics[col] / 5
    
    # Create radar chart
    fig = go.Figure()
    
    # Define the categories for the radar chart
    categories = [
        'Sentiment Score',
        'Positive %',
        'Rating'
    ]
    
    # Add a trace for each product
    for _, row in radar_metrics.iterrows():
        values = [
            row['avg_sentiment'] if not pd.isna(row['avg_sentiment']) else 0,
            row['positive_pct'] if not pd.isna(row['positive_pct']) else 0,
            row['avg_rating'] if not pd.isna(row['avg_rating']) else 0
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=row['product']
        ))
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        title='Product Comparison',
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig

def create_wordcloud(data):
    """
    Create a word cloud from review texts.
    
    Args:
        data (pd.DataFrame): DataFrame with review text data
        
    Returns:
        matplotlib.figure.Figure: Matplotlib figure
    """
    if 'review_text' not in data.columns:
        logging.error("No review_text column found in data")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No review text data available', 
                horizontalalignment='center', verticalalignment='center')
        return fig
    
    # Combine all review texts
    text = ' '.join(data['review_text'].dropna().astype(str))
    
    if not text:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No review text data available', 
                horizontalalignment='center', verticalalignment='center')
        return fig
    
    # Create word cloud
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        max_words=100,
        contour_width=1,
        contour_color='steelblue'
    ).generate(text)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title('Word Cloud of Reviews')
    
    return fig

def plot_aspect_sentiments(data):
    """
    Create a visualization of product aspects and their sentiments.
    
    Args:
        data (pd.DataFrame): DataFrame with aspect data
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure
    """
    if 'aspects' not in data.columns:
        logging.error("No aspects column found in data")
        return go.Figure()
    
    # Extract aspects and their sentiments
    aspects = {}
    
    for _, row in data.iterrows():
        if not row['aspects']:
            continue
            
        for aspect, adjectives in row['aspects'].items():
            if aspect not in aspects:
                aspects[aspect] = {'count': 0, 'sentiment_sum': 0}
            
            aspects[aspect]['count'] += 1
            aspects[aspect]['sentiment_sum'] += row['sentiment_score']
    
    # Calculate average sentiment for each aspect
    aspect_sentiments = []
    for aspect, data in aspects.items():
        if data['count'] > 0:
            avg_sentiment = data['sentiment_sum'] / data['count']
            aspect_sentiments.append({
                'aspect': aspect,
                'count': data['count'],
                'avg_sentiment': avg_sentiment
            })
    
    # Convert to DataFrame
    aspect_df = pd.DataFrame(aspect_sentiments)
    
    # Sort by count and limit to top aspects
    if not aspect_df.empty:
        aspect_df = aspect_df.sort_values('count', ascending=False).head(15)
    else:
        logging.warning("No aspects found in data")
        return go.Figure()
    
    # Create a horizontal bar chart
    fig = px.bar(
        aspect_df,
        x='count',
        y='aspect',
        color='avg_sentiment',
        color_continuous_scale=['red', 'yellow', 'green'],
        range_color=[-1, 1],
        title='Product Aspects and Their Sentiments',
        labels={'count': 'Mention Count', 'aspect': 'Aspect', 'avg_sentiment': 'Sentiment'},
        orientation='h'
    )
    
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(t=50, b=50, l=200, r=50)
    )
    
    return fig
