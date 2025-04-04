from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader, JSONLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from typing import List 
from langchain_core.documents import Document 
import os 
from dotenv import load_dotenv
import json

load_dotenv()


# Initialize text splitter and embedding function 
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
# embedding_function = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
# embedding_function = GoogleGenerativeAIEmbeddings(api_key=os.getenv("GOOGLE_API_KEY"), model='models/gemini-embedding-exp-03-07')
embedding_function = GoogleGenerativeAIEmbeddings(api_key=os.getenv("GOOGLE_API_KEY"), model='models/text-embedding-004')


# Initialize Chroma vector store 
vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embedding_function)



# Document Loading and Splitting
def load_and_split_document(file_path: str) -> List[Document]:
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith('.docx'):
        loader = Docx2txtLoader(file_path)
    elif file_path.endswith('.html'):
        loader = UnstructuredHTMLLoader(file_path)
    elif file_path.endswith('.json'):
        # Use TextLoader instead of JSONLoader for better encoding handling
        loader = TextLoader(file_path, encoding='utf-8')
    elif file_path.endswith('.txt'):
        # Simple text loader with explicit UTF-8 encoding
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        raise ValueError(f"Unsupported file type: {file_path}")
    
    documents = loader.load()
    return text_splitter.split_documents(documents)


# Indexing Documents
def index_document_to_chroma(file_path: str, file_id: int) -> bool:
    try:
        splits = load_and_split_document(file_path)

        # Add metadata to each split 
        for split in splits:
            split.metadata['file_id'] = file_id 
        
        vectorstore.add_documents(splits)
        return True 
    except Exception as e: 
        print(f"Error indexing document: {e}")
        return False
    
# Deleting Documents
def delete_doc_from_chroma(file_id: int):
    try: 
        docs = vectorstore.get(where={"file_id": file_id})
        print(f"Found {len(docs['ids'])} document chunks for file_id {file_id}")

        vectorstore._collection.delete(where={"file_id": file_id})
        print(f"Deleted all documents with file_id {file_id}")

        return True 
    except Exception as e:
        print(f"Error deleting document with file_id {file_id} from Chroma: {str(e)}")
        return False