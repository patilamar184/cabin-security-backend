from getpass import getpass

from app.db.control import ControlSessionLocal, init_control_db
from app.services.owner_registration import register_owner


def main() -> None:
    init_control_db()
    print("Create a Cabin Security owner account")
    full_name = input("Full name: ").strip()
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    phone = input("Phone: ").strip()
    department = input("Department: ").strip()
    password = getpass("Password (minimum 10 characters): ")
    confirm = getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    if len(password) < 10:
        raise SystemExit("Password must contain at least 10 characters.")

    db = ControlSessionLocal()
    try:
        owner, device_id, device_api_key = register_owner(
            db,
            full_name=full_name,
            username=username,
            email=email,
            password=password,
            phone=phone,
            department=department,
        )
        print("\nOwner created successfully.")
        print(f"Owner ID: {owner.id}")
        print(f"Username: {owner.username}")
        print(f"Tenant database: {owner.tenant_database}")
        print(f"ESP32 Device ID: {device_id}")
        print(f"ESP32 Device API key: {device_api_key}")
        print("\nStore the ESP32 API key securely. The hashed key is stored by the backend; it cannot be displayed again.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
