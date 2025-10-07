from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import pandas as pd
import json
import os
from collections import defaultdict
import glob
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS to allow requests from frontend
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",  # Local development
            "http://localhost:5000",  # Local backend
            "https://loreal-datathon.vercel.app",  # Production frontend
            "https://loreal-datathon.onrender.com",  # Production backend
            "https://*.vercel.app",  # All Vercel preview deployments
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Initialize sentence transformer for embeddings
print("Loading SentenceTransformer model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded successfully!")

# Initialize Gemini LLM
print("Initializing Google Gemini...")
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7
    )
    print("Gemini initialized successfully!")
except Exception as e:
    print(f"Failed to initialize Gemini: {e}")
    llm = None

# Load categories and create embeddings
def load_categories():
    """Load categories and create embeddings"""
    try:
        df = pd.read_csv('outputs/category.csv')
        categories = df['category'].tolist()
        
        # Create embeddings for categories
        category_embeddings = model.encode(categories)
        
        return categories, category_embeddings
    except Exception as e:
        print(f"Error loading categories: {e}")
        return [], []

# Load categories and embeddings on startup
categories_list, category_embeddings = load_categories()

# Load data on startup
def load_category_data():
    """Load category trends data"""
    try:
        df = pd.read_csv('outputs/category_trends.csv')
        return df.to_dict('records')
    except Exception as e:
        print(f"Error loading category data: {e}")
        return []

