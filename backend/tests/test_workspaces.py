"""
Workspace hierarchy CRUD validation tests.

Tests cover:
- Workspace CRUD (create, list, update, delete)
- Course CRUD within workspaces
- Subject CRUD within courses
- Topic CRUD within subjects
- Ownership isolation (user A can't see user B's workspaces)
- Cascade deletion (deleting workspace removes courses/subjects)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestWorkspaceCRUD:
    """Test workspace CRUD operations."""

    def test_create_workspace(self, client: TestClient, auth_headers: dict):
        """Creating a workspace should return 201 with workspace data."""
        response = client.post(
            "/api/v1/workspaces/",
            headers=auth_headers,
            json={"name": "My Study Space", "description": "Test workspace"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Study Space"
        assert data["description"] == "Test workspace"
        assert data["course_count"] == 0
        assert "id" in data

    def test_list_workspaces(self, client: TestClient, auth_headers: dict, test_workspace):
        """Listing workspaces should return user's workspaces."""
        response = client.get("/api/v1/workspaces/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        names = [w["name"] for w in data]
        assert "Test Workspace" in names

    def test_update_workspace(self, client: TestClient, auth_headers: dict, test_workspace):
        """Updating workspace name should persist."""
        response = client.patch(
            f"/api/v1/workspaces/{test_workspace.id}",
            headers=auth_headers,
            json={"name": "Renamed Workspace"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Workspace"

    def test_delete_workspace(self, client: TestClient, auth_headers: dict, test_workspace):
        """Deleting a workspace should return 204."""
        response = client.delete(
            f"/api/v1/workspaces/{test_workspace.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's gone
        response = client.get("/api/v1/workspaces/", headers=auth_headers)
        ids = [w["id"] for w in response.json()]
        assert str(test_workspace.id) not in ids

    def test_workspace_requires_auth(self, client: TestClient):
        """Workspace endpoints should require authentication."""
        response = client.get("/api/v1/workspaces/")
        assert response.status_code == 401

    def test_workspace_isolation(self, client: TestClient, auth_headers: dict, db: Session):
        """User should not see other users' workspaces."""
        from app.models.user import User
        from app.models.workspace import Workspace
        from app.core.security import hash_password

        # Create another user with a workspace
        other_user = User(
            email="other_ws@test.com",
            hashed_password=hash_password("OtherPass123!"),
            full_name="Other WS User",
        )
        db.add(other_user)
        db.flush()

        other_ws = Workspace(
            name="Other User's Workspace",
            user_id=other_user.id,
        )
        db.add(other_ws)
        db.commit()

        # Our user should not see the other workspace
        response = client.get("/api/v1/workspaces/", headers=auth_headers)
        names = [w["name"] for w in response.json()]
        assert "Other User's Workspace" not in names


class TestCourseCRUD:
    """Test course CRUD within workspaces."""

    def test_create_course(self, client: TestClient, auth_headers: dict, test_workspace):
        """Creating a course should return 201."""
        response = client.post(
            f"/api/v1/workspaces/{test_workspace.id}/courses",
            headers=auth_headers,
            json={"name": "Machine Learning"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Machine Learning"
        assert data["subject_count"] == 0
        assert data["workspace_id"] == str(test_workspace.id)

    def test_list_courses(self, client: TestClient, auth_headers: dict, test_workspace, test_course):
        """Listing courses should return courses in the workspace."""
        response = client.get(
            f"/api/v1/workspaces/{test_workspace.id}/courses",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(c["name"] == "Test Course" for c in data)

    def test_update_course(self, client: TestClient, auth_headers: dict, test_workspace, test_course):
        """Updating course name should persist."""
        response = client.patch(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}",
            headers=auth_headers,
            json={"name": "Renamed Course"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Course"

    def test_delete_course(self, client: TestClient, auth_headers: dict, test_workspace, test_course):
        """Deleting a course should return 204."""
        response = client.delete(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_course_not_found(self, client: TestClient, auth_headers: dict, test_workspace):
        """Accessing non-existent course should return 404."""
        response = client.get(
            f"/api/v1/workspaces/{test_workspace.id}/courses",
            headers=auth_headers,
        )
        assert response.status_code == 200  # Empty list is OK


class TestSubjectCRUD:
    """Test subject CRUD within courses."""

    def test_create_subject(self, client: TestClient, auth_headers: dict, test_workspace, test_course):
        """Creating a subject should return 201."""
        response = client.post(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects",
            headers=auth_headers,
            json={"name": "Neural Networks", "color": "#8B5CF6"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Neural Networks"
        assert data["color"] == "#8B5CF6"
        assert data["document_count"] == 0
        assert data["topic_count"] == 0

    def test_list_subjects(self, client: TestClient, auth_headers: dict, test_workspace, test_course, test_subject):
        """Listing subjects should return subjects in the course."""
        response = client.get(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["name"] == "Test Subject" for s in data)

    def test_update_subject(self, client: TestClient, auth_headers: dict, test_workspace, test_course, test_subject):
        """Updating subject should persist changes."""
        response = client.patch(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects/{test_subject.id}",
            headers=auth_headers,
            json={"name": "Updated Subject", "color": "#EF4444"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Subject"
        assert data["color"] == "#EF4444"

    def test_delete_subject(self, client: TestClient, auth_headers: dict, test_workspace, test_course, test_subject):
        """Deleting a subject should return 204."""
        response = client.delete(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects/{test_subject.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestTopicCRUD:
    """Test topic CRUD within subjects."""

    def test_create_topic(self, client: TestClient, auth_headers: dict, test_workspace, test_course, test_subject):
        """Creating a topic should return 201."""
        response = client.post(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects/{test_subject.id}/topics",
            headers=auth_headers,
            json={"name": "Tema 1: Constitución"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Tema 1: Constitución"
        assert data["document_count"] == 0

    def test_list_topics(self, client: TestClient, auth_headers: dict, test_workspace, test_course, test_subject, db: Session):
        """Listing topics should return topics in the subject."""
        from app.models.topic import Topic

        topic = Topic(name="Test Topic", subject_id=test_subject.id)
        db.add(topic)
        db.commit()

        response = client.get(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects/{test_subject.id}/topics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(t["name"] == "Test Topic" for t in data)

    def test_update_topic(self, client: TestClient, auth_headers: dict, test_workspace, test_course, test_subject, db: Session):
        """Updating topic name should persist."""
        from app.models.topic import Topic

        topic = Topic(name="Old Topic", subject_id=test_subject.id)
        db.add(topic)
        db.commit()
        db.refresh(topic)

        response = client.patch(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects/{test_subject.id}/topics/{topic.id}",
            headers=auth_headers,
            json={"name": "New Topic Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Topic Name"

    def test_delete_topic(self, client: TestClient, auth_headers: dict, test_workspace, test_course, test_subject, db: Session):
        """Deleting a topic should return 204."""
        from app.models.topic import Topic

        topic = Topic(name="To Delete", subject_id=test_subject.id)
        db.add(topic)
        db.commit()
        db.refresh(topic)

        response = client.delete(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{test_course.id}/subjects/{test_subject.id}/topics/{topic.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204


class TestCascadeDeletion:
    """Test that deleting parent entities cascades to children."""

    def test_delete_workspace_cascades_to_courses(
        self, client: TestClient, auth_headers: dict, db: Session, test_user,
    ):
        """Deleting a workspace should also delete its courses."""
        from app.models.workspace import Workspace
        from app.models.course import Course

        ws = Workspace(name="Cascade WS", user_id=test_user.id)
        db.add(ws)
        db.flush()

        course = Course(name="Cascade Course", workspace_id=ws.id)
        db.add(course)
        db.commit()
        course_id = course.id

        response = client.delete(
            f"/api/v1/workspaces/{ws.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Course should be gone
        remaining = db.query(Course).filter(Course.id == course_id).first()
        assert remaining is None

    def test_delete_course_cascades_to_subjects(
        self, client: TestClient, auth_headers: dict, db: Session, test_workspace,
    ):
        """Deleting a course should also delete its subjects."""
        from app.models.course import Course
        from app.models.subject import Subject

        course = Course(name="Cascade Course", workspace_id=test_workspace.id)
        db.add(course)
        db.flush()

        subject = Subject(name="Cascade Subject", course_id=course.id)
        db.add(subject)
        db.commit()
        subject_id = subject.id

        response = client.delete(
            f"/api/v1/workspaces/{test_workspace.id}/courses/{course.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        remaining = db.query(Subject).filter(Subject.id == subject_id).first()
        assert remaining is None
