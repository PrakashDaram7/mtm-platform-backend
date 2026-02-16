"""Payments module routes with role-based access control."""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import (
    get_db,
    get_user_from_db,
)
from app.core.rbac_middleware import (
    require_authenticated,
    require_admin,
)
from app.modules.auth.models import User


router = APIRouter(prefix="/api/payments", tags=["Payments"])


# ============================================================================
# USER PAYMENT ENDPOINTS (Authenticated Users)
# ============================================================================

@router.post("/create-payment")
async def create_payment(
    amount: float,
    description: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Create a new payment (authenticated users only).
    
    Args:
        amount: Payment amount
        description: Payment description
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Payment creation confirmation with payment details
    """
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than 0"
        )
    
    return {
        "message": "Payment created successfully",
        "payment_id": "PAY_" + current_user.id[:8],
        "amount": amount,
        "currency": "USD",
        "description": description,
        "created_by": current_user.full_name,
        "user_id": current_user.id,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "note": "Implement with your Payment model and payment gateway integration"
    }


@router.get("/my-payments")
async def get_my_payments(
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = None
) -> dict:
    """Get current user's payment history.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by payment status (pending, completed, failed, refunded)
        
    Returns:
        List of user's payments
    """
    return {
        "message": "Your payment history",
        "user_id": current_user.id,
        "skip": skip,
        "limit": limit,
        "status_filter": status_filter,
        "note": "Implement with your Payment model"
    }


@router.get("/payment/{payment_id}")
async def get_payment_details(
    payment_id: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Get details of a specific payment.
    
    Users can only view their own payments. Admins can view any payment.
    
    Args:
        payment_id: Payment ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Payment details
    """
    return {
        "message": f"Payment details for {payment_id}",
        "payment_id": payment_id,
        "note": "Implement authorization - users can only view own payments"
    }


@router.post("/payment/{payment_id}/cancel")
async def cancel_payment(
    payment_id: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Cancel a pending payment.
    
    Users can only cancel their own payments. Only pending payments can be cancelled.
    
    Args:
        payment_id: Payment ID to cancel
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Cancellation confirmation
    """
    return {
        "message": f"Payment {payment_id} cancelled",
        "cancelled_by": current_user.full_name,
        "cancelled_at": datetime.utcnow(),
        "note": "Implement authorization and status checks"
    }


@router.post("/payment/{payment_id}/refund-request")
async def request_refund(
    payment_id: str,
    reason: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Request a refund for a payment.
    
    Users can only request refunds for their own payments.
    
    Args:
        payment_id: Payment ID to refund
        reason: Refund reason
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Refund request confirmation
    """
    return {
        "message": f"Refund request submitted for payment {payment_id}",
        "requested_by": current_user.full_name,
        "reason": reason,
        "status": "pending_review",
        "created_at": datetime.utcnow(),
        "note": "Implement refund workflow"
    }


@router.get("/invoice/{payment_id}")
async def download_invoice(
    payment_id: str,
    current_user: User = Depends(require_authenticated),
    db: Session = Depends(get_db)
) -> dict:
    """Download invoice for a payment.
    
    Users can only download invoices for their own payments.
    
    Args:
        payment_id: Payment ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Invoice data
    """
    return {
        "message": f"Invoice for {payment_id}",
        "download_url": f"/api/payments/invoice/{payment_id}/download",
        "note": "Implement actual invoice generation and download"
    }


# ============================================================================
# ADMIN PAYMENT MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/admin/all-payments", dependencies=[Depends(require_admin)])
async def list_all_payments(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> dict:
    """List all payments in the system (admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by payment status
        date_from: Filter payments from this date
        date_to: Filter payments to this date
        
    Returns:
        List of all payments
    """
    return {
        "message": "All payments in system",
        "skip": skip,
        "limit": limit,
        "status_filter": status_filter,
        "date_range": f"{date_from} to {date_to}" if date_from and date_to else None,
        "admin_only": True,
        "note": "Implement with your Payment model"
    }


@router.get("/admin/payment/{payment_id}", dependencies=[Depends(require_admin)])
async def get_payment_details_admin(
    payment_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Get full payment details including sensitive info (admin only).
    
    Args:
        payment_id: Payment ID
        db: Database session
        
    Returns:
        Complete payment details
    """
    return {
        "message": f"Admin view of payment {payment_id}",
        "admin_only": True,
        "includes": [
            "payment_id", "user_info", "amount", "status", "payment_method",
            "transaction_id", "created_at", "updated_at", "notes"
        ]
    }


@router.post("/admin/payment/{payment_id}/approve")
async def approve_payment_admin(
    payment_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Manually approve a payment (admin only).
    
    Args:
        payment_id: Payment ID to approve
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Approval confirmation
    """
    return {
        "message": f"Payment {payment_id} approved",
        "approved_by": current_admin.full_name,
        "approved_at": datetime.utcnow(),
        "admin_only": True
    }


@router.post("/admin/payment/{payment_id}/reject")
async def reject_payment_admin(
    payment_id: str,
    reason: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Reject a payment (admin only).
    
    Args:
        payment_id: Payment ID to reject
        reason: Rejection reason
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Rejection confirmation
    """
    return {
        "message": f"Payment {payment_id} rejected",
        "reason": reason,
        "rejected_by": current_admin.full_name,
        "rejected_at": datetime.utcnow(),
        "admin_only": True
    }


@router.post("/admin/payment/{payment_id}/refund")
async def process_refund_admin(
    payment_id: str,
    amount: Optional[float] = None,
    reason: str = "",
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> dict:
    """Process a refund for a payment (admin only).
    
    Args:
        payment_id: Payment ID to refund
        amount: Refund amount (leave empty for full refund)
        reason: Refund reason
        current_admin: Current admin user
        db: Database session
        
    Returns:
        Refund processing confirmation
    """
    return {
        "message": f"Refund processed for payment {payment_id}",
        "refund_amount": amount or "full",
        "reason": reason,
        "processed_by": current_admin.full_name,
        "processed_at": datetime.utcnow(),
        "admin_only": True
    }


@router.get("/admin/pending-approvals", dependencies=[Depends(require_admin)])
async def get_pending_approvals(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> dict:
    """Get payments pending admin approval (admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of pending payments
    """
    return {
        "message": "Payments pending approval",
        "skip": skip,
        "limit": limit,
        "admin_only": True
    }


@router.get("/admin/pending-refunds", dependencies=[Depends(require_admin)])
async def get_pending_refunds(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
) -> dict:
    """Get pending refund requests (admin only).
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of pending refund requests
    """
    return {
        "message": "Pending refund requests",
        "skip": skip,
        "limit": limit,
        "admin_only": True
    }


# ============================================================================
# ADMIN PAYMENT ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/admin/stats/summary", dependencies=[Depends(require_admin)])
async def get_payment_statistics(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
) -> dict:
    """Get payment statistics summary (admin only).
    
    Args:
        db: Database session
        days: Number of days to include in statistics
        
    Returns:
        Payment statistics
    """
    return {
        "message": f"Payment statistics for last {days} days",
        "statistics": {
            "total_payments": 0,
            "total_amount": 0,
            "completed_payments": 0,
            "completed_amount": 0,
            "pending_payments": 0,
            "pending_amount": 0,
            "failed_payments": 0,
            "refunded_amount": 0
        },
        "admin_only": True,
        "note": "Implement with actual payment data"
    }


@router.get("/admin/stats/daily", dependencies=[Depends(require_admin)])
async def get_daily_payment_stats(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
) -> dict:
    """Get daily payment statistics (admin only).
    
    Args:
        db: Database session
        days: Number of days to include
        
    Returns:
        Daily payment statistics
    """
    return {
        "message": f"Daily payment statistics for last {days} days",
        "data": [],
        "admin_only": True,
        "note": "Implement with actual payment data"
    }
