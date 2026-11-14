from app.core.security import hash_password, verify_password, hash_secret

def test_password_hash_round_trip():
    hashed = hash_password('a-strong-password')
    assert hashed != 'a-strong-password'
    assert verify_password('a-strong-password', hashed)
    assert not verify_password('wrong-password', hashed)

def test_device_secret_is_not_stored_as_plaintext():
    secret = 'device-secret-value'
    assert hash_secret(secret) != secret
    assert hash_secret(secret) == hash_secret(secret)
