import os
import json
import pickle
from typing import List, Dict, Optional, Any
from datetime import datetime
import numpy as np
import faiss
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import openai
from ..core.config import settings
from ..db.models import KnowledgeBase
import logging

logger = logging.getLogger(__name__)

# Set OpenAI API key
openai.api_key = settings.openai_api_key


class KnowledgeBaseManager:
    """Knowledge base manager for storing and retrieving relevant information."""
    
    def __init__(self):
        self.embeddings_dim = 1536  # OpenAI embeddings dimension
        self.index = None
        self.documents = []
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        self.knowledge_base_path = settings.knowledge_base_path
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Initialize FAISS index and load existing knowledge base."""
        try:
            # Create knowledge base directory if it doesn't exist
            os.makedirs(self.knowledge_base_path, exist_ok=True)
            
            # Initialize FAISS index
            self.index = faiss.IndexFlatL2(self.embeddings_dim)
            
            # Load existing knowledge base
            self._load_knowledge_base()
            
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
    
    def _load_knowledge_base(self):
        """Load existing knowledge base from disk."""
        try:
            index_path = os.path.join(self.knowledge_base_path, "faiss_index.bin")
            docs_path = os.path.join(self.knowledge_base_path, "documents.pkl")
            
            if os.path.exists(index_path) and os.path.exists(docs_path):
                # Load FAISS index
                self.index = faiss.read_index(index_path)
                
                # Load documents
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                
                logger.info(f"Loaded knowledge base with {len(self.documents)} documents")
            else:
                logger.info("No existing knowledge base found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
    
    def _save_knowledge_base(self):
        """Save knowledge base to disk."""
        try:
            os.makedirs(self.knowledge_base_path, exist_ok=True)
            
            # Save FAISS index
            index_path = os.path.join(self.knowledge_base_path, "faiss_index.bin")
            faiss.write_index(self.index, index_path)
            
            # Save documents
            docs_path = os.path.join(self.knowledge_base_path, "documents.pkl")
            with open(docs_path, 'wb') as f:
                pickle.dump(self.documents, f)
            
            logger.info("Knowledge base saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving knowledge base: {e}")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get OpenAI embedding for text."""
        try:
            response = openai.Embedding.create(
                model="text-embedding-ada-002",
                input=text
            )
            return np.array(response['data'][0]['embedding'], dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return np.zeros(self.embeddings_dim, dtype=np.float32)
    
    def add_document(self, title: str, content: str, category: str = "general", 
                     tags: List[str] = None) -> bool:
        """Add document to knowledge base."""
        try:
            # Split content into chunks
            chunks = self.text_splitter.split_text(content)
            
            for i, chunk in enumerate(chunks):
                # Get embedding
                embedding = self.get_embedding(chunk)
                
                # Add to FAISS index
                self.index.add(embedding.reshape(1, -1))
                
                # Store document metadata
                doc_metadata = {
                    "title": title,
                    "content": chunk,
                    "category": category,
                    "tags": tags or [],
                    "chunk_index": i,
                    "created_at": datetime.now().isoformat(),
                    "id": len(self.documents)
                }
                
                self.documents.append(doc_metadata)
            
            # Save to disk
            self._save_knowledge_base()
            
            logger.info(f"Added document '{title}' with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return False
    
    def search_relevant_content(self, query: str, top_k: int = 5) -> str:
        """Search for relevant content based on query."""
        try:
            if self.index.ntotal == 0:
                return ""
            
            # Get query embedding
            query_embedding = self.get_embedding(query)
            
            # Search in FAISS index
            distances, indices = self.index.search(
                query_embedding.reshape(1, -1), 
                min(top_k, self.index.ntotal)
            )
            
            # Collect relevant documents
            relevant_content = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    relevant_content.append({
                        "content": doc["content"],
                        "title": doc["title"],
                        "score": float(distances[0][i])
                    })
            
            # Format for response
            if relevant_content:
                formatted_content = "Relevant information:\n\n"
                for doc in relevant_content:
                    formatted_content += f"From '{doc['title']}':\n{doc['content']}\n\n"
                return formatted_content
            else:
                return ""
                
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return ""
    
    def add_email_context(self, email_subject: str, email_body: str, 
                         response: str, category: str = "email_context"):
        """Add email context to knowledge base for learning."""
        try:
            title = f"Email Context: {email_subject}"
            content = f"Subject: {email_subject}\n\nBody: {email_body}\n\nResponse: {response}"
            
            self.add_document(title, content, category, ["email", "context"])
            
        except Exception as e:
            logger.error(f"Error adding email context: {e}")
    
    def load_from_files(self, directory: str):
        """Load knowledge base from text files in directory."""
        try:
            if not os.path.exists(directory):
                logger.warning(f"Directory {directory} does not exist")
                return
            
            for filename in os.listdir(directory):
                if filename.endswith('.txt'):
                    file_path = os.path.join(directory, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Use filename as title
                    title = os.path.splitext(filename)[0]
                    self.add_document(title, content, "file", [filename])
                    
                elif filename.endswith('.json'):
                    file_path = os.path.join(directory, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Handle different JSON structures
                    if isinstance(data, dict):
                        if 'title' in data and 'content' in data:
                            self.add_document(
                                data['title'], 
                                data['content'], 
                                data.get('category', 'json'),
                                data.get('tags', [])
                            )
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'title' in item and 'content' in item:
                                self.add_document(
                                    item['title'],
                                    item['content'],
                                    item.get('category', 'json'),
                                    item.get('tags', [])
                                )
            
            logger.info(f"Loaded knowledge base from {directory}")
            
        except Exception as e:
            logger.error(f"Error loading from files: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        categories = {}
        for doc in self.documents:
            category = doc.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        
        return {
            "total_documents": len(self.documents),
            "total_indexed": self.index.ntotal if self.index else 0,
            "categories": categories,
            "embeddings_dimension": self.embeddings_dim
        }


# Global knowledge base manager
knowledge_base_manager = KnowledgeBaseManager()