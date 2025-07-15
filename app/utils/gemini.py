from google import genai
import os

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client(api_key="")

def assess_job_feasibility(job_data: dict) -> str:
    # Remove `feasibility_status` if present
    job_data.pop('feasibility_status', None)

    # Create a structured prompt
    prompt = f"""
    You are an Upwork job analyzer. Your job is to assess whether a given job post is:
    - valid (real and trustworthy),
    - scam (fraudulent or suspicious), or
    - unsure (not enough information).

    Here is the job data in JSON:
    {job_data}

    Based on the data above, respond only with one of the following:
    - valid
    - scam
    - unsure
    """

    # Call Gemini API
    try:
        
        response = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
        )
        status = response.text.strip().lower()

        # Validate output
        if status not in ['valid', 'scam', 'unsure']:
            print(status)
            return 'unsure'  # fallback if Gemini returns something unexpected
        return status
    except Exception as e:
        print("Error in Gemini call:", e)
        return 'unsure'
