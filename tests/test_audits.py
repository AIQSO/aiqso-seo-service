"""Tests for audit creation and SSRF protection on audit endpoints."""

from app.models.website import Website


def test_create_audit_requires_valid_website(client, auth_headers, db_session, test_client_record):
    """Audit creation should reject nonexistent website."""
    response = client.post(
        "/api/v1/audits/",
        json={"website_id": 99999, "url": "https://example.com"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_audit_ssrf_blocked(client, auth_headers, db_session, test_client_record):
    """Audit creation should reject URLs targeting internal networks."""
    # Create a website first
    website = Website(
        client_id=test_client_record["client"].id,
        domain="example.com",
        url="https://example.com",
    )
    db_session.add(website)
    db_session.commit()
    db_session.refresh(website)

    response = client.post(
        "/api/v1/audits/",
        json={"website_id": website.id, "url": "http://192.168.1.1/admin"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Invalid audit URL" in response.json()["detail"]


def test_create_audit_blocks_localhost(client, auth_headers, db_session, test_client_record):
    """Audit creation should reject localhost URLs."""
    website = Website(
        client_id=test_client_record["client"].id,
        domain="test.com",
        url="https://test.com",
    )
    db_session.add(website)
    db_session.commit()
    db_session.refresh(website)

    response = client.post(
        "/api/v1/audits/",
        json={"website_id": website.id, "url": "http://localhost:8080/"},
        headers=auth_headers,
    )
    assert response.status_code == 400
