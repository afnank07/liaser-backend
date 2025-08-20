from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import openai
import google.generativeai as genai
from dotenv import load_dotenv

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

# Input schema (matches your frontend payload)
class CampaignInput(BaseModel):
    initialMessage: str
    answers: List[str]

@app.post("/api/campaign-context")
async def generate_campaign_context(data: CampaignInput):
    # Combine the input into one string
    conversation_text = f"Initial message: {data.initialMessage}\n\n"
    for i, ans in enumerate(data.answers, 1):
        conversation_text += f"Answer {i}: {ans}\n"

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
