from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic_models import QueryInput, QueryResponse, DocumentInfo, DeleteFileRequest, ScrapeRequest
from langchain_utils import get_rag_chain
from db_utils import insert_application_logs, get_chat_history, get_all_documents, insert_document_record, delete_document_record
from chroma_utils import index_document_to_chroma, delete_doc_from_chroma
from scraper_utils import scrape_and_prepare_faqs
import os
import uuid
import logging
import shutil
import tempfile
import json

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Initialize FastAPI app
app = FastAPI()


# 1. Chat Endpoint

@app.post('/chat', response_model=QueryResponse)
def chat(query_input: QueryInput):
    session_id = query_input.session_id or str(uuid.uuid4())
    logging.info(f'Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model.value}')

    chat_history = get_chat_history(session_id)
    rag_chain = get_rag_chain(query_input.model.value)
    answer = rag_chain.invoke({ 
        "input": query_input.question,
        "chat_history": chat_history
    })['answer']

    insert_application_logs(session_id, query_input.question, answer, query_input.model.value)
    logging.info(f"Session ID: {session_id}, AI Response: {answer}")
    return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)


# 2. Document Upload Endpoint
@app.post('/upload-doc')
def upload_and_index_document(file: UploadFile = File(...)):
    allowed_extensions = ['.pdf', '.docx', '.html']
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed types are: {', '.join(allowed_extensions)}")
    
    temp_file_path = f"temp_{file.filename}"

    try:
        # Save the uploaded file to a temporary file 
        with open(temp_file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_id = insert_document_record(file.filename)
        success = index_document_to_chroma(temp_file_path, file_id)

        if success:
            return {"message": f"File {file.filename} has been successfully uploaded and indexed.", "file_id": file_id}
        else:
            delete_document_record(file_id)
            raise HTTPException(status_code=500, detail=f"Failed to index {file.filename}.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# 3. List Documents Endpoint:
@app.get("/list-docs", response_model=list[DocumentInfo])
def list_documents():
    return get_all_documents()


# 4. Delete Document Endpoint
@app.post('/delete-doc')
def delete_document(request: DeleteFileRequest):
    chroma_delete_success = delete_doc_from_chroma(request.file_id)

    if chroma_delete_success:
        db_delete_success = delete_document_record(request.file_id)
        if db_delete_success:
            return {"message": f"Successfully deleted document with file_id {request.file_id} from the system."}
        else: 
            return {"error": f"Deleted from Chroma but failed to delete document with file_id {request.file_id} from the database."}
    else:
        return {"error": f"Failed to delete document with file_id {request.file_id} from Chroma."}


# 5. Scrape FAQ Endpoint
@app.post('/scrape-faqs')
def scrape_faqs(request: ScrapeRequest):
    """
    Scrape FAQs from Angel One support pages and add them to the RAG system
    """
    try:
        logging.info(f"Starting FAQ scraping from {request.base_url}")
        
        # Scrape FAQs from the support pages
        faq_data = scrape_and_prepare_faqs(request.base_url)
        
        if not faq_data:
            return {"message": "No FAQ data found or scraping failed"}
        
        # Count of successfully indexed FAQs
        indexed_count = 0
        file_ids = []
        
        # Process each FAQ page
        for i, faq_page in enumerate(faq_data):
            # Create a simplified version with only the essential content
            simplified_data = {
                "url": faq_page["url"],
                "content": faq_page.get("content", "")
            }
            
            # Generate a safe filename
            safe_filename = f"faq_{i}.txt"
            temp_file_path = f"temp_{safe_filename}"
            
            try:
                # Write directly as text content to avoid JSON encoding issues
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(simplified_data.get("content", ""))
                
                # Store the document record
                file_id = insert_document_record(safe_filename)
                
                # Index the document to Chroma
                success = index_document_to_chroma(temp_file_path, file_id)
                
                if success:
                    indexed_count += 1
                    file_ids.append(file_id)
                else:
                    delete_document_record(file_id)
                    logging.error(f"Failed to index FAQ from {faq_page['url']}")
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        
        return {
            "message": f"Successfully scraped and indexed {indexed_count} FAQ pages out of {len(faq_data)} total pages",
            "file_ids": file_ids
        }
    
    except Exception as e:
        logging.error(f"Error during FAQ scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during FAQ scraping: {str(e)}")


