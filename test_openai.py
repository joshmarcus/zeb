import os
import sys
import traceback
from openai import OpenAI
from dotenv import load_dotenv

def test_openai_connection():
    try:
        print("Loading environment variables...")
        load_dotenv()
        
        print("\nChecking OpenAI API key...")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables")
            return False
            
        print(f"API key found: {api_key[:10]}...")
        
        print("\nInitializing OpenAI client...")
        client = OpenAI(api_key=api_key)
        
        print("\nSending test request to OpenAI API...")
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello!"}
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            print("\nResponse received from OpenAI API:")
            print(response.choices[0].message.content)
            return True
            
        except Exception as api_error:
            print("\nError making API request:")
            print(f"Error type: {type(api_error).__name__}")
            print(f"Error message: {str(api_error)}")
            print("\nFull traceback:")
            traceback.print_exc()
            return False
        
    except Exception as e:
        print("\nUnexpected error:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting OpenAI API test...")
    success = test_openai_connection()
    print(f"\nTest {'succeeded' if success else 'failed'}")
    sys.exit(0 if success else 1) 