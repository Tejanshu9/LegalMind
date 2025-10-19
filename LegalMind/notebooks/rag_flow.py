import os
from openai import OpenAI
from dotenv import load_dotenv
from search import hybrid_search

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),  # your LLM7 key
    base_url="https://api.llm7.io/v1"     # required now
)


def generate_rag_answer(question: str, alpha=0.3, return_sources=False):
    """
    Full RAG flow:
    1. Run hybrid search (ES + Vector)
    2. Build context string
    3. Generate answer using OpenAI GPT
    """
    if not question.strip():
        return "⚠️ Please provide a valid question."

    results = hybrid_search(question, alpha=alpha)

    context = ""
    sources = []  # To store document sources if needed

    for collection, docs in results.items():
        for d in docs:
            text = d.get("text", "")
            fields = d.get("fields") or d.get("metadata") or {}
            fields_str = ", ".join([f"{k}: {v}" for k, v in fields.items()])
            chunk_str = f"{text}\n[{fields_str}]\n"
            context += chunk_str + "\n"

            # If return_sources=True, you can collect them here
            sources.append({"collection": collection, "fields": fields})

    if not context.strip():
        return "⚠️ No relevant content found for this query."

    # Build prompt
    prompt = f"""Prompt :
You are a legal assistant AI for Indian Criminal laws.

Rules:

1. Normal questions:
   - Crime: Define the act using BNS.
   - Procedure: Explain how authorities act using BNSS.
   - Evidence: Explain what evidence can be used using BSA.
   - Mention the relevant law (BNS, BNSS, BSA, IPC, CrPC, IEA) wherever applicable.
   - Keep language simple and understandable by ordinary people.

2. Direct section/chapter questions:
   - Explain the section directly and clearly using the relevant law.
   - Skip the usual crime-procedure-evidence format.
   - EXPLAIN the exact section that the user asked you.

3. Showing changes between old and new laws:
   - Use collection-map.
   - Explain with collection-new and collection-old: show old section, new section, subject, and what changed.

4. Restrictions:
   - Do NOT hallucinate.
   - If context is missing, reply: "Sorry, can you rephrase the question?".
   - Only use IPC, CrPC, IEA if explicitly asked.
   - Do NOT use your knowledge to say something.
   - Do NOT tell anything about context in the answer.

Context:
{context}

Question: {question}

Answer:""".format(context=context, question=question)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return response.choices[0].message.content.strip()
    except AttributeError:
        # fallback for older SDK versions
        return response.choices[0].content.strip()
