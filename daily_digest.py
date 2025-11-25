import os
import feedparser
import trafilatura
import google.generativeai as genai
from datetime import datetime
from jinja2 import Template

# --- CONFIGURATION ---
# Add your RSS feeds here
RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://news.ycombinator.com/rss",
    # Add more...
]

# Define what you care about
USER_INTERESTS = """
I am interested in Artificial Intelligence, Python programming, Geopolitics in Europe, 
and Space exploration. I do not care about sports, celebrity gossip, or crypto.
"""

# Setup Gemini
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

def get_headlines():
    print("Fetching RSS feeds...")
    articles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]: # Limit to latest 10 per feed to save time
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get('summary', '')[:500] # Truncate summary
                })
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    return articles

def filter_articles(articles):
    print("Filtering articles with LLM...")
    # We send the list to Gemini and ask it to pick the best 5-7 URLs
    prompt = f"""
    Here is a list of news headlines:
    {articles}

    Based on these user interests: "{USER_INTERESTS}"
    
    Select the top 5 to 7 most relevant articles. 
    Return ONLY a raw JSON list of their URLs, nothing else. 
    Example: ["url1", "url2", "url3"]
    """
    
    response = model.generate_content(prompt)
    try:
        # Clean up code blocks if the LLM adds them
        text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        selected_urls = json.loads(text)
        return selected_urls
    except:
        print("Error parsing LLM selection. Fallback to first 5.")
        return [a['link'] for a in articles[:5]]

def scrape_content(urls):
    print("Scraping full content...")
    full_texts = []
    for url in urls:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        if text:
            full_texts.append(f"SOURCE URL: {url}\nCONTENT:\n{text}\n---")
    return "\n".join(full_texts)

def generate_digest(content_text):
    print("Writing the digest...")
    prompt = f"""
    You are a professional news editor. 
    Here is the full text of several articles:
    
    {content_text}

    Task:
    1. Categorize these articles by topic (e.g., Tech, Politics, Science).
    2. Write a comprehensive "Morning Briefing" article.
    3. For each story, provide a detailed summary (readable in 2 minutes).
    4. MUST include the "SOURCE URL" provided in the text as a clickable link [Read full article](url) at the end of each section.
    5. Use Markdown formatting.
    """
    response = model.generate_content(prompt)
    return response.text

def save_html(markdown_content):
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Briefing - {{ date }}</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
    </head>
    <body>
        <h1>📅 {{ date }}</h1>
        <hr>
        <div>{{ content }}</div>
    </body>
    </html>
    """
    
    # Convert Markdown to HTML (using a simple lib or just let the LLM output HTML? 
    # Let's use 'markdown' lib for safety)
    import markdown
    html_content = markdown.markdown(markdown_content)
    
    t = Template(html_template)
    final_html = t.render(date=datetime.now().strftime("%Y-%m-%d"), content=html_content)
    
    # Save to index.html so GitHub Pages serves it
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    all_articles = get_headlines()
    selected_urls = filter_articles(all_articles)
    full_content = scrape_content(selected_urls)
    digest = generate_digest(full_content)
    save_html(digest)
    print("Done! index.html generated.")