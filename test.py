import os
openai.api_key = os.getenv("OPENAI_API_KEY") # This API KEY is not published on github as the original key due to security reasons

question = input("Ask me anything: ")

client = openai.OpenAI(api_key=openai.api_key)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": question}
    ]
)

print("AI:", response.choices[0].message.content)