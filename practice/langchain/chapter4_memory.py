from pprint import pprint
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

model = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.7)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an encouraging and thoughtful personal coach. You communicate in a warm, grounded, and supportive tone to help with daily goals and focus."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])
                                                                                                                                       
# 3. Base Chain                                                                                                                             
base_chain = prompt | model | StrOutputParser()                                                                                             
                                                                                                                                            
# 4. Storage for chat histories (a simple in-memory dictionary)                                                                             
# In production, this could be Redis, SQLite, or Postgres!                                                                                  
store = {}                                                                                                                                  
                                                                                                                                            
def get_session_history(session_id: str):                                                                                                   
    """Retrieve or create the notebook for a specific user session."""                                                                      
    if session_id not in store:                                                                                                             
        store[session_id] = InMemoryChatMessageHistory()                                                                                    
    return store[session_id]
                                                                                
                                                                                                                                            
# 5. Wrap our chain with Memory!                                                                                                            
chain_with_memory = RunnableWithMessageHistory(                                                                                             
    base_chain,                                                                                                                             
    get_session_history,                                                                                                                    
    input_messages_key="input",                                                                                                             
    history_messages_key="history"                                                                                                          
)

config = {"configurable": {"session_id": "session_user_jatin"}}

def print_stream_message(user_input):
    for chunk in chain_with_memory.stream(
        {"input": user_input},
        config=config
    ):
        print(chunk, end="", flush=True)
    print()    

print_stream_message("Greet me warmly and introduce who you are to start our session.")

while True:
    user_input = str(input("ask: "))

    if user_input.lower() in ["exit", "quit", "q"]:                                                                                     
        print("\nAI: Goodbye! Have a wonderful day! 👋\n")                                                                              
        break                                                                                                                           
                                                                                                                                        
    # Don't send empty messages                                                                                                         
    if not user_input:                                                                                                                  
        continue  
    
    print_stream_message(user_input=user_input)