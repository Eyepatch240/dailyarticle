import os
import json
import feedparser
import trafilatura
import google.generativeai as genai
import markdown
from datetime import datetime
from jinja2 import Template

# --- CONFIGURATION ---
RSS_FEEDS = [
    "https://news.ycombinator.com/rss",  
    "https://astralcodexten.substack.com/feed",  
    "https://aella.substack.com/feed",           
    "https://feeds.feedburner.com/marginalrevolution/feed", 
    "https://www.lesswrong.com/feed.xml?view=curated-rss", 
    "https://www.indiehackers.com/feed", 
    "https://spacenews.com/feed/",       
    "https://www.politico.eu/feed/",     
    "https://www.euractiv.com/feed/"     
]

USER_INTERESTS = """
I am looking for high-signal content. My specific interests are:

1. HARD TECH & AI: LLMs, agents, code, open-source models, and technical breakthroughs.
2. THE FUTURE: Transhumanism, longevity, biohacking, and space exploration.
3. BUSINESS: Bootstrapped startups, indie hacking, SaaS metrics, interesting VC-backed companies.
4. SOCIOLOGY & DATA: Unconventional social studies, evolutionary psychology, prediction markets, and contrarian takes on society.
5. GEOPOLITICS: Specifically European strategic autonomy, EU defense, and macro-political shifts in Europe. 

EXCLUDE: Generic gadget reviews (iPhone rumors), celebrity gossip, sports, partisan US domestic politics (unless it affects global tech), and crypto shitcoins (unless technical blockchain innovation).
"""

# --- SETUP MODELS ---
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# STRICT ADHERENCE TO REQUESTED MODELS
curator = genai.GenerativeModel('gemini-2.5-flash')
editor = genai.GenerativeModel('gemini-2.5-pro')

def get_headlines():
    print("Fetching RSS feeds...")
    articles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]: 
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get('summary', '')[:500]
                })
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    return articles

def filter_articles(articles):
    print(f"Filtering {len(articles)} articles with Gemini 2.5 Flash...")
    
    # YOUR EXACT PROMPT
    prompt = f"""
    Here is a list of news headlines:
    {json.dumps(articles)}

    Based on these user interests: "{USER_INTERESTS}"
    
    Select the TOP 13-15 most relevant and promising articles (err on the side of more, not fewer).
    Return ONLY a raw JSON list of their URLs, nothing else. 
    Example: ["url1", "url2", "url3"]
    Respond ONLY with that JSON list. No markdown formatting or commentary.
    """
    
    try:
        response = curator.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        selected_urls = json.loads(text)
        return selected_urls
    except Exception as e:
        print(f"Error parsing LLM selection ({e}). Fallback to first 8.")
        return [a['link'] for a in articles[:8]]

def scrape_content(urls):
    print("Scraping full content...")
    full_texts = []
    for url in urls:
        try:
            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded)
            if text:
                full_texts.append(f"SOURCE URL: {url}\nCONTENT:\n{text}\n---")
        except:
            pass
    return "\n".join(full_texts)

def generate_digest(content_text):
    print("Writing the digest with Gemini 2.5 Pro...")
    
    # YOUR EXACT PROMPT
    prompt = f"""
    You are a professional news editor.
    Here is the full text of several articles:
    
    {content_text}

    Task:
    1. Categorize each article by topic (e.g., Tech, Politics, Science).
    2. Write a curated, concise, and high-signal daily news digest. Use clear, readable language—avoid hype or filler.
    3. For each story, provide a substantive summary suitable for a sophisticated and time-constrained reader.
    4. At the end of each section, include the provided "SOURCE URL" as a clickable Markdown link: [Read full article](url).
    5. Use minimalist Markdown formatting—headings, short paragraph blocks, bullet points where useful. Avoid emojis, exclamation marks, and unnecessary flourishes.
    """

    response = editor.generate_content(prompt)
    return response.text

def save_html(markdown_content):
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Briefing - {{ date }}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg: #111111;
                --text: #e0e0e0;
                --text-muted: #a0a0a0;
                --link: #64b5f6;
                --border: #333333;
            }
            body {
                background: var(--bg);
                color: var(--text);
                font-family: 'Inter', sans-serif;
                max-width: 750px;
                margin: 0 auto;
                padding: 40px 20px 80px 20px;
                font-size: 18px;
                line-height: 1.7;
            }
            /* Main Title */
            h1 {
                font-size: 2.2rem;
                font-weight: 700;
                letter-spacing: -0.02em;
                margin-bottom: 0.5em;
                color: #ffffff;
                border-bottom: 1px solid var(--border);
                padding-bottom: 20px;
            }
            .date {
                font-size: 0.9rem;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 40px;
            }
            
            /* Section Headers (Tech, Politics...) */
            h2 {
                margin-top: 60px;
                margin-bottom: 20px;
                font-size: 1rem;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                color: var(--link);
                border-bottom: 1px solid var(--border);
                padding-bottom: 10px;
                display: inline-block;
            }

            /* Article Titles */
            h3 {
                font-size: 1.5rem;
                font-weight: 600;
                color: #ffffff;
                margin-top: 40px;
                margin-bottom: 15px;
                line-height: 1.3;
            }

            /* Content Typography */
            p {
                margin-bottom: 24px;
                color: #cccccc;
            }
            ul, ol {
                margin-bottom: 24px;
                padding-left: 20px;
                color: #cccccc;
            }
            li {
                margin-bottom: 10px;
            }
            strong {
                color: #ffffff;
            }
            
            /* Links */
            a {
                color: var(--link);
                text-decoration: none;
                border-bottom: 1px solid transparent;
                transition: 0.2s;
            }
            a:hover {
                border-bottom: 1px solid var(--link);
            }

            /* Code Blocks */
            pre {
                background: #1c1c1c;
                padding: 15px;
                border-radius: 6px;
                overflow-x: auto;
                border: 1px solid var(--border);
            }
            code {
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 0.9em;
            }

            /* Mobile adjustments */
            @media (max-width: 600px) {
                body { font-size: 17px; }
                h1 { font-size: 1.8rem; }
            }
        </style>
    </head>
    <body>
        <h1>Daily Briefing</h1>
        <div class="date">{{ date }}</div>
        <div>{{ content }}</div>
    </body>
    </html>
    """
    
    # Process Markdown
    html_content = markdown.markdown(markdown_content, extensions=['fenced_code', 'nl2br'])
    
    t = Template(html_template)
    final_html = t.render(date=datetime.now().strftime("%A, %B %d, %Y"), content=html_content)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)

if __name__ == "__main__":
    all_articles = get_headlines()
    if not all_articles:
        print("No articles found.")
        exit()
        
    selected_urls = filter_articles(all_articles)
    if not selected_urls:
        print("No URLs selected.")
        exit()
        
    full_content = scrape_content(selected_urls)
    digest = generate_digest(full_content)
    save_html(digest)
    print("Done! index.html generated.")
