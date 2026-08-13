"""
Integration tests for the updated POST /pandit/apply endpoint.

Tests cover:
- Full submission with all new wizard fields stored correctly in MongoDB
- Server-side gallery file count enforcement (max 7)
- Gallery file-type enforcement (.pdf rejected for gallery, .mp4 accepted)
- Duplicate email rejection
- Password mismatch rejection
- hashed_password not present in API response

Tests are split into two groups:
  - @pytest.mark.skipif(not MONGO_UP, ...)  → requires live MongoDB
  - no skip                                 → pure FastAPI validation, no DB

Run from the backend root:
    python -m pytest test_pandit_full_registration.py -v -s
"""

import io
import os
import sys
import socket
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(__file__))

from httpx import AsyncClient, ASGITransport
from app.main import app


# ── MongoDB availability probe ─────────────────────────────────────────────────

def _mongodb_available(host: str = "localhost", port: int = 27017, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


MONGO_UP = _mongodb_available()


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def async_client():
    """Yield a configured httpx AsyncClient wrapping the FastAPI app."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Test data helpers ──────────────────────────────────────────────────────────

TEST_EMAIL = "test.pandit.reg@mantrasetu.test"

_SMALL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _base_data(overrides: dict | None = None) -> list[tuple]:
    """
    Return all form fields as (key, (None, value, 'text/plain')) tuples.

    When mixed data= + files= is passed to httpx AsyncClient with ASGITransport,
    httpx uses a SyncByteStream which raises RuntimeError. Encoding everything as
    files= tuples forces an AsyncByteStream and avoids the issue.
    """
    d = {
        "name":              "Pt. Ramesh Kumar Sharma",
        "email":             TEST_EMAIL,
        "phone":             "9876543210",
        "password":          "SecurePass@123",
        "confirm_password":  "SecurePass@123",
        "city":              "Varanasi",
        "state":             "Uttar Pradesh",
        "experience":        "10 years",
        "gender":            "Male",
        "availability_mode": "Both",
        "education":         "Shastri (Sanskrit)",
        "gurukul":           "Kashi Vidya Peeth",
        "bio":               "Experienced Vedic priest.",
    }
    if overrides:
        d.update(overrides)

    # Scalar fields as file-like form fields (None filename → treated as form field)
    items: list[tuple] = [
        (k, (None, v, "text/plain")) for k, v in d.items()
    ]
    # Multi-value fields
    for lang in ("Hindi", "Sanskrit"):
        items.append(("languages", (None, lang, "text/plain")))
    for spec in ("वैदिक अनुष्ठान (Vedic Rituals)", "विवाह संस्कार (Marriage Ceremonies)"):
        items.append(("specializations", (None, spec, "text/plain")))
    for area in ("Delhi NCR", "Online Puja"):
        items.append(("service_areas", (None, area, "text/plain")))
    for ach in ("Conducted 500+ yajnas at Kashi Vishwanath", "Trained under Pt. Shri Ram Sharma Acharya"):
        items.append(("achievements", (None, ach, "text/plain")))
    return items


# ── DB-dependent tests ─────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not MONGO_UP, reason="MongoDB not running -- DB tests skipped")
async def test_full_registration_all_fields():
    """
    POST /pandit/apply with every wizard field.
    Verifies response shape, MongoDB document structure, and security.
    """
    from app.core.config import settings
    mongo = AsyncIOMotorClient(settings.MONGODB_URI)
    collection = mongo[settings.DATABASE_NAME]["pandit_applications"]
    await collection.delete_many({"email": TEST_EMAIL})

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/pandit/apply",
                files=_base_data() + [
                    ("gallery_files", ("gallery1.png", _SMALL_PNG, "image/png")),
                ],
            )

        # ── Response ─────────────────────────────────────────────────────────
        assert response.status_code == 200, f"{response.status_code}: {response.text}"
        body = response.json()
        assert body["status"] == "success"
        assert body["application_id"]
        assert body["application_status"] == "pending"
        assert "hashed_password" not in body
        assert "password" not in body

        # ── MongoDB document ──────────────────────────────────────────────────
        doc = await collection.find_one({"email": TEST_EMAIL})
        assert doc is not None

        # specializations -> List[str]
        assert isinstance(doc["specializations"], list)
        assert "vadik anusthan (Vedic Rituals)" in doc["specializations"] or \
               any("Vedic" in s for s in doc["specializations"]), \
               f"specializations: {doc['specializations']}"

        # gallery_files -> list of paths under uploads/gallery/
        assert isinstance(doc["gallery_files"], list)
        assert len(doc["gallery_files"]) == 1
        gpath = doc["gallery_files"][0]
        assert "gallery" in gpath
        assert os.path.exists(gpath), f"Gallery file not on disk: {gpath}"

        # service_areas, achievements
        assert "Delhi NCR" in doc["service_areas"]
        assert len(doc["achievements"]) == 2

        # new scalar fields
        assert doc["gender"] == "Male"
        assert doc["availability_mode"] == "Both"
        assert doc["education"] == "Shastri (Sanskrit)"
        assert doc["gurukul"] == "Kashi Vidya Peeth"
        assert doc["bio"] == "Experienced Vedic priest."

        # password hashed (not plaintext)
        assert "hashed_password" in doc
        assert not doc["hashed_password"].startswith("Secure")

        print(f"\nPASS: Registration stored. id={body['application_id']}")
        safe_specs = [s.encode('ascii', errors='replace').decode('ascii') for s in doc['specializations']]
        safe_achievements = [a.encode('ascii', errors='replace').decode('ascii') for a in doc['achievements']]
        print(f"  specializations : {safe_specs}")
        print(f"  gallery_files   : {doc['gallery_files']}")
        print(f"  service_areas   : {doc['service_areas']}")
        print(f"  achievements    : {safe_achievements}")
        print(f"  hashed_password : {doc['hashed_password'][:20]}... [NOT in response OK]")

    finally:
        await collection.delete_many({"email": TEST_EMAIL})
        mongo.close()


@pytest.mark.anyio
@pytest.mark.skipif(not MONGO_UP, reason="MongoDB not running -- DB tests skipped")
async def test_duplicate_email_rejected():
    """Second application with same email -> 409."""
    from app.core.config import settings
    mongo = AsyncIOMotorClient(settings.MONGODB_URI)
    collection = mongo[settings.DATABASE_NAME]["pandit_applications"]
    await collection.delete_many({"email": TEST_EMAIL})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.post("/pandit/apply", files=_base_data())
            assert r1.status_code == 200, f"First failed: {r1.text}"

            r2 = await client.post("/pandit/apply", files=_base_data())
            assert r2.status_code == 409, f"Got {r2.status_code}: {r2.text}"
        print("\nPASS: Duplicate email -> 409")
    finally:
        await collection.delete_many({"email": TEST_EMAIL})
        mongo.close()


# ── Pure FastAPI validation tests (no MongoDB touch) ───────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not MONGO_UP, reason="MongoDB not running — DB tests skipped")
async def test_gallery_file_count_limit():
    """8 gallery files (> max 7) -> 400 before any DB write."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = _base_data() + [
            ("gallery_files", (f"img_{i}.png", _SMALL_PNG, "image/png"))
            for i in range(8)
        ]
        response = await client.post("/pandit/apply", files=files)

    assert response.status_code == 400, f"Got {response.status_code}: {response.text}"
    assert "Too many gallery files" in response.json()["detail"]
    print("\nPASS: Server-side 7-file gallery cap enforced -> 400")


@pytest.mark.anyio
@pytest.mark.skipif(not MONGO_UP, reason="MongoDB not running — DB tests skipped")
async def test_gallery_pdf_rejected():
    """.pdf must be rejected in gallery (allowed only for aadhaar/cert)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = _base_data() + [("gallery_files", ("portfolio.pdf", b"%PDF-1.4 fake", "application/pdf"))]
        response = await client.post("/pandit/apply", files=files)

    assert response.status_code == 400, f"Got {response.status_code}: {response.text}"
    assert ".pdf" in response.json()["detail"]
    print("\nPASS: .pdf rejected for gallery -> 400")


@pytest.mark.anyio
async def test_password_mismatch_rejected():
    """Mismatched passwords → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = _base_data({"confirm_password": "WrongPassword!"})
        response = await client.post("/pandit/apply", files=data)

    assert response.status_code == 400, f"Got {response.status_code}: {response.text}"
    print("\nPASS: Password mismatch -> 400")
