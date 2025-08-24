from supabase_client import supabase
# from typing import Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import openai
import google.generativeai as genai
from dotenv import load_dotenv
# import sys
import asyncio
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../tg_agent')))
from tg_agent import run_telegram_agent 

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL(s) for more security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Choose your provider: "openai" or "gemini"
# PROVIDER = "openai"  
PROVIDER = "gemini" 

# --- Setup API keys ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
openai.api_key = OPENAI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)

######## --- Campaign Context Generation Logic --- #######
# Input schema (matches your frontend payload)
class CampaignInput(BaseModel):
    initialMessage: str
    qaPairs: List[dict]

@app.post("/api/campaign-context")
async def generate_campaign_context(data: CampaignInput):
    # Combine the input into one string
    conversation_text = f"Initial message: {data.initialMessage}\n\n"
    for i, qa in enumerate(data.qaPairs, 1):
        question = qa.get('question', f'Question {i}')
        answer = qa.get('answer', '')
        conversation_text += f"Q{i}: {question}\nA{i}: {answer}\n"

    prompt = f"""
    You are a marketing strategist AI. 
    Based on the following inputs, summarize the user's campaign context in a concise way:

    {conversation_text}

    Provide a clear summary that highlights the target audience, their problem, budget, and preferred channels.
    """

    try:
        if PROVIDER == "openai":
            # OpenAI GPT call
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-4o", "gpt-3.5-turbo"
                messages=[
                    {"role": "system", "content": "You are a helpful marketing strategist."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
            )
            final_context = response.choices[0].message.content.strip()

        elif PROVIDER == "gemini":
            # Gemini call
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            final_context = response.text.strip()
        # if PROVIDER:
        #     final_context = "No context generated. Please check the input data."
        else:
            final_context = "Error: Unknown provider selected."

    except Exception as e:
        final_context = f"Error while generating context: {str(e)}"

    return {"finalContext": final_context}

########## --- Campaign Launch Logic --- ##########
# Input schema (matches your frontend payload)
class LaunchCampaignInput(BaseModel):
    summary: str

# Simple matching logic 
def match_users_with_summary(summary: str) -> list[dict]:
    # Example: match users by domain, role, or keywords in summary
    # You should adjust this logic to your schema and matching strategy
    # For demo, we fetch all users and filter by keyword in summary
    response = supabase.table("PotentialLeads").select("*").execute()
    # print(f"Supabase response: {response.data}")
    users = response.data if hasattr(response, 'data') else response
    matched = []
    summary_lower = summary.lower()
    for user in users:
        # Example: match if any keyword in summary is in user's domain or role
        domain = user.get("domain", "").lower()
        role = user.get("role", "").lower()

        if domain and domain in summary_lower:
            matched.append(user)
        elif role and role in summary_lower:
            matched.append(user)
    return matched

@app.post("/api/launch-campaign")
async def launch_campaign(data: LaunchCampaignInput):
    summary = data.summary
    matched_users = match_users_with_summary(summary)
    # You can format the campaigns as needed for frontend
    campaigns = [
        {
            "id": str(user.get("id", "")),
            "target": {
                "username": user.get("username", ""),
                "avatar": user.get("avatar", "U"),
                "domain": user.get("domain", ""),
                "role": user.get("role", ""),
                "tg_id": user.get("tg_id", ""),
                "per_desc": user.get("person_description", ""),
            },
            "status": "contacting",
            "lastInteraction": "just now"
        }
        for user in matched_users
    ]

        # Call run_telegram_agent for each matched user (fire and forget)
    for user in matched_users:
        tg_id = user.get("tg_id", "")
        if tg_id:
            product_summary = data.summary
            target_description = user.get("person_description", "")
            # asyncio.create_task(run_telegram_agent(product_summary, target_description, tg_id))
            run_telegram_agent(product_summary, target_description, tg_id)
        break

    return {"campaigns": campaigns}