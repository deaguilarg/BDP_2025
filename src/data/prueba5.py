from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
import numpy as np
import faiss
import re
import streamlit as st
import fitz  # PyMuPDF
import os
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# -------- FUNCIONES --------

def extract_text_without_footer(pdf_path, margin_bottom=70, handle_columns=True):
    doc = fitz.open(pdf_path)
    text_by_page = []

    for page in doc:
        blocks = page.get_text("blocks")
        page_height = page.rect.height
        page_width = page.rect.width

        clean_blocks = []
        for block in blocks:
            if block[1] < page_height - margin_bottom:
                text = block[4].strip()
                if text and not text.lower().startswith("<image"):
                    clean_blocks.append(block)

        if handle_columns:
            left_col = [b for b in clean_blocks if b[0] < page_width / 2]
            right_col = [b for b in clean_blocks if b[0] >= page_width / 2]

            left_col_sorted = sorted(left_col, key=lambda b: (b[1], b[0]))
            right_col_sorted = sorted(right_col, key=lambda b: (b[1], b[0]))

            sorted_blocks = left_col_sorted + right_col_sorted
        else:
            sorted_blocks = sorted(clean_blocks, key=lambda b: (b[1], b[0]))

        page_text = "\n".join(block[4].strip() for block in sorted_blocks if block[4].strip())
        text_by_page.append(page_text)

    return text_by_page

def splitter(texts, doc_ids):
    split_texts = []
    split_ids = []

    for text, doc_id in zip(texts, doc_ids):
        text = text.replace('\r', '\n')
        pattern = r"(?:^|\n)([¿A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑ\s\d\-:,\.\(\)\?\!]{5,})(?=\n|\s)"
        matches = list(re.finditer(pattern, text))

        if not matches:
            split_texts.append(text.strip())
            split_ids.append(f"{doc_id} | sección única")
            continue

        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chunk = text[start:end].strip()
            clean = re.sub(r'\s+', ' ', chunk).strip()
            if len(clean) > 50:
                split_texts.append(clean)
                split_ids.append(f"{doc_id} | sección {i+1}")

    return split_texts, split_ids

# -------- EJECUCIÓN --------
pdf_path = os.path.abspath("C:/Users/roxsi/OneDrive/Escritorio/ESADE/BDP/Pruebas RAG/Poliza.pdf")
texts = extract_text_without_footer(pdf_path)
doc_ids = [f"{os.path.basename(pdf_path)} | página {i+1}" for i in range(len(texts))]

split_texts, split_ids = splitter(texts, doc_ids)

output_path = os.path.abspath("C:/Users/roxsi/OneDrive/Escritorio/ESADE/BDP/Pruebas RAG/chunks_output.txt")
with open(output_path, "w", encoding="utf-8") as f:
    for i, (text, ref) in enumerate(zip(split_texts, split_ids)):
        f.write(f"*** Chunk {i+1} ***\n")
        f.write(f"Origen: {ref}\n")
        f.write(text + "\n\n")
        f.write("-" * 40 + "\n\n")

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_texts(split_texts, embedding_model)
retriever = vectorstore.as_retriever()

llm = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
    model_name="local-model"
)

qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

query = "¿Qué cubre la póliza?"
respuesta = qa.run(query)

print(f"\n🤖 Respuesta del modelo local:\n{respuesta}")
