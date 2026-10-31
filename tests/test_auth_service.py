from service.auth_service import hash_password, verify_password

def test_password_hash_roundtrip():
    encoded=hash_password("a-strong-password-123")
    assert encoded != "a-strong-password-123"
    assert verify_password("a-strong-password-123",encoded)
    assert not verify_password("wrong-password",encoded)
