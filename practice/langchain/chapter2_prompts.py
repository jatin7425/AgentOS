from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pprint import pprint

model = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.7)

prompt_template = ChatPromptTemplate.from_messages([                                                                                        
    ("system", "You are an elitist, snobby chef specializing in {cuisine} cuisine. You are easily offended."),                              
    ("human", "What do you think if I add {unholy_combination}?")                                                                           
])

prompt_value = prompt_template.invoke({
    "cuisine": "Italian",
    "unholy_combination": "pineapple on traditional carbonara"
})

response = model.invoke(prompt_value)

# 5. Print clean text!
pprint(response.text)