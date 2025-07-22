import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import os
import re
import json
from io import BytesIO

from scraper import scrape_product_reviews, supported_platforms
from analyzer import analyze_sentiment, extract_topics
from visualizer import (
    plot_sentiment_distribution, 
    plot_sentiment_over_time, 
    plot_topic_distribution,
    plot_rating_distribution,
    plot_product_comparison,
    create_wordcloud
)
from data_processor import (
    process_scraped_data, 
    analyze_temporal_trends,
    prepare_comparison_data
)
from utils import validate_url, extract_product_id

# Page configuration
st.set_page_config(
    page_title="Customer Feedback Analyzer",
    page_icon="📊",
    layout="wide"
)

# Initialize session state variables
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = {}
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = {}
if 'comparison_products' not in st.session_state:
    st.session_state.comparison_products = []
if 'temporal_data' not in st.session_state:
    st.session_state.temporal_data = {}

# Title and introduction
st.title("📊 Customer Feedback Analyzer")
st.markdown("""
This application helps you analyze customer feedback and reviews for products.
Enter product URLs to scrape reviews, perform sentiment analysis, and track changes over time.
""")

# Sidebar
with st.sidebar:
    st.header("Options")
    
    # URL Input
    st.subheader("Add Product for Analysis")
    platform = st.selectbox("Select Platform", supported_platforms)
    product_url = st.text_input("Product URL", "")
    product_name = st.text_input("Product Name (Optional)", "")
    max_reviews = st.slider("Maximum Reviews to Scrape", 10, 1000, 100)
    
    scrape_button = st.button("Scrape & Analyze")
    
    # Product Comparison
    st.subheader("Product Comparison")
    if st.session_state.analyzed_data:
        products_to_compare = st.multiselect(
            "Select Products to Compare",
            options=list(st.session_state.analyzed_data.keys())
        )
        if st.button("Compare Selected Products"):
            st.session_state.comparison_products = products_to_compare
    
    # Export Options
    st.subheader("Export Data")
    if st.session_state.analyzed_data:
        export_format = st.selectbox("Export Format", ["CSV", "JSON", "Excel"])
        export_product = st.selectbox(
            "Select Product to Export", 
            options=list(st.session_state.analyzed_data.keys())
        )
        
        if st.button("Export Data"):
            if export_product in st.session_state.analyzed_data:
                df = st.session_state.analyzed_data[export_product]
                if export_format == "CSV":
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{export_product}_analysis.csv",
                        mime="text/csv"
                    )
                elif export_format == "JSON":
                    json_str = df.to_json(orient="records")
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"{export_product}_analysis.json",
                        mime="application/json"
                    )
                elif export_format == "Excel":
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='Analysis', index=False)
                    excel_data = output.getvalue()
                    st.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name=f"{export_product}_analysis.xlsx",
                        mime="application/vnd.ms-excel"
                    )

# Main content
if scrape_button:
    if not validate_url(product_url):
        st.error("Please enter a valid URL for the selected platform.")
    else:
        with st.spinner(f"Scraping reviews from {platform}..."):
            # Use product name if provided, otherwise extract from URL
            if not product_name:
                product_name = extract_product_id(product_url)
            
            # Scrape reviews
            reviews = scrape_product_reviews(product_url, platform, max_reviews)
            
            if reviews:
                st.session_state.scraped_data[product_name] = reviews
                
                # Process and analyze the data
                with st.spinner("Processing and analyzing reviews..."):
                    processed_data = process_scraped_data(reviews, platform)
                    
                    # Analyze sentiment
                    processed_data = analyze_sentiment(processed_data)
                    
                    # Extract topics
                    processed_data = extract_topics(processed_data)
                    
                    # Store analyzed data
                    st.session_state.analyzed_data[product_name] = processed_data
                    
                    # Analyze temporal trends if there are dates in the data
                    if 'date' in processed_data.columns:
                        st.session_state.temporal_data[product_name] = analyze_temporal_trends(processed_data)
                    
                st.success(f"Successfully scraped and analyzed {len(reviews)} reviews for {product_name}")
            else:
                st.error(f"Failed to scrape reviews from {platform}. Please check the URL and try again.")

