from langchain_google_genai import ChatGoogleGenerativeAI                              
from langchain_core.messages import SystemMessage, HumanMessage                        

# LangChain automatically reads GOOGLE_API_KEY from your exported variable!         
model = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.7)

messages = [
    SystemMessage(content="You are a grumpy 5-star restaurant chef."),
    HumanMessage(content="Can I put ketchup on my expensive steak?")
]

pprint("Asking the chef...\n")
response = model.invoke(messages)
pprint(response.content)