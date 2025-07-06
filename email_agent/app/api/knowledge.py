from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlmodel import select
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..db.database import get_session
from ..db.models import KnowledgeBase
from ..agent.knowledge_base import knowledge_base_manager
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import json
import os

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating knowledge base entries."""
    title: str
    content: str
    category: str = "general"
    tags: List[str] = []


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating knowledge base entries."""
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/", response_model=Dict[str, Any])
async def create_knowledge_entry(
    entry: KnowledgeBaseCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new knowledge base entry."""
    try:
        # Create database entry
        kb_entry = KnowledgeBase(
            title=entry.title,
            content=entry.content,
            category=entry.category,
            tags=json.dumps(entry.tags) if entry.tags else None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        session.add(kb_entry)
        await session.commit()
        await session.refresh(kb_entry)
        
        # Add to vector store
        success = knowledge_base_manager.add_document(
            title=entry.title,
            content=entry.content,
            category=entry.category,
            tags=entry.tags
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add entry to vector store"
            )
        
        return {
            "id": kb_entry.id,
            "title": kb_entry.title,
            "category": kb_entry.category,
            "created_at": kb_entry.created_at.isoformat(),
            "message": "Knowledge base entry created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating knowledge base entry: {str(e)}"
        )


@router.get("/", response_model=List[Dict[str, Any]])
async def get_knowledge_entries(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get knowledge base entries with optional filtering."""
    try:
        query = select(KnowledgeBase).where(KnowledgeBase.is_active == True)
        
        # Apply filters
        if category:
            query = query.where(KnowledgeBase.category == category)
        if search:
            query = query.where(KnowledgeBase.title.contains(search))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.exec(query)
        entries = result.all()
        
        return [
            {
                "id": entry.id,
                "title": entry.title,
                "category": entry.category,
                "tags": json.loads(entry.tags) if entry.tags else [],
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "content_preview": entry.content[:200] + "..." if len(entry.content) > 200 else entry.content
            }
            for entry in entries
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving knowledge base entries: {str(e)}"
        )


@router.get("/{entry_id}")
async def get_knowledge_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific knowledge base entry."""
    try:
        entry = await session.get(KnowledgeBase, entry_id)
        if not entry or not entry.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base entry not found"
            )
        
        return {
            "id": entry.id,
            "title": entry.title,
            "content": entry.content,
            "category": entry.category,
            "tags": json.loads(entry.tags) if entry.tags else [],
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving knowledge base entry: {str(e)}"
        )


@router.put("/{entry_id}")
async def update_knowledge_entry(
    entry_id: int,
    update_data: KnowledgeBaseUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update a knowledge base entry."""
    try:
        entry = await session.get(KnowledgeBase, entry_id)
        if not entry or not entry.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base entry not found"
            )
        
        # Update fields
        if update_data.title is not None:
            entry.title = update_data.title
        if update_data.content is not None:
            entry.content = update_data.content
        if update_data.category is not None:
            entry.category = update_data.category
        if update_data.tags is not None:
            entry.tags = json.dumps(update_data.tags)
        
        entry.updated_at = datetime.now()
        
        await session.commit()
        
        # Update vector store (re-add document)
        if update_data.content is not None:
            knowledge_base_manager.add_document(
                title=entry.title,
                content=entry.content,
                category=entry.category,
                tags=json.loads(entry.tags) if entry.tags else []
            )
        
        return {"message": "Knowledge base entry updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating knowledge base entry: {str(e)}"
        )


@router.delete("/{entry_id}")
async def delete_knowledge_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete a knowledge base entry (soft delete)."""
    try:
        entry = await session.get(KnowledgeBase, entry_id)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base entry not found"
            )
        
        entry.is_active = False
        entry.updated_at = datetime.now()
        
        await session.commit()
        
        return {"message": "Knowledge base entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting knowledge base entry: {str(e)}"
        )


@router.post("/search")
async def search_knowledge_base(
    query: str,
    top_k: int = 5
):
    """Search knowledge base for relevant content."""
    try:
        relevant_content = knowledge_base_manager.search_relevant_content(query, top_k)
        
        return {
            "query": query,
            "relevant_content": relevant_content,
            "top_k": top_k
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching knowledge base: {str(e)}"
        )


@router.post("/upload")
async def upload_knowledge_files(
    files: List[UploadFile] = File(...),
    category: str = "uploaded"
):
    """Upload files to knowledge base."""
    try:
        uploaded_files = []
        
        for file in files:
            if file.content_type not in ["text/plain", "application/json"]:
                continue
            
            content = await file.read()
            content_str = content.decode('utf-8')
            
            # Handle different file types
            if file.filename.endswith('.json'):
                try:
                    data = json.loads(content_str)
                    if isinstance(data, dict) and 'title' in data and 'content' in data:
                        success = knowledge_base_manager.add_document(
                            title=data['title'],
                            content=data['content'],
                            category=data.get('category', category),
                            tags=data.get('tags', [])
                        )
                        if success:
                            uploaded_files.append(file.filename)
                except json.JSONDecodeError:
                    continue
            else:
                # Plain text file
                title = os.path.splitext(file.filename)[0]
                success = knowledge_base_manager.add_document(
                    title=title,
                    content=content_str,
                    category=category,
                    tags=[file.filename]
                )
                if success:
                    uploaded_files.append(file.filename)
        
        return {
            "message": f"Uploaded {len(uploaded_files)} files to knowledge base",
            "uploaded_files": uploaded_files
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading files: {str(e)}"
        )


@router.get("/stats/overview")
async def get_knowledge_stats():
    """Get knowledge base statistics."""
    try:
        stats = knowledge_base_manager.get_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving knowledge base stats: {str(e)}"
        )


@router.post("/load-from-directory")
async def load_from_directory(
    directory_path: str
):
    """Load knowledge base from directory of files."""
    try:
        if not os.path.exists(directory_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Directory not found"
            )
        
        knowledge_base_manager.load_from_files(directory_path)
        
        return {"message": f"Knowledge base loaded from {directory_path}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading knowledge base: {str(e)}"
        )