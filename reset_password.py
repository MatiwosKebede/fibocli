import bcrypt

def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt())

new_password = "matiwos"  # Replace with your desired password
hashed_password = hash_password(new_password)
print(f"New hashed password: {hashed_password.decode('utf-8')}")
