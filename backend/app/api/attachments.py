from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.attachment import Attachment
from app.models.complaint import Complaint
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.services.attachment_storage import attachment_storage

router = APIRouter(
    tags=["Attachments"],
)


def verify_complaint_access(complaint: Complaint, user: User) -> None:
    if user.role == "admin":
        return
    if user.role == "authority" and complaint.assigned_authority_id == user.id:
        return
    if complaint.citizen_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not allowed to access this complaint's resources",
    )


@router.post(
    "/complaints/{complaint_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    complaint_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    # Only creator citizen or admin can upload evidence
    if current_user.role != "admin" and complaint.citizen_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to upload attachments for this complaint",
        )

    file_bytes = file.file.read()
    stored_filename, file_size = attachment_storage.save_file(
        file_bytes=file_bytes,
        original_filename=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
    )

    attachment = Attachment(
        complaint_id=complaint.id,
        uploaded_by=current_user.id,
        original_filename=file.filename or "attachment",
        stored_filename=stored_filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return attachment


@router.get(
    "/complaints/{complaint_id}/attachments",
    response_model=List[AttachmentResponse],
)
def get_complaint_attachments(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    verify_complaint_access(complaint, current_user)

    attachments = (
        db.query(Attachment)
        .filter(Attachment.complaint_id == complaint_id)
        .order_by(Attachment.created_at.asc())
        .all()
    )

    return attachments


@router.get(
    "/attachments/{attachment_id}",
)
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id)
        .first()
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == attachment.complaint_id)
        .first()
    )
    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated complaint not found",
        )

    verify_complaint_access(complaint, current_user)

    file_path = attachment_storage.get_file_path(attachment.stored_filename)

    return FileResponse(
        path=file_path,
        media_type=attachment.content_type,
        filename=attachment.original_filename,
    )


@router.delete(
    "/attachments/{attachment_id}",
)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id)
        .first()
    )

    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    if current_user.role != "admin" and attachment.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this attachment",
        )

    attachment_storage.delete_file(attachment.stored_filename)
    db.delete(attachment)
    db.commit()

    return {"message": "Attachment deleted successfully"}
