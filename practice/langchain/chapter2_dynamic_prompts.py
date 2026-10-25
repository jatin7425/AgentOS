from langchain_core.prompts import PromptTemplate  
from langchain_google_genai import ChatGoogleGenerativeAI
from pprint import pprint

model = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.7)
                                                                                                                                            
# Notice the {% if is_vip %} logic directly inside the text!                                                                                
template_text = """                                                                                                                         
You are a concierge at a 5-star hotel.                                                                                                      
The guest's name is {{ name }}.                                                                                                             
                                                                                                                                            
{% if is_vip %}                                                                                                                             
IMPORTANT: This guest is a VIP! Offer them complimentary champagne and a room upgrade.                                                      
{% endif %}                                                                                                                                 
                                                                                                                                            
Guest question: {{ question }}     
return only answer                                                                              
"""                                                                                                                                         
                                                                                                                                            
prompt = PromptTemplate(                                                                                                                    
    template=template_text,                                                                                                                 
    input_variables=["name", "is_vip", "question"],                                                                                         
    template_format="jinja2"  # <--- Tells LangChain to enable if/else conditions!                                                          
)                                                                                                                                           
                                                                                                                                            
# Test 1: Normal Guest (is_vip = False)                                                                                                     
print("--- NORMAL GUEST ---")                                                                                                               
normal_prompt = prompt.invoke({                                                                                                                       
    "name": "Bob",                                                                                                                          
    "is_vip": False,                                                                                                                        
    "question": "Where is the pool?"                                                                                                        
})      
pprint(normal_prompt.text) 
print("\n\n")
pprint(model.invoke(normal_prompt))                                                                                                                

print("\n\n")
print("\n\n")

# Test 2: VIP Guest (is_vip = True)                                                                                                         
print("\n--- VIP GUEST ---")                                                                                                                
vip_prompt = prompt.invoke({                                                                                                                       
    "name": "Sarah",                                                                                                                        
    "is_vip": True,                                                                                                                         
    "question": "Where is the pool?"                                                                                                        
})

pprint(vip_prompt.text)
print("\n\n")
pprint(model.invoke(vip_prompt))                                                                                                                
                                       