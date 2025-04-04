from pydantic import BaseModel, Field 
from enum import Enum 
from datetime import datetime 

# class ModelName(str, Enum):
#     GPT4_O = 'gpt-4o'
#     GPT4_O_MINI = 'gpt-4o-mini'

class ModelName(str, Enum):
    GEMINI_FLASH = 'gemini-2.0-flash'
    GEMINI_PRO = 'gemini-2.5-pro-exp-03-25'

class QueryInput(BaseModel):
    question: str 
    session_id: str = Field(default=None)
    model: ModelName = Field(default=ModelName.GEMINI_FLASH)

class QueryResponse(BaseModel):
    answer: str 
    session_id: str 
    model: ModelName 

class DocumentInfo(BaseModel):
    id: int 
    filename: str 
    upload_timestamp: datetime 

class DeleteFileRequest(BaseModel):
    file_id: int

class ScrapeRequest(BaseModel):
    base_url: str = 'https://www.angelone.in/support/'