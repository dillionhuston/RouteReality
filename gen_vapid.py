from py_vapid import Vapid

vapid = Vapid()
vapid.generate_keys()
print(f"VAPID_PUBLIC_KEY={vapid.public_key.decode()}")
print(f"VAPID_PRIVATE_KEY={vapid.private_key.decode()}")
print("\nAdd these to your .env file. Also add VAPID_CLAIMS_EMAIL=your-email@example.com")