def load_keyword_trends():
    """Load keyword trend insights"""
    try:
        with open('outputs/keyword_trend_insights.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading keyword trends: {e}")
        return []

def load_csv_data():
    """Load data from all CSV files in second_layer_data"""
    data = {}
    csv_files = glob.glob('second_layer_data/*.csv')
    
    for file_path in csv_files:
        try:
            filename = os.path.basename(file_path).replace('.csv', '').replace('_', ' ')
            
            # Read a sample of the data (first 1000 rows for performance)
            df = pd.read_csv(file_path, nrows=1000)
            
            # Convert to records
            data[filename] = {
                'total_rows': len(df),
                'columns': list(df.columns),
                'sample_data': df.head(10).to_dict('records')
            }
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            data[filename] = {'error': str(e)}
    
    return data

# Load data on startup
category_data = load_category_data()
keyword_trends = load_keyword_trends()
csv_data = load_csv_data()

@app.route('/api/categories')
def get_categories():
    """Get category performance data"""
    return jsonify(category_data)

@app.route('/api/trending-keywords')
def get_trending_keywords():
    """Get trending keywords data"""
    # Extract top trending keywords across all categories
    all_keywords = []
    
    for category_info in keyword_trends:
        category = category_info.get('category', '')
        keywords = category_info.get('keywords', [])
        
        for keyword_info in keywords:
            keyword_info['category'] = category
            all_keywords.append(keyword_info)
    
    # Sort by growth rate and return top 20
    sorted_keywords = sorted(all_keywords, key=lambda x: x.get('growth_rate', 0), reverse=True)[:20]
    
    return jsonify(sorted_keywords)

@app.route('/api/metrics')
def get_metrics():
    """Get overview metrics"""
    total_keywords = sum(len(cat.get('keywords', [])) for cat in keyword_trends)
    trending_up = sum(1 for cat in keyword_trends for kw in cat.get('keywords', []) if kw.get('trend') == 'up')
    trending_down = sum(1 for cat in keyword_trends for kw in cat.get('keywords', []) if kw.get('trend') == 'down')
    
    # Get top growth rate
    top_growth = 0
    top_keyword = "N/A"
    for cat in keyword_trends:
        for kw in cat.get('keywords', []):
            if kw.get('growth_rate', 0) > top_growth:
                top_growth = kw.get('growth_rate', 0)
                top_keyword = kw.get('keyword', 'N/A')
    
    metrics = {
        'total_keywords': total_keywords,
        'trending_up': trending_up,
        'trending_down': trending_down,
        'top_growth_rate': f"{top_growth:.1f}%",
        'top_keyword': top_keyword
    }
    
    return jsonify(metrics)

@app.route('/api/category-breakdown')
def get_category_breakdown():
    """Get detailed category breakdown"""
    breakdown = []
    
    for category_data_item in category_data:
        category_name = category_data_item.get('category', '')
        
        # Find corresponding keyword trends
        category_keywords = []
        for trend_category in keyword_trends:
            if trend_category.get('category') == category_name:
                category_keywords = trend_category.get('keywords', [])
                break
        
        # Calculate growth percentage
        growth_rate = 0
        if category_keywords:
            growth_rate = sum(kw.get('growth_rate', 0) for kw in category_keywords) / len(category_keywords)
        
        # Map category name to icon
        category_icons = {
            'Makeup & Cosmetics': '💄',
            'Skincare & Anti-Aging': '🧴',
            'Hair Coloring & Transformation': '💇‍♀️',
            'Beauty Reviews & Brands': '⭐',
            'Facial Care & Exercises': '✨',
            'Hair Transformations & Makeovers': '💇',
            'Men\'s Fashion & Style': '👔',
            'General Beauty & Buzzwords': '🎯',
            'Hair Styling & Men\'s Grooming': '✂️',
            'Vlogs & Lifestyle': '📹'
        }
        
        breakdown.append({
            'name': category_name,
            'count': len(category_keywords),
            'percentage': min(100, max(0, int(category_data_item.get('engagement_rate', 0) * 1000))),  # Scale engagement rate
            'growth': f"+{growth_rate:.1f}%" if growth_rate > 0 else f"{growth_rate:.1f}%",
            'trend': 'up' if growth_rate > 0 else 'down',
            'icon': category_icons.get(category_name, '📊'),
            'viewCount': int(category_data_item.get('viewCount', 0)),
            'likeCount': int(category_data_item.get('likeCount', 0)),
            'commentCount': int(category_data_item.get('commentCount', 0)),
            'engagement_rate': float(category_data_item.get('engagement_rate', 0))
        })
    
    # Sort by percentage (engagement rate scaled)
    breakdown.sort(key=lambda x: x['percentage'], reverse=True)
    
    return jsonify(breakdown)

@app.route('/api/csv-data')
def get_csv_data():
    """Get information about all CSV files"""
    return jsonify(csv_data)

@app.route('/api/csv-data/<category>')
def get_csv_category_data(category):
    """Get data for a specific category CSV file"""
    # Convert URL category back to filename format
    filename = category.replace('-', ' ').title()
    
    if filename in csv_data:
        return jsonify(csv_data[filename])
    else:
        return jsonify({'error': 'Category not found'}), 404

@app.route('/api/keyword-trends-by-category')
def get_keyword_trends_by_category():
    """Get keyword trends organized by category"""
    return jsonify(keyword_trends)

@app.route('/api/trend-analysis')
def get_trend_analysis():
    """Get comprehensive trend analysis data for the trending page"""
    analysis_data = []
    
    # Category icons mapping
    category_icons = {
        'Beauty Reviews & Brands': '⭐',
        'General Beauty & Buzzwords': '🎯',
        'Facial Care & Exercises': '✨',
        'Hair Coloring & Transformation': '🎨',
        'Hair Styling & Men\'s Grooming': '✂️',
        'Hair Transformations & Makeovers': '💇',
        'Makeup & Cosmetics': '💄',
        'Men\'s Fashion & Style': '👔',
        'Skincare & Anti-Aging': '🧴',
        'Vlogs & Lifestyle': '📹'
    }
    
    # Calculate trend analysis for each category
    for i, category_data in enumerate(keyword_trends):
        category_name = category_data.get('category', '')
        keywords = category_data.get('keywords', [])
        
        if not keywords:
            continue
            
        # Calculate category-level metrics
        total_growth = sum(kw.get('growth_rate', 0) for kw in keywords)
        avg_growth = total_growth / len(keywords) if keywords else 0
        trending_up_count = sum(1 for kw in keywords if kw.get('trend') == 'up')
        trending_down_count = sum(1 for kw in keywords if kw.get('trend') == 'down')
        
        # Determine overall category trend
        if avg_growth > 2:
            category_trend = 'up'
        elif avg_growth < -2:
            category_trend = 'down'
        else:
            category_trend = 'stable'
        
        # Format category change percentage
        change_str = f"+{avg_growth:.1f}%" if avg_growth >= 0 else f"{avg_growth:.1f}%"
        
        # Get top keywords for this category (max 5)
        top_keywords = []
        sorted_keywords = sorted(keywords, key=lambda x: x.get('growth_rate', 0), reverse=True)[:5]
        
        for kw in sorted_keywords:
            growth_rate = kw.get('growth_rate', 0)
            trend = kw.get('trend', 'stable')
            is_hot = growth_rate > 10  # Mark as hot if growth > 10%
            
            growth_str = f"+{growth_rate:.1f}%" if growth_rate >= 0 else f"{growth_rate:.1f}%"
            
            top_keywords.append({
                'keyword': kw.get('keyword', ''),
                'growth': growth_str,
                'trend': trend,
                'isHot': is_hot
            })
        
        # Calculate rank based on average growth rate
        rank = i + 1  # This will be sorted later
        
        analysis_data.append({
            'category': category_name,
            'trend': category_trend,
            'change': change_str,
            'icon': category_icons.get(category_name, '📊'),
            'rank': rank,
            'keywords': top_keywords,
            'avg_growth': avg_growth,
            'trending_up_count': trending_up_count,
            'trending_down_count': trending_down_count
        })
    
    # Sort by average growth rate and assign proper ranks
    analysis_data.sort(key=lambda x: x['avg_growth'], reverse=True)
    for i, item in enumerate(analysis_data):
        item['rank'] = i + 1
    
    return jsonify(analysis_data)

@app.route('/api/trend-summary')
def get_trend_summary():
    """Get summary statistics for trending analysis"""
    total_categories = len(keyword_trends)
    categories_trending_up = 0
    categories_trending_down = 0
    all_growth_rates = []
    hot_keywords_count = 0
    
    for category_data in keyword_trends:
        keywords = category_data.get('keywords', [])
        if not keywords:
            continue
            
        # Calculate average growth for category
        avg_growth = sum(kw.get('growth_rate', 0) for kw in keywords) / len(keywords)
        all_growth_rates.append(avg_growth)
        
        if avg_growth > 2:
            categories_trending_up += 1
        elif avg_growth < -2:
            categories_trending_down += 1
            
        # Count hot keywords (growth > 10%)
        hot_keywords_count += sum(1 for kw in keywords if kw.get('growth_rate', 0) > 10)
    
    # Calculate overall statistics
    highest_growth = max(kw.get('growth_rate', 0) for cat in keyword_trends for kw in cat.get('keywords', []))
    avg_category_growth = sum(all_growth_rates) / len(all_growth_rates) if all_growth_rates else 0
    percentage_trending_up = (categories_trending_up / total_categories * 100) if total_categories > 0 else 0
    
    return jsonify({
        'categories_trending_up_percentage': f"{percentage_trending_up:.0f}%",
        'highest_growth': f"+{highest_growth:.1f}%",
        'hot_keywords_count': hot_keywords_count,
        'avg_category_growth': f"+{avg_category_growth:.1f}%"
    })

@app.route('/api/growth-chart')
def get_growth_chart():
    """Get data for growth chart"""
    # Generate monthly growth data based on keyword trends
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    chart_data = []
    for i, month in enumerate(months):
        # Simulate growth data based on trending keywords
        base_value = 100 + (i * 10)  # Base growth trend
        
        # Add some variation based on keyword trends
        variation = sum(kw.get('growth_rate', 0) for cat in keyword_trends for kw in cat.get('keywords', [])[:3]) / 10
        
        chart_data.append({
            'month': month,
            'keywords': max(0, int(base_value + variation + (i * 2))),
            'engagement': max(0, int(base_value * 0.8 + variation + (i * 1.5))),
            'reach': max(0, int(base_value * 1.2 + variation + (i * 3)))
        })
    
    return jsonify(chart_data)

@app.route('/api/keyword-checker', methods=['POST'])
def keyword_checker():
    """Check keyword and find matching category and trend data"""
    try:
        data = request.get_json()
        if not data or 'keyword' not in data:
            return jsonify({'error': 'Keyword is required'}), 400
            
        user_keyword = data['keyword'].strip()
        if not user_keyword:
            return jsonify({'error': 'Keyword cannot be empty'}), 400
        
        # Step 1: Find the nearest category using embeddings
        user_embedding = model.encode([user_keyword])
        
        # Calculate cosine similarity with all categories
        similarities = cosine_similarity(user_embedding, category_embeddings)[0]
        best_category_idx = np.argmax(similarities)
        best_category = categories_list[best_category_idx]
        category_similarity = float(similarities[best_category_idx])
        
        print(f"Best matching category for '{user_keyword}': {best_category} (similarity: {category_similarity:.3f})")
        
        # Step 2: Load the corresponding keyword trend phases CSV
        csv_filename = f"third_layer_data/{best_category}_keyword_trend_phases.csv"
        
        if not os.path.exists(csv_filename):
            return jsonify({
                'error': f'Data file not found for category: {best_category}',
                'category': best_category,
                'category_similarity': category_similarity
            }), 404
        
        # Load keyword data for the matched category
        keyword_df = pd.read_csv(csv_filename)
        
        if keyword_df.empty:
            return jsonify({
                'error': f'No keyword data found for category: {best_category}',
                'category': best_category,
                'category_similarity': category_similarity
            }), 404
        
        # Step 3: Find the closest keyword using embeddings
        category_keywords = keyword_df['keyword'].tolist()
        category_keyword_embeddings = model.encode(category_keywords)
        
        # Calculate cosine similarity with all keywords in the category
        keyword_similarities = cosine_similarity(user_embedding, category_keyword_embeddings)[0]
        best_keyword_idx = np.argmax(keyword_similarities)
        best_keyword_match = category_keywords[best_keyword_idx]
        keyword_similarity = float(keyword_similarities[best_keyword_idx])
        
        # Extract the trend data for the best matching keyword
        keyword_data = keyword_df.iloc[best_keyword_idx]
        
        # Get LLM analysis for future trends
        print(f"Getting LLM analysis for keyword: {user_keyword}")
        llm_analysis = analyze_keyword_with_llm(
            keyword=user_keyword,
            category=best_category,
            phase=keyword_data['phase'],
            velocity=float(keyword_data['velocity']),
            engagement_rate=float(keyword_data['engagement_rate']),
            matched_keyword=best_keyword_match
        )

        result = {
            'user_keyword': user_keyword,
            'matched_category': best_category,
            'category_similarity': round(category_similarity, 3),
            'matched_keyword': best_keyword_match,
            'keyword_similarity': round(keyword_similarity, 3),
            'phase': keyword_data['phase'],
            'velocity': float(keyword_data['velocity']),
            'engagement_rate': float(keyword_data['engagement_rate']),
            'velocity_description': f"{keyword_data['velocity']:.1f} mentions per month (past 3 months)",
            'engagement_description': f"Popularity score: {keyword_data['engagement_rate']:.3f}",
            'phase_description': get_phase_description(keyword_data['phase']),
            # Add LLM analysis
            'future_trend': llm_analysis['future_trend'],
            'insights': llm_analysis['insights'],
            'recommendations': llm_analysis['recommendations']
        }
        
        print(f"Keyword checker result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in keyword checker: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

def analyze_keyword_with_llm(keyword, category, phase, velocity, engagement_rate, matched_keyword):
    """Use Gemini to analyze keyword trends and provide insights"""
    if not llm:
        return {
            "future_trend": "AI analysis temporarily unavailable",
            "insights": ["Manual trend analysis required", "Data shows current engagement patterns"],
            "recommendations": ["Monitor velocity changes", "Track engagement trends"]
        }
    
    try:
        # Create a comprehensive prompt for trend analysis with metrics explanation
        prompt = f"""
        You are a beauty industry trend analyst for L'Oréal. Analyze the following keyword data and provide clear, actionable insights.

        KEYWORD DATA:
        - User Input: "{keyword}"
        - Best Category Match: "{category.replace('_', ' ')}"
        - Similar Keyword: "{matched_keyword}"
        - Trend Phase: {phase}
        - Velocity: {velocity:.1f} mentions/month (3-month trend)
        - Engagement Rate: {engagement_rate:.4f}

        METRICS EXPLAINED:
        - Velocity: Slope of mentions over last 3 months (positive = increasing, negative = decreasing)
        - Engagement Rate: Average user interaction score (likes + comments + shares) / views
        - Phase Classification:
          * Emerging: Rising mentions, low engagement
          * Growing: Rising mentions, high engagement  
          * Peaking: Slowing mentions, high engagement
          * Decaying: Slowing mentions, low engagement

        RESPONSE FORMAT:
        Provide exactly 3 sections with clean, professional language:

        FUTURE TREND:
        [One clear sentence about expected trend direction for next 3-6 months based on the metrics]

        KEY INSIGHTS:
        - [Business insight 1]
        - [Business insight 2]
        - [Business insight 3]

        RECOMMENDATIONS:
        - [Actionable recommendation 1]
        - [Actionable recommendation 2]
        - [Actionable recommendation 3]

        Keep language professional, avoid asterisks, and focus on practical business value for beauty brands.
        """
        
        # Get response from Gemini
        response = llm.invoke(prompt)
        analysis_text = response.content
        
        # Parse the response into structured format
        parsed_analysis = parse_llm_response_enhanced(analysis_text)
        
        return parsed_analysis
        
    except Exception as e:
        print(f"Error in LLM analysis: {e}")
        return {
            "future_trend": "Trend analysis indicates potential market evolution based on current metrics",
            "insights": [
                "Current engagement levels suggest active audience interest",
                "Velocity patterns indicate momentum changes in market attention",
                "Category positioning shows competitive landscape dynamics"
            ],
            "recommendations": [
                "Monitor weekly mention patterns for early trend detection",
                "Track competitor engagement strategies in this category",
                "Adjust content strategy based on audience engagement feedback"
            ]
        }

def parse_llm_response_enhanced(response_text):
    """Parse LLM response into structured format with improved cleaning"""
    try:
        # Clean the response text
        response_text = response_text.replace('**', '').replace('*', '')
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        future_trend = ""
        insights = []
        recommendations = []
        current_section = None
        
        for line in lines:
            line_lower = line.lower()
            
            # Identify sections
            if "future trend" in line_lower:
                current_section = "trend"
                continue
            elif "key insight" in line_lower or "insights:" in line_lower:
                current_section = "insights"
                continue
            elif "recommend" in line_lower:
                current_section = "recommendations"
                continue
                
            # Extract content based on current section
            if current_section == "trend" and not future_trend:
                if len(line) > 15 and not line.startswith('-'):  # Avoid bullet points
                    future_trend = line.strip()
                    
            elif current_section == "insights":
                if line.startswith('-'):
                    clean_insight = line[1:].strip()
                    if clean_insight and len(clean_insight) > 10:
                        insights.append(clean_insight)
                elif len(line) > 15 and len(insights) < 3 and not any(keyword in line_lower for keyword in ['insight', 'recommendation']):
                    insights.append(line.strip())
                    
            elif current_section == "recommendations":
                if line.startswith('-'):
                    clean_rec = line[1:].strip()
                    if clean_rec and len(clean_rec) > 10:
                        recommendations.append(clean_rec)
                elif len(line) > 15 and len(recommendations) < 3 and not any(keyword in line_lower for keyword in ['insight', 'recommendation']):
                    recommendations.append(line.strip())
        
        # Ensure we have quality content
        if not future_trend or "based on current metrics, expect continued trend evolution" in future_trend.lower():
            if "peaking" in str(response_text).lower():
                future_trend = "This keyword is approaching market saturation and may see declining momentum in the coming months"
            elif "growing" in str(response_text).lower():
                future_trend = "Strong upward trajectory suggests continued growth and increased market interest over the next quarter"
            elif "emerging" in str(response_text).lower():
                future_trend = "Early-stage trend with potential for significant growth as market awareness increases"
            elif "decaying" in str(response_text).lower():
                future_trend = "Downward trend indicates declining market interest and reduced content engagement"
            else:
                future_trend = "Market dynamics suggest evolving consumer interest patterns requiring strategic monitoring"
        
        # Ensure minimum quality insights
        if len(insights) < 2:
            default_insights = [
                "Current engagement metrics indicate measurable audience interaction levels",
                "Velocity patterns reveal important momentum shifts in market attention",
                "Category positioning demonstrates competitive landscape opportunities"
            ]
            insights.extend(default_insights[:3-len(insights)])
        
        # Ensure minimum quality recommendations  
        if len(recommendations) < 2:
            default_recommendations = [
                "Implement weekly monitoring of mention patterns and engagement rates",
                "Develop targeted content strategies aligned with current trend phase",
                "Analyze competitor activities within this keyword category"
            ]
            recommendations.extend(default_recommendations[:3-len(recommendations)])
            
        return {
            "future_trend": future_trend.strip(),
            "insights": insights[:3],  # Limit to 3 items
            "recommendations": recommendations[:3]  # Limit to 3 items
        }
        
    except Exception as e:
        print(f"Error parsing enhanced LLM response: {e}")
        return {
            "future_trend": "Market analysis suggests dynamic trend patterns requiring continued observation",
            "insights": [
                "Data indicates active engagement within target audience segments",
                "Velocity measurements show significant momentum characteristics",
                "Category metrics reveal competitive positioning opportunities"
            ],
            "recommendations": [
                "Establish systematic monitoring protocols for trend detection",
                "Develop adaptive content strategies based on engagement feedback", 
                "Monitor competitive landscape for strategic positioning opportunities"
            ]
        }

def get_phase_description(phase):
    """Get description for trend phase"""
    descriptions = {
        'Emerging': 'This keyword is in its early adoption phase with growing interest.',
        'Growing': 'This keyword is gaining momentum and popularity rapidly.',
        'Peaking': 'This keyword has reached its peak popularity and is widely discussed.',
        'Decaying': 'This keyword is declining in popularity and mentions.',
        'Stable': 'This keyword maintains consistent engagement over time.'
    }
    return descriptions.get(phase, f'This keyword is in the {phase} phase.')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
