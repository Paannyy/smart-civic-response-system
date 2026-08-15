from app.core.security import create_access_token, hash_password
from app.models.user import User

from app.models.complaint import Complaint
from app.models.complaint_history import ComplaintStatusHistory

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

    assert len(data) == 2
    assert data[0]["role"] == "admin"
    assert data[1]["role"] == "citizen"

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

    assert len(data) == 1
    assert data[0]["title"] == "Test complaint"
    assert data[0]["status"] == "pending"


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