# Display analysis if data is available
if st.session_state.analyzed_data:
    # Create tabs for different analysis views
    tabs = st.tabs(["Single Product Analysis", "Product Comparison", "Temporal Analysis", "Raw Data"])
    
    # Single Product Analysis Tab
    with tabs[0]:
        st.header("Single Product Analysis")
        
        # Select product to analyze
        product_to_analyze = st.selectbox(
            "Select Product", 
            options=list(st.session_state.analyzed_data.keys())
        )
        
        if product_to_analyze:
            data = st.session_state.analyzed_data[product_to_analyze]
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_sentiment = data['sentiment_score'].mean()
                st.metric("Average Sentiment", f"{avg_sentiment:.2f}")
            with col2:
                avg_rating = data['rating'].mean() if 'rating' in data.columns else None
                if avg_rating:
                    st.metric("Average Rating", f"{avg_rating:.1f}")
            with col3:
                positive_pct = (data['sentiment'] == 'positive').mean() * 100
                st.metric("Positive Reviews", f"{positive_pct:.1f}%")
            with col4:
                negative_pct = (data['sentiment'] == 'negative').mean() * 100
                st.metric("Negative Reviews", f"{negative_pct:.1f}%")
            
            # Date filter if temporal data is available
            filtered_data = data.copy()  # Default to all data
            if 'date' in data.columns:
                # Convert pandas Timestamp to Python datetime objects to avoid KeyError
                min_date = data['date'].min()
                max_date = data['date'].max()
                if pd.notna(min_date) and pd.notna(max_date):
                    min_date = min_date.to_pydatetime()
                    max_date = max_date.to_pydatetime()
                    date_range = st.slider(
                        "Select Date Range",
                        min_value=min_date,
                        max_value=max_date,
                        value=(min_date, max_date)
                    )
                    # Apply date filter
                    filtered_data = data[(data['date'] >= date_range[0]) & (data['date'] <= date_range[1])]
            
            # Visualizations
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Sentiment Distribution")
                fig = plot_sentiment_distribution(filtered_data)
                st.plotly_chart(fig, use_container_width=True)
                
                if 'rating' in filtered_data.columns:
                    st.subheader("Rating Distribution")
                    fig = plot_rating_distribution(filtered_data)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Topic Distribution")
                fig = plot_topic_distribution(filtered_data)
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Word Cloud")
                fig = create_wordcloud(filtered_data)
                st.pyplot(fig)
            
            # Show sample reviews
            st.subheader("Sample Reviews")
            sample_size = min(5, len(filtered_data))
            for _, row in filtered_data.sample(sample_size).iterrows():
                with st.expander(f"{row['sentiment']} review ({row['sentiment_score']:.2f})"):
                    st.write(row['review_text'])
                    if 'rating' in row:
                        st.write(f"Rating: {row['rating']}")
                    if 'date' in row:
                        st.write(f"Date: {row['date']}")
    
    # Product Comparison Tab
    with tabs[1]:
        st.header("Product Comparison")
        
        if len(st.session_state.comparison_products) < 2:
            st.info("Please select at least two products to compare in the sidebar.")
        else:
            comparison_data = prepare_comparison_data(
                st.session_state.analyzed_data,
                st.session_state.comparison_products
            )
            
            # Display comparison metrics
            st.subheader("Comparison Metrics")
            comparison_metrics = comparison_data['metrics']
            st.dataframe(comparison_metrics)
            
            # Visualization
            st.subheader("Sentiment Comparison")
            fig = plot_product_comparison(comparison_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Topic comparison
            st.subheader("Top Topics by Product")
            topic_cols = st.columns(len(st.session_state.comparison_products))
            for i, product in enumerate(st.session_state.comparison_products):
                with topic_cols[i]:
                    st.write(f"**{product}**")
                    if product in comparison_data['topics']:
                        for topic, count in comparison_data['topics'][product].items():
                            st.write(f"- {topic}: {count}")
    
    # Temporal Analysis Tab
    with tabs[2]:
        st.header("Temporal Analysis")
        
        products_with_dates = [p for p in st.session_state.analyzed_data.keys() 
                            if 'date' in st.session_state.analyzed_data[p].columns]
        
        if not products_with_dates:
            st.info("No products have temporal data available. Scrape products with dated reviews.")
        else:
            # Select product for temporal analysis
            temporal_product = st.selectbox(
                "Select Product for Temporal Analysis",
                options=products_with_dates
            )
            
            if temporal_product in st.session_state.temporal_data:
                temporal_data = st.session_state.temporal_data[temporal_product]
                
                # Time aggregation
                time_unit = st.selectbox(
                    "Time Aggregation",
                    options=["Day", "Week", "Month"]
                )
                
                # Plot sentiment over time
                st.subheader("Sentiment Trends Over Time")
                fig = plot_sentiment_over_time(temporal_data, time_unit.lower())
                st.plotly_chart(fig, use_container_width=True)
                
                # Display trends insights
                st.subheader("Trend Insights")
                trend_period = st.selectbox(
                    "Analysis Period",
                    options=["Last 30 days", "Last 90 days", "All time"]
                )
                
                # Calculate trend insights based on the selected period
                if temporal_product in st.session_state.analyzed_data:
                    data = st.session_state.analyzed_data[temporal_product]
                    if 'date' in data.columns:
                        if trend_period == "Last 30 days":
                            cutoff_date = datetime.now() - timedelta(days=30)
                            recent_data = data[data['date'] >= cutoff_date]
                            older_data = data[(data['date'] < cutoff_date) & 
                                            (data['date'] >= cutoff_date - timedelta(days=30))]
                        elif trend_period == "Last 90 days":
                            cutoff_date = datetime.now() - timedelta(days=90)
                            recent_data = data[data['date'] >= cutoff_date]
                            older_data = data[(data['date'] < cutoff_date) & 
                                            (data['date'] >= cutoff_date - timedelta(days=90))]
                        else:
                            median_date = data['date'].median()
                            recent_data = data[data['date'] >= median_date]
                            older_data = data[data['date'] < median_date]
                        
                        if not older_data.empty and not recent_data.empty:
                            recent_sentiment = recent_data['sentiment_score'].mean()
                            old_sentiment = older_data['sentiment_score'].mean()
                            sentiment_change = recent_sentiment - old_sentiment
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(
                                    "Recent Sentiment Score", 
                                    f"{recent_sentiment:.2f}",
                                    f"{sentiment_change:.2f}"
                                )
                            with col2:
                                if 'rating' in data.columns:
                                    recent_rating = recent_data['rating'].mean()
                                    old_rating = older_data['rating'].mean()
                                    rating_change = recent_rating - old_rating
                                    st.metric(
                                        "Recent Average Rating", 
                                        f"{recent_rating:.1f}",
                                        f"{rating_change:.1f}"
                                    )
                            
                            # Topic changes
                            st.subheader("Topic Changes")
                            recent_topics = recent_data['topic'].value_counts().head(5)
                            old_topics = older_data['topic'].value_counts().head(5)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write("Recent Top Topics")
                                for topic, count in recent_topics.items():
                                    st.write(f"- {topic}: {count}")
                            with col2:
                                st.write("Previous Top Topics")
                                for topic, count in old_topics.items():
                                    st.write(f"- {topic}: {count}")
    
    # Raw Data Tab
    with tabs[3]:
        st.header("Raw Data")
        
        product = st.selectbox(
            "Select Product", 
            options=list(st.session_state.analyzed_data.keys()),
            key="raw_data_product"
        )
        
        if product in st.session_state.analyzed_data:
            data = st.session_state.analyzed_data[product]
            st.dataframe(data)
            
            # Filter options
            st.subheader("Filter Data")
            col1, col2 = st.columns(2)
            with col1:
                sentiment_filter = st.multiselect(
                    "Filter by Sentiment",
                    options=data['sentiment'].unique(),
                    default=data['sentiment'].unique()
                )
            
            # Initialize topic_filter with default value
            topic_filter = None
            with col2:
                if 'topic' in data.columns:
                    topic_filter = st.multiselect(
                        "Filter by Topic",
                        options=data['topic'].unique(),
                        default=data['topic'].unique()
                    )
            
            # Apply filters
            filtered = data[data['sentiment'].isin(sentiment_filter)]
            if 'topic' in data.columns and topic_filter is not None:
                filtered = filtered[filtered['topic'].isin(topic_filter)]
            
            st.dataframe(filtered)
else:
    st.info("Enter a product URL in the sidebar to start the analysis process.")
