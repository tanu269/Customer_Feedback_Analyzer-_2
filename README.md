# Customer Feedback Analyzer

An advanced customer feedback analyzer that scrapes online product reviews, performs sentiment analysis, and enables product comparison and temporal trend tracking.

## Running the Application

### Running in Replit

When running the application in Replit:

1. The app will automatically run on port 5000 using the workflow configuration.
2. You can access the application directly through the Replit webview.
3. No additional configuration is needed.

### Running in VS Code or Locally

If you are running the application in VS Code or on your local machine:

1. Use the included `run_local.py` script to start the application:
   ```
   python run_local.py
   ```

2. This will configure Streamlit to run on `127.0.0.1` (localhost) and port 5000.

3. Access the application in your browser at:
   ```
   http://localhost:5000
   ```
   or
   ```
   http://127.0.0.1:5000
   ```

4. **Do not** use `0.0.0.0:5000` to access the application locally - this will result in an error.

## Features

- Scrape product reviews from various e-commerce platforms
- Perform sentiment analysis on reviews
- Extract topics and key phrases from reviews
- Visualize sentiment distribution and trends over time
- Compare multiple products based on customer feedback
- Export analysis results in CSV, JSON, or Excel formats

## Required Dependencies

- beautifulsoup4
- matplotlib
- nltk
- numpy
- pandas
- plotly
- requests
- scikit-learn
- spacy
- streamlit
- trafilatura
- wordcloud
