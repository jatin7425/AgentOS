# 🚀 LangChain Learning Progress & Cheat Sheet

**Learner:** Jatin  
**Repository:** `/workspaces/AgentOS/practice`  
**Current Status:** Completed Chapters 1–6 (Up to Full RAG). Next: Chapter 7 (Tools).

---

## 📚 Chapters Completed

### ✅ Chapter 1: The Model & Messages
* **Core Concepts:**
  * Initializing an LLM / Chat Model (`ChatGoogleGenerativeAI`).
  * Using modern model: `gemini-3.8-flash`.
  * Roles: `SystemMessage` (personality / rules) vs `HumanMessage` (user query) vs `AIMessage` (AI response).
  * Method: `model.invoke(messages)`.
* **File:** [`chapter1.py`](file:///workspaces/AgentOS/practice/langchain/chapter1.py)

---

### ✅ Chapter 2: Prompt Templates & Dynamic Prompts
* **Core Concepts:**
  * Reusable prompt recipes with `{variables}` instead of hardcoded strings.
  * Modular prompts: defining prompts in separate files / libraries and importing them anywhere.
  * Partial prompts: pre-filling some variables early (`template.partial(cuisine="Italian")`).
  * **Dynamic / Conditional Prompts:**
    * **Jinja2:** Using `{% if is_vip %} ... {% endif %}` directly inside prompt text.
    * **Python Variables:** Passing conditional strings or empty string `""` based on boolean checks.
* **Files:** 
  * [`chapter2_prompts.py`](file:///workspaces/AgentOS/practice/langchain/chapter2_prompts.py)
  * [`chapter2_dynamic_prompts.py`](file:///workspaces/AgentOS/practice/langchain/chapter2_dynamic_prompts.py)

---

### ✅ Chapter 3: Chains & Output Parsers (LCEL)
* **Core Concepts:**
  * **LCEL (LangChain Expression Language):** The assembly line syntax using the pipe operator (`|`).
  * Flow: `Input -> Prompt | Model | Parser -> Output`.
  * **`StrOutputParser`:** Strips raw model metadata, signatures, and returns pure Python string.
  * **`JsonOutputParser`:** Enforces Pydantic schema structure and parses AI replies directly into Python dictionaries (`dict`).

---

### ✅ Chapter 4: Chat History & Memory
* **Core Concepts:**
  * The **Stateless** problem: AI models have no memory between requests.
  * **`MessagesPlaceholder(variable_name="history")`**: The blank space in prompt templates where past conversation is inserted.
  * **Live Streaming:** Using `.stream()` to deliver words word-by-word (real-time typing effect) instead of `.invoke()`.
  * Interactive terminal chat loop with graceful exit handling (`exit`, `quit`, `q`).
* **File:** [`chapter4_memory.py`](file:///workspaces/AgentOS/practice/langchain/chapter4_memory.py)

---

### ✅ Chapter 5: RAG Part 1 — Document Loaders & Chunking
* **Core Concepts:**
  * What is **RAG** (Retrieval Augmented Generation): Giving the AI an open-book reference.
  * `TextLoader`: Reading documents into LangChain `Document` objects (`page_content` + `metadata`).
  * `RecursiveCharacterTextSplitter`: Slicing long texts into manageable chunks.
  * **`chunk_size` vs `chunk_overlap`:** Why overlap prevents sentences and meaning from being cut in half.
  * Debugging: Understanding how hard line breaks (`\n`) affect text splitting priority.
* **File:** [`chapter5_RAG_basic.py`](file:///workspaces/AgentOS/practice/langchain/chapter5_RAG_basic.py)

---

### ✅ Chapter 6: RAG Part 2 — Embeddings, Vector Stores & QA
* **Core Concepts:**
  * **Embeddings:** Converting words into coordinate numbers representing *meaning* (Semantic Search).
  * **Vector Store (`InMemoryVectorStore`):** Database that stores embedded chunks and finds similar concepts.
  * **Retriever:** The librarian that fetches the top $k$ chunks matching the question.
  * **Local Embeddings (`FastEmbedEmbeddings`):** Running embeddings 100% locally on CPU to avoid cloud API rate limits (HTTP 429) and preserve privacy.
  * **The RAG Chain:** 
    `{"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | model | StrOutputParser()`
  * **Critical Engineering Lesson:** Setting appropriate `chunk_size` (e.g. 500–1000) and `k` (e.g. 3–5) so questions aren't separated from their answers.
* **Files:**
  * [`chapter6_rag_complete.py`](file:///workspaces/AgentOS/practice/langchain/chapter6_rag_complete.py)
  * [`company_policy.txt`](file:///workspaces/AgentOS/practice/langchain/company_policy.txt)

---

## 🔜 Next Chapters To Learn

* [ ] **Chapter 7: Tools & Function Calling** (Giving the AI hands to run Python functions like calculators, weather API, database lookups).
* [ ] **Chapter 8: Autonomous Agents** (Letting the AI reason in a loop: Question -> Think -> Choose Tool -> Observe -> Answer).

---

## 📖 Plain English Vocabulary Reference

| Term | Plain English Meaning |
| :--- | :--- |
| **LLM / Chat Model** | The AI brain that generates text from messages. |
| **Prompt Template** | A recipe with blanks (`{variable}`) to fill dynamically. |
| **Chain (`\|`)** | A conveyor belt passing output from one step into the next. |
| **Output Parser** | Converts raw model output into clean text or Python dicts. |
| **Memory / History** | The notebook recording previous turns so the AI remembers. |
| **Streaming** | Printing words one-by-one live as they are generated. |
| **Chunking** | Slicing large files into bite-sized paragraphs. |
| **Embedding** | Converting text into numbers based on semantic meaning. |
| **Vector Store** | A database that searches by meaning instead of exact keywords. |
| **Retriever** | The component that fetches relevant chunks from the vector store. |
| **RAG** | Grounding the model's answer strictly in retrieved documents. |
