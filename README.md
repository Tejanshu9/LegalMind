# Legal Mind - India’s Criminal Law AI Assistant

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.24-orange?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)


**Legal Mind**  is an AI-powered legal assistant built for India’s new criminal justice system. It enables citizens, lawyers, police officers, and judges to seamlessly understand and interact with the latest laws.

By translating complex legal texts into clear, practical insights, **Legal Mind**:

* Helps citizens clearly understand crimes, legal procedures, and evidence rules.
* Guides police officers in effectively applying updated criminal laws.
* Assists lawyers and judges in quickly mapping old laws to the new legal framework.

Powered by **RAG-based question answering**, **hybrid search**, and an **intuitive dashboard**, Legal Mind makes India’s new criminal justice system transparent, accessible, and effortless to navigate for everyone.


---

## 📝 Problem Statement

On **July 1, 2024**, India implemented a major overhaul of its criminal justice system:

- **Bharatiya Nyaya Sanhita (BNS)** replaced the **Indian Penal Code (IPC)**  
- **Bharatiya Nagarik Suraksha Sanhita (BNSS)** replaced the **Code of Criminal Procedure (CrPC)**  
- **Bharatiya Sakshya Adhiniyam (BSA)** replaced the **Indian Evidence Act (IEA)**  

The reforms aim to **shift the focus from punishment to justice**, leveraging modern technology, enhancing victim protection, and streamlining procedures to ensure faster case resolution.

**Legal Mind** empowers citizens with a clear and practical understanding of crimes, criminal procedures, and evidentiary rules, ensuring they stay informed and protected from misinformation or misuse of the law. Since legal language is often difficult for a normal person to grasp, **Legal Mind** provides simple, structured, and easy-to-understand answers.  

It bridges the gap between complex legal texts and everyday understanding while offering professionals precise mappings from old laws to the new legal framework — making their work faster, more accurate, and effortless when navigating India’s evolving criminal justice system.

---
LegalMind/
├── data/
│   ├── esdata/
│   ├── questions/│   │ 
│   │       ├── all-questions.csv
│   │       ├── bns.json
│   │       ├── bnss.json
│   │       ├── bsa.json
│   │       ├── crpc.json
│   │       ├── iea.json
│   │       ├── ipc.json
│   │       ├── llm_questions_mapping.json  
│   │       ├── llm_questions_newlaws.json
│   │       ├── llm_questions_oldlaws.json
│   │       └── mapping_of_laws.json
│   
├── es_data/               # ElasticSearch/OpenSearch/Vector DB data/indices
├── notebooks/             # Development and utility scripts
│   ├── __pycache__/
│   ├── app.py             # Main Streamlit application entry point
│   ├── chunking.ipynb     # Notebook for data preparation/text chunking
│   ├── rag_flow.py        # Core RAG logic (e.g., generate_rag_answer)
│   └── search.py          # Code for search/retrieval functions
├── qdrant_storage/        # Storage directory for the Qdrant vector database
├── test_notebooks/        # Notebooks for evaluation and testing
│   ├── eval_test_data_generation.ipynb
│   ├── prompt_test.ipynb
│   └── search_eval_test.ipynb
├── venv/                  # Python Virtual Environment (ignored by Git)
│   ├── .env               # Environment variables (credentials, API keys, etc.)
│   └── (other venv files)
├── .DS_Store              # macOS file (should be ignored by Git)
├── .env                   # Environment variables (root level)
├── Pipfile                # Dependency management (if using pipenv)
├── Pipfile.lock           # Dependency lock file
├── README.md              # Project overview and documentation (this file)
├── docker-compose.yml     # Configuration for multi-container Docker setup
└── requirements.txt       # List of project dependencies for installation


## 📂 Dataset

The dataset includes:

- **New Laws:** `BNS.pdf`, `BNSS.pdf`, `BSA.pdf`  
- **Old Laws:** `IPC.pdf`, `CRpC.pdf`, `IEA.pdf`  
- **Law Mappings:** `BNS_to_IPC.pdf`, `BNSS_to_CRpC.pdf`, `BSA_to_IEA.pdf`  

All PDFs are **chunked and processed**:

- Chunks from mapping PDFs are stored in `mapping_of_laws.json`  
- Chunks from new laws go into the respective json files  
- Chunks from old laws go into the respective json files    

The **comparisons** include:

- BNS → IPC  
- BNSS → CRpC  
- BSA → IEA  

---

## ⚙️ Features

### RAG-based Question Answering
- Questions generated using LLM for 20% of chunks from each collection and for rest using rule based questions generated.  
- Stored as three JSON files:  
  - `llm_questions_mapping.json`  
  - `llm_questions_newlaws.json`  
  - `llm_questions_oldlaws.json`  
- Each question includes `chunk_id`, 5 generated questions, and source collection.
- implemented in test_notebooks/eval_test_data_generation.ipynb

### Search Methods Evaluated
- **Elastic Search**  
- **Vector Search**  
- **Hybrid Search with re-rankig of documents** (chosen as the best performing method with highest hit rate and MRR)
- implemented in test_notebooks/search_eval_test.ipynb

### Prompt Testing
- Tested 3 different prompts on 200 questions per collection.  
- Best prompt selected for production.
- implemented in test_notebooks/prompt_test.ipynb

### User Interface
- Built using **Streamlit**  
- Users can input queries and receive answers  
- Feedback is collected for every query (query, response, feedback, timestamp)  
- Dashboard provides analytics on usage and feedback

### Modular Architecture
- `app.py` calls `generate_rag_answer()` from `rag_flow.py`  
- `generate_rag_answer()` calls `hybrid_search()` in `search.py`  
- `hybrid_search()` internally uses `elastic_search()` and `vector_search()`

---

## 🚀 Quick Start

### Requirements

All package versions are specified in `Pipfile`. Key dependencies include:

- `streamlit`  
- `pandas`  
- `flask`  
- `psycopg2-binary`  
- `openai`  
- `scikit-learn`  

---
### OpenAI API Key

To run this project, you need an OpenAI API key.  
Add your key to the existing `.env` file .

### Running Locally with Docker (Recommended)

1. Clone the repository:

```bash
git clone git@github.com:Tejanshu9/LegalMind.git
cd LegalMind
pip install -r requirements.txt
cd LegalMind
```
2. Start Docker services:
```bash
docker-compose up
```
3.Run the Streamlit App:
```bash
cd notebooks
streamlit run app.py
```


## Contributing
Suggestions, bug reports, and feature requests can be submitted via GitHub issues. Feedback helps improve the project.

---

##Acknowledgments

DataTalks.Club – for the LLM Zoomcamp course structure

BPRD (Bureau of Police Research and Development), Ministry of Home Affairs, Govt. of India – for valuable data and resources

Open-source community – for the excellent tools and frameworks that made this project possible


