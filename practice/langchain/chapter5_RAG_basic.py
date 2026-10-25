from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

loader = TextLoader("company_policy.txt")
docs = loader.load()

print(f"Loaded {len(docs)} document.")                                                                                                      
print("Metadata:", docs[0].metadata)                                                                                                        
print("Preview of content:\n", docs[0].page_content[:150], "...\n")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50
)

chunks = text_splitter.split_documents(docs)

print(f"Sliced document into {len(chunks)} chunks:\n")
for i, chunk in enumerate(chunks):
    print(f"--- Chunk #{i+1} ---")
    print(chunk.page_content.strip())
    print()