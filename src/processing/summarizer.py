import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

def build_prompt(articles):
    """
    Builds the single batched prompt.
    We give Gemini all articles and ask for all 7 sections in one go.
    Strict JSON output format means we can parse it reliably.
    """
    
    # Format articles as a numbered list for the prompt
    article_block = ""
    for i, a in enumerate(articles):
        article_block += f"""
[{i+1}] SOURCE: {a['source']} | CATEGORY: {a['category']}
TITLE: {a['title']}
SUMMARY: {a['summary']}
LINK: {a['link']}
---"""

    prompt = f"""You are a senior analyst writing a daily intelligence brief for a tech and finance professional.

Below are today's news articles. Analyze them and produce a structured JSON digest.

ARTICLES:
{article_block}

Produce ONLY a valid JSON object with exactly this structure. No markdown, no explanation, just JSON:

{{
  "ai_news": [
    {{
      "headline": "short punchy headline, max 10 words",
      "summary": "2-3 sentence summary of what happened",
      "why_it_matters": "1 sentence on significance to tech/finance/AI professionals",
      "source": "source name",
      "link": "url"
    }}
  ],
  "tech_news": [ same structure, 5 items ],
  "finance_news": [ same structure, 5 items ],
  "startup_funding": [
    {{
      "company": "company name",
      "amount": "$XM",
      "investor": "lead investor or investors",
      "one_liner": "what the company does",
      "link": "url"
    }}
  ],
  "stocks_to_watch": [
    {{
      "ticker": "TICKER",
      "reason": "1 sentence why it is worth watching today"
    }}
  ],
  "hiring_trends": {{
    "signal": "1-2 sentence observation about tech/AI hiring right now",
    "source": "based on which articles"
  }},
  "contrarian_insight": {{
    "take": "2-3 sentence non-obvious insight that goes against the grain of today's headlines",
    "reasoning": "why this perspective is worth considering"
  }}
}}

Rules:
- ai_news: 5 items, prioritize actual AI model/research/company news over general tech
- tech_news: 5 items, no overlap with ai_news
- finance_news: 5 items, prioritize macro/markets/policy
- startup_funding: up to 5 items, only include if actual funding news exists in articles
- stocks_to_watch: 3-5 tickers mentioned or implied by today's news
- If a section has no relevant articles, return an empty array
- All links must come from the provided articles, do not invent URLs
- The contrarian_insight should genuinely challenge the dominant narrative in today's articles
"""
    return prompt

def generate_digest(articles):
    """
    Sends the batched prompt to Gemini and parses the response as JSON.
    Returns the structured digest dict.
    """
    prompt = build_prompt(articles)
    
    print("[Summarizer] Sending to Gemini 2.5 Flash...")
    response = model.generate_content(prompt)
    
    raw = response.text.strip()
    
    # Gemini sometimes wraps JSON in markdown code fences despite instructions
    # Strip them if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        digest = json.loads(raw)
        print("[Summarizer] Digest generated successfully.")
        return digest
    except json.JSONDecodeError as e:
        print(f"[Summarizer] JSON parse failed: {e}")
        print(f"[Summarizer] Raw response:\n{raw[:500]}")
        raise