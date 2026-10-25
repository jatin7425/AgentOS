import os                                                                                                                                   
from langchain_community.document_loaders import TextLoader                                                                                 
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter                                                                         
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings                                                     
from langchain_core.vectorstores import InMemoryVectorStore                                                                                 
from langchain_core.prompts import ChatPromptTemplate                                                                                       
from langchain_core.output_parsers import StrOutputParser                                                                                   
from langchain_core.runnables import RunnablePassthrough

                                                                                                                                            
# 1. LOAD & CHUNK (from Chapter 5)                                                                                                          
print("1. Loading and chunking document...")                                                                                                
loader = TextLoader("company_policy.txt")                                                                                                   
docs = loader.load()                                                                                                                        
                                                                                                                                            
text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)                                                            
chunks = text_splitter.split_documents(docs)                                                                                                
                                                                                                                                            
# 2. EMBEDDINGS & VECTOR STORE                                                                                                              
# This converts our chunks into mathematical meaning and stores them in memory                                                              
print("2. Creating embeddings and storing in Vector Store...")                                                                                    
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")                                                                
vector_store = InMemoryVectorStore.from_documents(chunks, embeddings)
                                                                                
# 3. THE RETRIEVER (Our Librarian)                                                                                                          
# k=4 means: "fetch the top 4 most relevant chunks"                                                                                         
retriever = vector_store.as_retriever(search_kwargs={"k": 4})                                                                               
                                                                                                                                            
# Helper function to format the retrieved documents into one block of text                                                                  
def format_docs(docs):                                                                                                                      
    return "\n\n".join(doc.page_content for doc in docs)
                                                                                                                                   
# 4. THE PROMPT (Grounding the AI in our facts)                                                                                             
prompt = ChatPromptTemplate.from_template("""                                                                                               
You are a helpful HR assistant at QuantumCloud Technologies.                                                                                
Answer the user's question using ONLY the provided context below.                                                                           
If the answer is not in the context, say: "I do not have information about that in the company policy."                                     
                                                                                                                                            
Context:                                                                                                                                    
{context}                                                                                                                                   
                                                                                                                                            
Question: {question}                                                                                                                        
""")     
                                                            
# 5. THE MODEL                                                                                                                              
model = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.1)   

# 6. THE RAG CHAIN (Conveyor belt!)                                                                                                         
# Notice RunnablePassthrough: it passes your question directly to {question}                                                                
# while the retriever fetches the matching text for {context}!                                                                              
rag_chain = (                                                                                                                               
    {"context": retriever | format_docs, "question": RunnablePassthrough()}                                                                 
    | prompt                                                                                                                                
    | model                                                                                                                                 
    | StrOutputParser()                                                                                                                     
)

def print_stream_message(user_input):
    for chunk in rag_chain.stream(user_input):
        print(chunk, end="", flush=True)
    print()    

while True:
    user_input = str(input("ask: "))

    if user_input.lower() in ["exit", "quit", "q"]:                                                                                     
        print("\nAI: Goodbye! Have a wonderful day! 👋\n")                                                                              
        break                                                                                                                           
                                                                                                                                        
    # Don't send empty messages                                                                                                         
    if not user_input:                                                                                                                  
        continue  
    
    print_stream_message(user_input=user_input)