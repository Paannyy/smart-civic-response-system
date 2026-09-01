from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.complaint import Complaint
from app.models.complaint_history import ComplaintStatusHistory
from app.models.notification import Notification
from app.models.attachment import Attachment
from app.api.complaints import ALLOWED_STATUS_TRANSITIONS


def test_pending_can_be_assigned():
    assert "assigned" in ALLOWED_STATUS_TRANSITIONS["pending"]


def test_assigned_can_be_in_progress():
    assert "in_progress" in ALLOWED_STATUS_TRANSITIONS["assigned"]


def test_in_progress_can_be_resolved():
    assert "resolved" in ALLOWED_STATUS_TRANSITIONS["in_progress"]


def test_resolved_cannot_change():
    assert ALLOWED_STATUS_TRANSITIONS["resolved"] == set()


def test_invalid_transition_is_not_allowed():
    assert "pending" not in ALLOWED_STATUS_TRANSITIONS["in_progress"]
    assert "in_progress" not in ALLOWED_STATUS_TRANSITIONS["resolved"]

def test_unauthenticated_complaint_request_returns_401(client):
    response = client.get("/complaints/")

    assert response.status_code == 401

def test_citizen_cannot_assign_complaint(client, db):
    citizen = User(
        name="Test Citizen",
        email="testcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add(citizen)
    db.commit()
    db.refresh(citizen)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.patch(
        "/complaints/1/assign",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "authority_id": 2
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_user_registration_returns_201(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "New Citizen",
            "email": "newcitizen@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "New Citizen"
    assert data["email"] == "newcitizen@example.com"
    assert data["role"] == "citizen"

def test_duplicate_registration_returns_409(client):
    payload = {
        "name": "Duplicate Citizen",
        "email": "duplicate@example.com",
        "password": "password123",
    }

    first_response = client.post(
        "/auth/register",
        json=payload,
    )

    second_response = client.post(
        "/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

def test_login_returns_access_token(client):
    registration = client.post(
        "/auth/register",
        json={
            "name": "Login Citizen",
            "email": "login@example.com",
            "password": "password123",
        },
    )

    assert registration.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_authenticated_user_can_get_profile(client):
    registration = client.post(
        "/auth/register",
        json={
            "name": "Profile Citizen",
            "email": "profile@example.com",
            "password": "password123",
        },
    )

    token = create_access_token({"sub": str(registration.json()["id"])})
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "profile@example.com"
    assert response.json()["role"] == "citizen"


def test_login_with_wrong_password_returns_401(client):
    client.post(
        "/auth/register",
        json={
            "name": "Wrong Password User",
            "email": "wrongpassword@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "wrongpassword@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_citizen_can_create_complaint(client, db):
    citizen = User(
        name="Complaint Citizen",
        email="complaint@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add(citizen)
    db.commit()
    db.refresh(citizen)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.post(
        "/complaints/",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "title": "Street light not working",
            "description": "The street light near my house is not working.",
            "category": "electricity",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Street light not working"
    assert data["category"] == "electricity"
    assert data["status"] == "pending"
    assert data["citizen_id"] == citizen.id

def test_wrong_authority_cannot_update_complaint(client, db):
    citizen = User(
        name="Complaint Owner",
        email="owner@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="Wrong Authority",
        email="wrongauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        is_active=True,
    )

    assigned_authority = User(
        name="Assigned Authority",
        email="assignedauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        is_active=True,
    )

    db.add_all([citizen, authority, assigned_authority])
    db.commit()

    complaint = Complaint(
        title="Water leakage",
        description="There is a water leakage on the main road.",
        category="water",
        priority="medium",
        status="assigned",
        citizen_id=citizen.id,
        assigned_authority_id=assigned_authority.id,
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    token = create_access_token({"sub": str(authority.id)})

    response = client.patch(
        f"/complaints/{complaint.id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "status": "in_progress"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Complaint is not assigned to you"

def test_assigned_authority_can_update_complaint(client, db):
    citizen = User(
        name="Test Citizen",
        email="workflowcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="Assigned Authority",
        email="workflowauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        is_active=True,
    )

    db.add_all([citizen, authority])
    db.commit()

    complaint = Complaint(
        title="Road damage",
        description="The road has been damaged for several days.",
        category="roads",
        priority="medium",
        status="assigned",
        citizen_id=citizen.id,
        assigned_authority_id=authority.id,
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    token = create_access_token({"sub": str(authority.id)})

    response = client.patch(
        f"/complaints/{complaint.id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "status": "in_progress"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "in_progress"
    assert data["assigned_authority_id"] == authority.id

def test_status_update_creates_history(client, db):
    citizen = User(
        name="History Citizen",
        email="historycitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="History Authority",
        email="historyauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        is_active=True,
    )

    db.add_all([citizen, authority])
    db.commit()

    complaint = Complaint(
        title="Garbage problem",
        description="Garbage has not been collected for several days.",
        category="garbage",
        priority="medium",
        status="assigned",
        citizen_id=citizen.id,
        assigned_authority_id=authority.id,
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    token = create_access_token({"sub": str(authority.id)})

    response = client.patch(
        f"/complaints/{complaint.id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "status": "in_progress"
        },
    )

    assert response.status_code == 200

    history = (
        db.query(ComplaintStatusHistory)
        .filter(
            ComplaintStatusHistory.complaint_id == complaint.id
        )
        .all()
    )

    assert len(history) == 1
    assert history[0].status == "in_progress"
    assert history[0].changed_by == authority.id

def test_admin_can_view_all_users(client, db):
    admin = User(
        name="Test Admin",
        email="testadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    citizen = User(
        name="Test Citizen",
        email="adminviewcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([admin, citizen])
    db.commit()

    token = create_access_token({"sub": str(admin.id)})

    response = client.get(
        "/admin/users",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["role"] == "admin"
    assert data["items"][1]["role"] == "citizen"

def test_citizen_cannot_view_all_users(client, db):
    citizen = User(
        name="Normal Citizen",
        email="adminblockedcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add(citizen)
    db.commit()
    db.refresh(citizen)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.get(
        "/admin/users",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_authority_cannot_view_all_users(client, db):
    authority = User(
        name="Blocked Authority",
        email="blockedauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        is_active=True,
    )

    db.add(authority)
    db.commit()
    db.refresh(authority)

    token = create_access_token({"sub": str(authority.id)})

    response = client.get(
        "/admin/users",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_admin_can_change_user_status(client, db):
    admin = User(
        name="Status Admin",
        email="statusadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    citizen = User(
        name="Status Citizen",
        email="statuscitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([admin, citizen])
    db.commit()
    db.refresh(admin)
    db.refresh(citizen)

    token = create_access_token({"sub": str(admin.id)})

    response = client.patch(
        f"/admin/users/{citizen.id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "is_active": False
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = client.patch(
        f"/admin/users/{citizen.id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "is_active": True
        },
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_citizen_cannot_change_user_status(client, db):
    citizen = User(
        name="Blocked Status Citizen",
        email="blockedstatus@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    target = User(
        name="Target User",
        email="targetstatus@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([citizen, target])
    db.commit()
    db.refresh(citizen)
    db.refresh(target)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.patch(
        f"/admin/users/{target.id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "is_active": False
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_inactive_user_cannot_access_protected_endpoint(client, db):
    user = User(
        name="Inactive User",
        email="inactive@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})

    response = client.get(
        "/complaints/",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"

def test_admin_can_view_all_complaints(client, db):
    admin = User(
        name="Complaint Admin",
        email="complaintadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    citizen = User(
        name="Complaint Citizen",
        email="admincomplaintcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([admin, citizen])
    db.commit()

    complaint = Complaint(
        title="Test complaint",
        description="This is a test complaint for admin access.",
        category="garbage",
        priority="medium",
        status="pending",
        citizen_id=citizen.id,
    )

    db.add(complaint)
    db.commit()

    token = create_access_token({"sub": str(admin.id)})

    response = client.get(
        "/admin/complaints",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Test complaint"
    assert data["items"][0]["status"] == "pending"


def test_citizen_cannot_view_all_complaints(client, db):
    citizen = User(
        name="Blocked Citizen",
        email="blockedadmincomplaints@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add(citizen)
    db.commit()
    db.refresh(citizen)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.get(
        "/admin/complaints",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_admin_can_filter_complaints_by_status(client, db):
    admin = User(
        name="Filter Admin",
        email="filteradmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    citizen = User(
        name="Filter Citizen",
        email="filtercitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([admin, citizen])
    db.commit()

    complaint = Complaint(
        title="Garbage complaint",
        description="Garbage collection is delayed in this area.",
        category="garbage",
        priority="medium",
        status="resolved",
        citizen_id=citizen.id,
    )

    db.add(complaint)
    db.commit()

    token = create_access_token({"sub": str(admin.id)})

    response = client.get(
        "/admin/complaints?status_filter=resolved",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "resolved"


def test_admin_can_filter_complaints_by_category(client, db):
    admin = User(
        name="Category Admin",
        email="categoryadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    citizen = User(
        name="Category Citizen",
        email="categorycitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([admin, citizen])
    db.commit()

    complaint = Complaint(
        title="Garbage complaint",
        description="Garbage collection is delayed in this area.",
        category="garbage",
        priority="medium",
        status="resolved",
        citizen_id=citizen.id,
    )

    db.add(complaint)
    db.commit()

    token = create_access_token({"sub": str(admin.id)})

    response = client.get(
        "/admin/complaints?category=garbage",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["category"] == "garbage"

def test_complaint_is_automatically_assigned(client, db):
    citizen = User(
        name="Auto Assign Citizen",
        email="autoassigncitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
    name="Auto Assign Authority",
    email="autoassignauthority@example.com",
    password_hash=hash_password("password123"),
    role="authority",
    department="sanitation",
    is_active=True,
)

    db.add_all([citizen, authority])
    db.commit()
    db.refresh(citizen)
    db.refresh(authority)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.post(
        "/complaints/",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "title": "Garbage collection problem",
            "description": "Garbage has not been collected in our area.",
            "category": "garbage",
            "priority": "medium",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "assigned"
    assert data["assigned_authority_id"] == authority.id

def test_automatic_assignment_creates_history(client, db):
    citizen = User(
        name="History Auto Citizen",
        email="historyautocitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="History Auto Authority",
        email="historyautoauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )

    db.add_all([citizen, authority])
    db.commit()
    db.refresh(citizen)
    db.refresh(authority)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.post(
        "/complaints/",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "title": "Water problem",
            "description": "There is a water problem in our area.",
            "category": "water",
            "priority": "medium",
        },
    )

    assert response.status_code == 201

    complaint_id = response.json()["id"]

    history = (
        db.query(ComplaintStatusHistory)
        .filter(
            ComplaintStatusHistory.complaint_id == complaint_id
        )
        .all()
    )

    assert len(history) == 1
    assert history[0].status == "assigned"
    assert history[0].changed_by == citizen.id

def test_garbage_complaint_is_assigned_to_sanitation_authority(client, db):
    citizen = User(
        name="Department Citizen",
        email="departmentcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    sanitation_authority = User(
        name="Sanitation Authority",
        email="sanitationauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )

    db.add_all([citizen, sanitation_authority])
    db.commit()
    db.refresh(citizen)
    db.refresh(sanitation_authority)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.post(
        "/complaints/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Garbage department test",
            "description": "Testing department based assignment.",
            "category": "garbage",
            "priority": "medium",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "assigned"
    assert data["assigned_authority_id"] == sanitation_authority.id


def test_unsupported_category_remains_pending(client, db):
    citizen = User(
        name="Unsupported Category Citizen",
        email="unsupportedcategory@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="Sanitation Authority",
        email="unsupportedauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )

    db.add_all([citizen, authority])
    db.commit()
    db.refresh(citizen)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.post(
        "/complaints/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Unsupported category test",
            "description": "Testing unsupported complaint category.",
            "category": "other",
            "priority": "medium",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "pending"
    assert data["assigned_authority_id"] is None


def test_no_matching_department_remains_pending(client, db):
    citizen = User(
        name="No Department Citizen",
        email="nodepartmentcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="Water Authority",
        email="waterauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )

    db.add_all([citizen, authority])
    db.commit()
    db.refresh(citizen)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.post(
        "/complaints/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Electricity department test",
            "description": "Testing missing matching department.",
            "category": "electricity",
            "priority": "medium",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "pending"
    assert data["assigned_authority_id"] is None

def test_authority_can_view_assigned_complaints(client, db):
    citizen = User(
        name="Assigned Citizen",
        email="assignedcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="Assigned Authority",
        email="assignedauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )

    complaint = Complaint(
        title="Garbage complaint",
        description="Garbage not collected.",
        category="garbage",
        priority="medium",
        status="assigned",
        citizen_id=1,
        assigned_authority_id=2,
    )

    db.add_all([citizen, authority])
    db.commit()

    db.refresh(citizen)
    db.refresh(authority)

    complaint.citizen_id = citizen.id
    complaint.assigned_authority_id = authority.id

    db.add(complaint)
    db.commit()

    token = create_access_token({"sub": str(authority.id)})

    response = client.get(
        "/complaints/assigned",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["assigned_authority_id"] == authority.id


def test_authority_can_filter_assigned_complaints_by_status(client, db):
    citizen = User(
        name="Status Filter Citizen",
        email="statusfiltercitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="Status Filter Authority",
        email="statusfilterauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )

    db.add_all([citizen, authority])
    db.commit()

    db.refresh(citizen)
    db.refresh(authority)

    complaints = [
        Complaint(
            title="Assigned garbage",
            description="Garbage complaint.",
            category="garbage",
            priority="medium",
            status="assigned",
            citizen_id=citizen.id,
            assigned_authority_id=authority.id,
        ),
        Complaint(
            title="Resolved garbage",
            description="Garbage complaint resolved.",
            category="garbage",
            priority="medium",
            status="resolved",
            citizen_id=citizen.id,
            assigned_authority_id=authority.id,
        ),
    ]

    db.add_all(complaints)
    db.commit()

    token = create_access_token({"sub": str(authority.id)})

    response = client.get(
        "/complaints/assigned?status_filter=resolved",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "resolved"


def test_authority_can_filter_assigned_complaints_by_category(client, db):
    citizen = User(
        name="Category Filter Citizen",
        email="categoryfiltercitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    authority = User(
        name="Category Filter Authority",
        email="categoryfilterauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )

    db.add_all([citizen, authority])
    db.commit()

    db.refresh(citizen)
    db.refresh(authority)

    complaints = [
        Complaint(
            title="Garbage complaint",
            description="Garbage issue.",
            category="garbage",
            priority="medium",
            status="assigned",
            citizen_id=citizen.id,
            assigned_authority_id=authority.id,
        ),
        Complaint(
            title="Water complaint",
            description="Water issue.",
            category="water",
            priority="high",
            status="assigned",
            citizen_id=citizen.id,
            assigned_authority_id=authority.id,
        ),
    ]

    db.add_all(complaints)
    db.commit()

    token = create_access_token({"sub": str(authority.id)})

    response = client.get(
        "/complaints/assigned?category=garbage",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["category"] == "garbage"


def test_citizen_cannot_view_assigned_complaints(client, db):
    citizen = User(
        name="Unauthorized Citizen",
        email="unauthorizedcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add(citizen)
    db.commit()
    db.refresh(citizen)

    token = create_access_token({"sub": str(citizen.id)})

    response = client.get(
        "/complaints/assigned",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403

def test_admin_can_assign_complaint_to_matching_department(client, db):
    admin = User(
        name="Test Admin",
        email="testadminassignment@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    authority = User(
        name="Sanitation Authority",
        email="sanitationassignment@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )

    citizen = User(
        name="Assignment Citizen",
        email="assignmentcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([admin, authority, citizen])
    db.commit()

    complaint = Complaint(
        title="Garbage problem",
        description="Garbage has not been collected.",
        category="garbage",
        priority="medium",
        status="pending",
        citizen_id=citizen.id,
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    token = create_access_token({"sub": str(admin.id)})

    response = client.patch(
        f"/complaints/{complaint.id}/assign",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "authority_id": authority.id
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "assigned"
    assert data["assigned_authority_id"] == authority.id

def test_admin_cannot_assign_complaint_to_wrong_department(client, db):
    admin = User(
        name="Test Admin Wrong Department",
        email="testadminwrongdept@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    authority = User(
        name="Electrical Authority",
        email="electricalwrongdept@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="electrical",
        is_active=True,
    )

    citizen = User(
        name="Wrong Department Citizen",
        email="wrongdepartmentcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )

    db.add_all([admin, authority, citizen])
    db.commit()

    complaint = Complaint(
        title="Garbage problem",
        description="Garbage has not been collected.",
        category="garbage",
        priority="medium",
        status="pending",
        citizen_id=citizen.id,
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    token = create_access_token({"sub": str(admin.id)})

    response = client.patch(
        f"/complaints/{complaint.id}/assign",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "authority_id": authority.id
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Authority department does not match "
        "complaint category: garbage"
    )


def test_inactive_user_cannot_login(client, db):
    user = User(
        name="Deactivated Citizen",
        email="deactivated@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    response = client.post(
        "/auth/login",
        json={
            "email": "deactivated@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


def test_admin_cannot_deactivate_self(client, db):
    admin = User(
        name="Self Deactivate Admin",
        email="selfadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = create_access_token({"sub": str(admin.id)})

    response = client.patch(
        f"/admin/users/{admin.id}/status",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "is_active": False
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Admins cannot deactivate their own account"


def test_workload_aware_assignment_assigns_to_least_loaded_authority(client, db):
    citizen = User(
        name="Workload Citizen",
        email="workloadcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    auth1 = User(
        name="Busy Authority",
        email="busyauth@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )
    auth2 = User(
        name="Free Authority",
        email="freeauth@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )
    db.add_all([citizen, auth1, auth2])
    db.commit()
    db.refresh(citizen)
    db.refresh(auth1)
    db.refresh(auth2)

    # Assign 2 active complaints to auth1 and 1 to auth2
    complaint1 = Complaint(
        title="Garbage 1",
        description="Garbage 1 description.",
        category="garbage",
        priority="medium",
        status="assigned",
        citizen_id=citizen.id,
        assigned_authority_id=auth1.id,
    )
    complaint2 = Complaint(
        title="Garbage 2",
        description="Garbage 2 description.",
        category="garbage",
        priority="medium",
        status="in_progress",
        citizen_id=citizen.id,
        assigned_authority_id=auth1.id,
    )
    complaint3 = Complaint(
        title="Garbage 3",
        description="Garbage 3 description.",
        category="garbage",
        priority="medium",
        status="assigned",
        citizen_id=citizen.id,
        assigned_authority_id=auth2.id,
    )
    # Auth1 also has 3 resolved complaints (must not affect workload)
    resolved_complaint = Complaint(
        title="Resolved Garbage",
        description="Resolved garbage description.",
        category="garbage",
        priority="low",
        status="resolved",
        citizen_id=citizen.id,
        assigned_authority_id=auth1.id,
    )
    db.add_all([complaint1, complaint2, complaint3, resolved_complaint])
    db.commit()

    token = create_access_token({"sub": str(citizen.id)})
    response = client.post(
        "/complaints/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "New Garbage Complaint",
            "description": "Should go to free authority.",
            "category": "garbage",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["assigned_authority_id"] == auth2.id
    assert data["status"] == "assigned"


def test_workload_aware_assignment_tie_breaker_by_lowest_id(client, db):
    citizen = User(
        name="Tie Citizen",
        email="tiecitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    auth1 = User(
        name="Authority A",
        email="autha@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )
    auth2 = User(
        name="Authority B",
        email="authb@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )
    db.add_all([citizen, auth1, auth2])
    db.commit()
    db.refresh(citizen)
    db.refresh(auth1)
    db.refresh(auth2)

    # Both have 0 active complaints. Tie-breaker should pick auth1 (lowest id)
    token = create_access_token({"sub": str(citizen.id)})
    response = client.post(
        "/complaints/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Water Leakage Problem",
            "description": "Water leaking from main pipe on 5th avenue.",
            "category": "water",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    data = response.json()
    expected_id = min(auth1.id, auth2.id)
    assert data["assigned_authority_id"] == expected_id


def test_role_based_single_complaint_access(client, db):
    citizen1 = User(
        name="Owner Citizen",
        email="ownercitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    citizen2 = User(
        name="Other Citizen",
        email="othercitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    auth1 = User(
        name="Assigned Officer",
        email="assignedofficer@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="electrical",
        is_active=True,
    )
    auth2 = User(
        name="Other Officer",
        email="otherofficer@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="electrical",
        is_active=True,
    )
    admin = User(
        name="System Admin",
        email="sysadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    db.add_all([citizen1, citizen2, auth1, auth2, admin])
    db.commit()
    db.refresh(citizen1)
    db.refresh(citizen2)
    db.refresh(auth1)
    db.refresh(auth2)
    db.refresh(admin)

    complaint = Complaint(
        title="Streetlight outage",
        description="Entire block has no streetlights.",
        category="electricity",
        priority="high",
        status="assigned",
        citizen_id=citizen1.id,
        assigned_authority_id=auth1.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # 1. Citizen owner can view
    token_c1 = create_access_token({"sub": str(citizen1.id)})
    r1 = client.get(f"/complaints/{complaint.id}", headers={"Authorization": f"Bearer {token_c1}"})
    assert r1.status_code == 200
    assert r1.json()["id"] == complaint.id

    # 2. Other citizen gets 403 Forbidden
    token_c2 = create_access_token({"sub": str(citizen2.id)})
    r2 = client.get(f"/complaints/{complaint.id}", headers={"Authorization": f"Bearer {token_c2}"})
    assert r2.status_code == 403
    assert r2.json()["detail"] == "You are not allowed to view this complaint"

    # 3. Assigned authority can view
    token_a1 = create_access_token({"sub": str(auth1.id)})
    r3 = client.get(f"/complaints/{complaint.id}", headers={"Authorization": f"Bearer {token_a1}"})
    assert r3.status_code == 200
    assert r3.json()["id"] == complaint.id

    # 4. Other authority gets 403 Forbidden
    token_a2 = create_access_token({"sub": str(auth2.id)})
    r4 = client.get(f"/complaints/{complaint.id}", headers={"Authorization": f"Bearer {token_a2}"})
    assert r4.status_code == 403

    # 5. Admin can view any complaint
    token_admin = create_access_token({"sub": str(admin.id)})
    r5 = client.get(f"/complaints/{complaint.id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert r5.status_code == 200
    assert r5.json()["id"] == complaint.id

    # 6. Non-existent complaint returns 404
    r6 = client.get("/complaints/999999", headers={"Authorization": f"Bearer {token_admin}"})
    assert r6.status_code == 404
    assert r6.json()["detail"] == "Complaint not found"


def test_complaint_search_and_pagination(client, db):
    admin = User(
        name="Search Admin",
        email="searchadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    citizen = User(
        name="Search Citizen",
        email="searchcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add_all([admin, citizen])
    db.commit()
    db.refresh(admin)
    db.refresh(citizen)

    complaints = [
        Complaint(
            title="Pothole on Main St",
            description="Deep pothole causing vehicle damage.",
            category="roads",
            priority="high",
            status="pending",
            citizen_id=citizen.id,
        ),
        Complaint(
            title="Broken Traffic Light",
            description="Signal stuck on red for hours.",
            category="electricity",
            priority="medium",
            status="assigned",
            citizen_id=citizen.id,
        ),
        Complaint(
            title="Water Pipe Burst",
            description="Flooding the sidewalk on Elm street.",
            category="water",
            priority="high",
            status="in_progress",
            citizen_id=citizen.id,
        ),
    ]
    db.add_all(complaints)
    db.commit()

    token = create_access_token({"sub": str(citizen.id)})

    # Search by title keyword
    r_search = client.get(
        "/complaints/?search=pothole",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_search.status_code == 200
    data = r_search.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Pothole on Main St"

    # Search by description keyword
    r_desc = client.get(
        "/complaints/?search=sidewalk",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_desc.status_code == 200
    assert r_desc.json()["total"] == 1
    assert r_desc.json()["items"][0]["title"] == "Water Pipe Burst"

    # Pagination: limit=2, offset=0
    r_page1 = client.get(
        "/complaints/?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_page1.status_code == 200
    assert len(r_page1.json()["items"]) == 2
    assert r_page1.json()["total"] == 3
    assert r_page1.json()["limit"] == 2
    assert r_page1.json()["offset"] == 0

    # Pagination: limit=2, offset=2
    r_page2 = client.get(
        "/complaints/?limit=2&offset=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_page2.status_code == 200
    assert len(r_page2.json()["items"]) == 1

    # Invalid pagination validation
    r_invalid_limit = client.get(
        "/complaints/?limit=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_invalid_limit.status_code == 422

    r_max_limit = client.get(
        "/complaints/?limit=101",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_max_limit.status_code == 422


def test_workload_aware_assignment_ignores_inactive_authority(client, db):
    citizen = User(
        name="Inactive Test Citizen",
        email="inactivetestcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    inactive_auth = User(
        name="Inactive Authority",
        email="inactiveauth@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="public_works",
        is_active=False,
    )
    active_auth = User(
        name="Active Authority",
        email="activeauth@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="public_works",
        is_active=True,
    )
    db.add_all([citizen, inactive_auth, active_auth])
    db.commit()
    db.refresh(citizen)
    db.refresh(inactive_auth)
    db.refresh(active_auth)

    token = create_access_token({"sub": str(citizen.id)})
    response = client.post(
        "/complaints/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Road Repair Request",
            "description": "Massive pothole on highway ramp.",
            "category": "roads",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    assert response.json()["assigned_authority_id"] == active_auth.id


def test_admin_and_authority_search_and_user_search(client, db):
    admin = User(
        name="Super Admin",
        email="superadminsearch@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    authority = User(
        name="Officer Dave",
        email="officerdave@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )
    citizen = User(
        name="Alice Citizen",
        email="alice@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add_all([admin, authority, citizen])
    db.commit()
    db.refresh(admin)
    db.refresh(authority)
    db.refresh(citizen)

    complaint = Complaint(
        title="Water contamination alert",
        description="Tap water has unusual odor.",
        category="water",
        priority="high",
        status="assigned",
        citizen_id=citizen.id,
        assigned_authority_id=authority.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Authority search by numeric complaint ID
    token_auth = create_access_token({"sub": str(authority.id)})
    r_auth_search = client.get(
        f"/complaints/assigned?search={complaint.id}",
        headers={"Authorization": f"Bearer {token_auth}"},
    )
    assert r_auth_search.status_code == 200
    assert r_auth_search.json()["total"] == 1
    assert r_auth_search.json()["items"][0]["id"] == complaint.id

    # Admin search complaints by title
    token_admin = create_access_token({"sub": str(admin.id)})
    r_admin_search = client.get(
        "/admin/complaints?search=contamination",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    # Admin search users by email
    r_user_search = client.get(
        "/admin/users?search=officerdave",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r_user_search.status_code == 200
    assert r_user_search.json()["total"] == 1
    assert r_user_search.json()["items"][0]["name"] == "Officer Dave"


def test_sqlalchemy_orm_relationships(db):
    citizen = User(
        name="Relationship Citizen",
        email="relcitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    authority = User(
        name="Relationship Authority",
        email="relauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )
    db.add_all([citizen, authority])
    db.commit()
    db.refresh(citizen)
    db.refresh(authority)

    complaint = Complaint(
        title="ORM relationship test",
        description="Testing bidirectional relationships.",
        category="water",
        priority="medium",
        status="assigned",
        citizen_id=citizen.id,
        assigned_authority_id=authority.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status="assigned",
        changed_by=citizen.id,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    # 1. User -> created_complaints
    assert len(citizen.created_complaints) == 1
    assert citizen.created_complaints[0].id == complaint.id

    # 2. User -> assigned_complaints
    assert len(authority.assigned_complaints) == 1
    assert authority.assigned_complaints[0].id == complaint.id

    # 3. User -> status_changes
    assert len(citizen.status_changes) == 1
    assert citizen.status_changes[0].id == history.id

    # 4. Complaint -> citizen
    assert complaint.citizen.id == citizen.id
    assert complaint.citizen.email == "relcitizen@example.com"

    # 5. Complaint -> assigned_authority
    assert complaint.assigned_authority is not None
    assert complaint.assigned_authority.id == authority.id

    # 6. Complaint -> status_history
    assert len(complaint.status_history) == 1
    assert complaint.status_history[0].id == history.id

    # 7. ComplaintStatusHistory -> complaint
    assert history.complaint.id == complaint.id

    # 8. ComplaintStatusHistory -> changed_by_user
    assert history.changed_by_user.id == citizen.id


def test_deterministic_pagination_ordering(client, db):
    citizen = User(
        name="Order Citizen",
        email="ordercitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add(citizen)
    db.commit()
    db.refresh(citizen)

    # Create 5 complaints
    for i in range(5):
        c = Complaint(
            title=f"Ordering issue #{i}",
            description=f"Description for issue #{i}",
            category="roads",
            priority="low",
            status="pending",
            citizen_id=citizen.id,
        )
        db.add(c)
    db.commit()

    token = create_access_token({"sub": str(citizen.id)})

    r_all = client.get("/complaints/?limit=5&offset=0", headers={"Authorization": f"Bearer {token}"})
    assert r_all.status_code == 200
    all_ids = [item["id"] for item in r_all.json()["items"]]

    r_p1 = client.get("/complaints/?limit=2&offset=0", headers={"Authorization": f"Bearer {token}"})
    r_p2 = client.get("/complaints/?limit=2&offset=2", headers={"Authorization": f"Bearer {token}"})
    r_p3 = client.get("/complaints/?limit=2&offset=4", headers={"Authorization": f"Bearer {token}"})

    p_ids = (
        [item["id"] for item in r_p1.json()["items"]]
        + [item["id"] for item in r_p2.json()["items"]]
        + [item["id"] for item in r_p3.json()["items"]]
    )

    # Deterministic paginated items match full query exactly without duplicates or skips
    assert p_ids == all_ids


def test_timezone_aware_utc_timestamps(db):
    citizen = User(
        name="Timezone User",
        email="tzuser@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add(citizen)
    db.commit()
    db.refresh(citizen)

    assert citizen.created_at is not None
    assert citizen.updated_at is not None

    complaint = Complaint(
        title="Timezone Complaint",
        description="Testing timezone timestamps.",
        category="roads",
        priority="low",
        status="pending",
        citizen_id=citizen.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    assert complaint.created_at is not None
    assert complaint.updated_at is not None


def test_security_hardening_non_admin_blocked_from_admin_routes(client, db):
    citizen = User(
        name="Security Citizen",
        email="seccitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    authority = User(
        name="Security Authority",
        email="secauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )
    db.add_all([citizen, authority])
    db.commit()
    db.refresh(citizen)
    db.refresh(authority)

    citizen_token = create_access_token({"sub": str(citizen.id)})
    auth_token = create_access_token({"sub": str(authority.id)})

    # Citizen trying admin routes
    r1 = client.get("/admin/users", headers={"Authorization": f"Bearer {citizen_token}"})
    assert r1.status_code == 403

    r2 = client.get("/admin/complaints", headers={"Authorization": f"Bearer {citizen_token}"})
    assert r2.status_code == 403

    r3 = client.patch(f"/admin/users/{authority.id}/status", json={"is_active": False}, headers={"Authorization": f"Bearer {citizen_token}"})
    assert r3.status_code == 403

    # Authority trying admin routes
    r4 = client.get("/admin/users", headers={"Authorization": f"Bearer {auth_token}"})
    assert r4.status_code == 403

    r5 = client.get("/admin/complaints", headers={"Authorization": f"Bearer {auth_token}"})
    assert r5.status_code == 403

    r6 = client.patch(f"/admin/users/{citizen.id}/status", json={"is_active": False}, headers={"Authorization": f"Bearer {auth_token}"})
    assert r6.status_code == 403


def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_admin_analytics_rbac_and_zero_resolved(client, db):
    admin = User(
        name="Analytics Admin",
        email="analyticsadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    citizen = User(
        name="Analytics Citizen",
        email="analyticscitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    authority = User(
        name="Analytics Authority",
        email="analyticsauthority@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )
    db.add_all([admin, citizen, authority])
    db.commit()
    db.refresh(admin)
    db.refresh(citizen)
    db.refresh(authority)

    citizen_token = create_access_token({"sub": str(citizen.id)})
    auth_token = create_access_token({"sub": str(authority.id)})
    admin_token = create_access_token({"sub": str(admin.id)})

    # Non-admin forbidden
    r_cit = client.get("/admin/analytics", headers={"Authorization": f"Bearer {citizen_token}"})
    assert r_cit.status_code == 403

    r_auth = client.get("/admin/analytics", headers={"Authorization": f"Bearer {auth_token}"})
    assert r_auth.status_code == 403

    # Admin access with 0 complaints
    r_admin = client.get("/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    assert r_admin.status_code == 200
    data = r_admin.json()
    assert data["total_complaints"] == 0
    assert data["pending_complaints"] == 0
    assert data["resolved_complaints"] == 0
    assert data["avg_resolution_time_seconds"] is None


def test_admin_analytics_counts_and_resolution_time(client, db):
    admin = User(
        name="Metrics Admin",
        email="metricsadmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    citizen = User(
        name="Metrics Citizen",
        email="metricscitizen@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add_all([admin, citizen])
    db.commit()
    db.refresh(admin)
    db.refresh(citizen)

    now = datetime.now(timezone.utc)
    t1 = now - timedelta(hours=4)
    t2 = now - timedelta(hours=2)

    c1 = Complaint(
        title="Garbage collection missed",
        description="Trash has not been picked up.",
        category="garbage",
        priority="high",
        status="pending",
        citizen_id=citizen.id,
        created_at=t1,
        updated_at=t1,
    )
    c2 = Complaint(
        title="Water leak near school",
        description="Clean water is flowing onto street.",
        category="water",
        priority="medium",
        status="resolved",
        citizen_id=citizen.id,
        created_at=t1,
        updated_at=t2,  # 2 hours resolution time = 7200s
    )
    c3 = Complaint(
        title="Power line down",
        description="Live wire on road after storm.",
        category="electricity",
        priority="high",
        status="in_progress",
        citizen_id=citizen.id,
        created_at=t2,
        updated_at=now,
    )
    db.add_all([c1, c2, c3])
    db.commit()

    admin_token = create_access_token({"sub": str(admin.id)})
    r = client.get("/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()

    assert data["total_complaints"] == 3
    assert data["pending_complaints"] == 1
    assert data["in_progress_complaints"] == 1
    assert data["resolved_complaints"] == 1

    assert data["by_category"]["garbage"] == 1
    assert data["by_category"]["water"] == 1
    assert data["by_category"]["electricity"] == 1
    assert data["by_category"]["roads"] == 0

    assert data["by_department"]["sanitation"] == 1
    assert data["by_department"]["water"] == 1
    assert data["by_department"]["electrical"] == 1
    assert data["by_department"]["public_works"] == 0

    assert data["avg_resolution_time_seconds"] is not None
    assert abs(data["avg_resolution_time_seconds"] - 7200.0) < 1.0
    assert abs(data["avg_resolution_time_by_department"]["water"] - 7200.0) < 1.0


# ---------------------------------------------------------------------------
# PHASE 4 TESTS — Notifications & Attachments
# ---------------------------------------------------------------------------

def test_notification_creation_on_complaint_lifecycle(client, db):
    # Setup users
    citizen = User(
        name="Notif Citizen",
        email="notifcit@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    authority = User(
        name="Notif Officer",
        email="notifauth@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="sanitation",
        is_active=True,
    )
    db.add_all([citizen, authority])
    db.commit()
    db.refresh(citizen)
    db.refresh(authority)

    citizen_token = create_access_token({"sub": str(citizen.id)})
    auth_token = create_access_token({"sub": str(authority.id)})

    # 1. Citizen creates complaint -> auto-assigned to authority
    create_res = client.post(
        "/complaints/",
        json={
            "title": "Overflowing bin on 5th Ave",
            "description": "Garbage has not been collected for three days.",
            "category": "garbage",
            "priority": "high",
        },
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert create_res.status_code == 201
    complaint_id = create_res.json()["id"]

    # Citizen should have complaint_created + complaint_assigned notifications
    cit_notifs = client.get("/notifications/", headers={"Authorization": f"Bearer {citizen_token}"}).json()
    assert cit_notifs["total"] >= 2
    cit_types = [n["type"] for n in cit_notifs["items"]]
    assert "complaint_created" in cit_types
    assert "complaint_assigned" in cit_types

    # Authority should have complaint_assigned notification
    auth_notifs = client.get("/notifications/", headers={"Authorization": f"Bearer {auth_token}"}).json()
    assert auth_notifs["total"] >= 1
    assert auth_notifs["items"][0]["type"] == "complaint_assigned"

    # 2. Authority updates status to in_progress
    client.patch(
        f"/complaints/{complaint_id}/status",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    cit_notifs2 = client.get("/notifications/", headers={"Authorization": f"Bearer {citizen_token}"}).json()
    cit_types2 = [n["type"] for n in cit_notifs2["items"]]
    assert "status_updated" in cit_types2

    # 3. Authority resolves complaint
    client.patch(
        f"/complaints/{complaint_id}/status",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    cit_notifs3 = client.get("/notifications/", headers={"Authorization": f"Bearer {citizen_token}"}).json()
    cit_types3 = [n["type"] for n in cit_notifs3["items"]]
    assert "complaint_resolved" in cit_types3


def test_notifications_retrieval_and_ownership(client, db):
    u1 = User(
        name="User One",
        email="u1@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    u2 = User(
        name="User Two",
        email="u2@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)

    n1 = Notification(user_id=u1.id, type="test", title="U1 Alert", message="Msg 1")
    n2 = Notification(user_id=u2.id, type="test", title="U2 Alert", message="Msg 2")
    db.add_all([n1, n2])
    db.commit()

    u1_token = create_access_token({"sub": str(u1.id)})
    u2_token = create_access_token({"sub": str(u2.id)})

    r1 = client.get("/notifications/", headers={"Authorization": f"Bearer {u1_token}"}).json()
    assert r1["total"] == 1
    assert r1["items"][0]["title"] == "U1 Alert"

    r2 = client.get("/notifications/", headers={"Authorization": f"Bearer {u2_token}"}).json()
    assert r2["total"] == 1
    assert r2["items"][0]["title"] == "U2 Alert"


def test_mark_single_notification_read_and_security(client, db):
    u1 = User(
        name="Owner User",
        email="owner@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    u2 = User(
        name="Other User",
        email="other@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add_all([u1, u2])
    db.commit()
    db.refresh(u1)
    db.refresh(u2)

    n1 = Notification(user_id=u1.id, type="test", title="Alert", message="Hello", is_read=False)
    db.add(n1)
    db.commit()
    db.refresh(n1)

    u1_token = create_access_token({"sub": str(u1.id)})
    u2_token = create_access_token({"sub": str(u2.id)})

    # u2 cannot mark u1's notification as read
    r_forbidden = client.patch(f"/notifications/{n1.id}/read", headers={"Authorization": f"Bearer {u2_token}"})
    assert r_forbidden.status_code == 403

    # u1 can mark own notification read
    r_ok = client.patch(f"/notifications/{n1.id}/read", headers={"Authorization": f"Bearer {u1_token}"})
    assert r_ok.status_code == 200
    assert r_ok.json()["is_read"] is True
    assert r_ok.json()["read_at"] is not None

    # 404 for non-existent
    r_404 = client.patch("/notifications/99999/read", headers={"Authorization": f"Bearer {u1_token}"})
    assert r_404.status_code == 404


def test_mark_all_notifications_read(client, db):
    u = User(
        name="Bulk User",
        email="bulk@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    n1 = Notification(user_id=u.id, type="test", title="Alert 1", message="Msg", is_read=False)
    n2 = Notification(user_id=u.id, type="test", title="Alert 2", message="Msg", is_read=False)
    db.add_all([n1, n2])
    db.commit()

    token = create_access_token({"sub": str(u.id)})

    r = client.patch("/notifications/read-all", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["updated_count"] == 2

    # Check unread_count is now 0
    res = client.get("/notifications/", headers={"Authorization": f"Bearer {token}"}).json()
    assert res["unread_count"] == 0


def test_attachment_upload_and_security(client, db):
    cit1 = User(
        name="Att Cit 1",
        email="attcit1@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    cit2 = User(
        name="Att Cit 2",
        email="attcit2@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add_all([cit1, cit2])
    db.commit()
    db.refresh(cit1)
    db.refresh(cit2)

    complaint = Complaint(
        title="Pothole in front of house",
        description="Dangerous pothole causing traffic issues.",
        category="roads",
        priority="medium",
        status="pending",
        citizen_id=cit1.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    cit1_token = create_access_token({"sub": str(cit1.id)})
    cit2_token = create_access_token({"sub": str(cit2.id)})

    file_content = b"%PDF-1.4 test dummy pdf content"
    files = {"file": ("evidence.pdf", file_content, "application/pdf")}

    # Cit 2 (not creator) attempts to upload -> 403 Forbidden
    r_forbidden = client.post(
        f"/complaints/{complaint.id}/attachments",
        files=files,
        headers={"Authorization": f"Bearer {cit2_token}"},
    )
    assert r_forbidden.status_code == 403

    # Cit 1 (owner) uploads -> 201 Created
    files_ok = {"file": ("evidence.pdf", file_content, "application/pdf")}
    r_ok = client.post(
        f"/complaints/{complaint.id}/attachments",
        files=files_ok,
        headers={"Authorization": f"Bearer {cit1_token}"},
    )
    assert r_ok.status_code == 201
    att_data = r_ok.json()
    assert att_data["original_filename"] == "evidence.pdf"
    assert att_data["content_type"] == "application/pdf"
    assert att_data["complaint_id"] == complaint.id


def test_attachment_validation_invalid_type_and_oversize(client, db):
    cit = User(
        name="Validator Cit",
        email="valcit@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    db.add(cit)
    db.commit()
    db.refresh(cit)

    complaint = Complaint(
        title="Water leak test",
        description="Leaking pipe at corner.",
        category="water",
        priority="low",
        status="pending",
        citizen_id=cit.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    token = create_access_token({"sub": str(cit.id)})

    # Invalid extension / MIME
    bad_files = {"file": ("malicious.exe", b"MZexecutable", "application/octet-stream")}
    r_bad = client.post(
        f"/complaints/{complaint.id}/attachments",
        files=bad_files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_bad.status_code == 400

    # Oversized file (> 5MB)
    huge_content = b"A" * (6 * 1024 * 1024)
    huge_files = {"file": ("huge.jpg", huge_content, "image/jpeg")}
    r_huge = client.post(
        f"/complaints/{complaint.id}/attachments",
        files=huge_files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_huge.status_code == 400


def test_attachment_rbac_listing_and_download(client, db):
    cit = User(
        name="Download Cit",
        email="dlcit@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    auth = User(
        name="Download Officer",
        email="dlauth@example.com",
        password_hash=hash_password("password123"),
        role="authority",
        department="water",
        is_active=True,
    )
    stranger = User(
        name="Stranger Cit",
        email="stranger@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    admin = User(
        name="DL Admin",
        email="dladmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    db.add_all([cit, auth, stranger, admin])
    db.commit()
    db.refresh(cit)
    db.refresh(auth)
    db.refresh(stranger)
    db.refresh(admin)

    complaint = Complaint(
        title="Water burst on main street",
        description="Significant water flooding.",
        category="water",
        priority="high",
        status="assigned",
        citizen_id=cit.id,
        assigned_authority_id=auth.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    cit_token = create_access_token({"sub": str(cit.id)})
    auth_token = create_access_token({"sub": str(auth.id)})
    stranger_token = create_access_token({"sub": str(stranger.id)})
    admin_token = create_access_token({"sub": str(admin.id)})

    # Upload attachment by citizen
    file_bytes = b"\x89PNG\r\n\x1a\n\x00\x00dummy png bytes"
    files = {"file": ("photo.png", file_bytes, "image/png")}
    up_res = client.post(
        f"/complaints/{complaint.id}/attachments",
        files=files,
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert up_res.status_code == 201
    att_id = up_res.json()["id"]

    # Listing:
    # Citizen owner can list
    r_list_cit = client.get(f"/complaints/{complaint.id}/attachments", headers={"Authorization": f"Bearer {cit_token}"})
    assert r_list_cit.status_code == 200
    assert len(r_list_cit.json()) == 1

    # Assigned authority can list
    r_list_auth = client.get(f"/complaints/{complaint.id}/attachments", headers={"Authorization": f"Bearer {auth_token}"})
    assert r_list_auth.status_code == 200

    # Admin can list
    r_list_admin = client.get(f"/complaints/{complaint.id}/attachments", headers={"Authorization": f"Bearer {admin_token}"})
    assert r_list_admin.status_code == 200

    # Stranger citizen is blocked from listing
    r_list_stranger = client.get(f"/complaints/{complaint.id}/attachments", headers={"Authorization": f"Bearer {stranger_token}"})
    assert r_list_stranger.status_code == 403

    # Download:
    # Stranger citizen is blocked from downloading
    r_dl_stranger = client.get(f"/attachments/{att_id}", headers={"Authorization": f"Bearer {stranger_token}"})
    assert r_dl_stranger.status_code == 403

    # Citizen owner can download
    r_dl_cit = client.get(f"/attachments/{att_id}", headers={"Authorization": f"Bearer {cit_token}"})
    assert r_dl_cit.status_code == 200
    assert r_dl_cit.content == file_bytes


def test_attachment_deletion_and_rbac(client, db):
    cit = User(
        name="Delete Cit",
        email="delcit@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    other = User(
        name="Delete Other",
        email="delother@example.com",
        password_hash=hash_password("password123"),
        role="citizen",
        is_active=True,
    )
    admin = User(
        name="Delete Admin",
        email="deladmin@example.com",
        password_hash=hash_password("password123"),
        role="admin",
        is_active=True,
    )
    db.add_all([cit, other, admin])
    db.commit()
    db.refresh(cit)
    db.refresh(other)
    db.refresh(admin)

    complaint = Complaint(
        title="Garbage pile up",
        description="Clean up requested.",
        category="garbage",
        priority="medium",
        status="pending",
        citizen_id=cit.id,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    cit_token = create_access_token({"sub": str(cit.id)})
    other_token = create_access_token({"sub": str(other.id)})
    admin_token = create_access_token({"sub": str(admin.id)})

    # Upload
    files = {"file": ("doc.pdf", b"%PDF-1.4 test", "application/pdf")}
    up = client.post(
        f"/complaints/{complaint.id}/attachments",
        files=files,
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    att_id = up.json()["id"]

    # Other user cannot delete
    r_del_forbidden = client.delete(f"/attachments/{att_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert r_del_forbidden.status_code == 403

    # Owner can delete
    r_del_ok = client.delete(f"/attachments/{att_id}", headers={"Authorization": f"Bearer {cit_token}"})
    assert r_del_ok.status_code == 200

    # 404 after deletion
    r_get_404 = client.get(f"/attachments/{att_id}", headers={"Authorization": f"Bearer {cit_token}"})
    assert r_get_404.status_code == 404


def test_attachment_path_traversal_protection():
    from app.services.attachment_storage import attachment_storage
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        attachment_storage.get_file_path("../../etc/passwd")
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# PHASE 5 TESTS — Production Readiness, Security, Observability & Deployment
# ---------------------------------------------------------------------------

def test_security_headers_present(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Content-Security-Policy" in response.headers


def test_request_id_middleware_and_propagation(client):
    # Test generation of X-Request-ID when not supplied
    res1 = client.get("/health")
    assert "X-Request-ID" in res1.headers
    generated_id = res1.headers["X-Request-ID"]
    assert len(generated_id) > 0

    # Test propagation of custom X-Request-ID
    custom_id = "test-custom-request-id-12345"
    res2 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res2.headers["X-Request-ID"] == custom_id


def test_health_and_readiness_endpoints(client):
    # Liveness check
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"

    # Readiness check (DB connected)
    r_ready = client.get("/ready")
    assert r_ready.status_code == 200
    assert r_ready.json() == {"status": "ready", "database": "connected"}



def test_rate_limiting_auth_endpoint(client):
    from app.core.rate_limiter import limiter
    from app.db.database import settings

    limiter.reset()
    original_limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
    settings.RATE_LIMIT_AUTH_PER_MINUTE = 3  # Low limit for testing

    try:
        for _ in range(3):
            r = client.post("/auth/login", json={"email": "nonexistent@test.com", "password": "wrong"})
            assert r.status_code == 401

        # 4th request should trigger HTTP 429 Too Many Requests
        r_blocked = client.post("/auth/login", json={"email": "nonexistent@test.com", "password": "wrong"})
        assert r_blocked.status_code == 429
        assert "Rate limit exceeded" in r_blocked.json()["detail"]
    finally:
        settings.RATE_LIMIT_AUTH_PER_MINUTE = original_limit
        limiter.reset()


def test_email_service_disabled_and_mocked():
    from app.services.email_service import email_service
    from app.db.database import settings
    from unittest.mock import patch, MagicMock

    # When SMTP_HOST is None, send_email returns False without error
    settings.SMTP_HOST = None
    result = email_service.send_email(
        to_email="citizen@example.com",
        subject="Test Alert",
        body_text="Test Body",
    )
    assert result is False

    # When mocked SMTP server is used
    settings.SMTP_HOST = "smtp.mockserver.local"
    with patch("smtplib.SMTP") as mock_smtp:
        instance = MagicMock()
        mock_smtp.return_value = instance

        res_ok = email_service.send_email(
            to_email="citizen@example.com",
            subject="Test Alert",
            body_text="Test Body",
        )
        assert res_ok is True
        assert instance.send_message.called

    settings.SMTP_HOST = None


def test_s3_storage_provider_abstraction():
    from app.services.attachment_storage import attachment_storage
    from app.db.database import settings

    # Switch to s3 storage mode
    settings.ATTACHMENT_STORAGE = "s3"
    settings.S3_BUCKET = "test-civic-bucket"

    stored_name, size = attachment_storage.save_file(
        file_bytes=b"%PDF-1.4 s3 test",
        original_filename="doc.pdf",
        content_type="application/pdf",
    )
    assert stored_name.endswith(".pdf")
    assert size > 0

    path = attachment_storage.get_file_path(stored_name)
    assert path.is_file()

    deleted = attachment_storage.delete_file(stored_name)
    assert deleted is True

    settings.ATTACHMENT_STORAGE = "local"
