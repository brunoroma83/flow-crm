import json
import urllib.request

login_req = urllib.request.Request(
    "http://127.0.0.1:8000/api/auth/login",
    data=json.dumps({"email": "bruuno@gmail.com", "password": "182436"}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(login_req) as resp:
    token = json.loads(resp.read().decode())["access_token"]

users_req = urllib.request.Request(
    "http://127.0.0.1:8000/api/users",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(users_req) as resp:
    users = json.loads(resp.read().decode())
    print(f"Status: {resp.status}")
    print(f"Total usuários retornados: {len(users)}")
    for u in users:
        print(f" - [{u['id']}] {u['name']} <{u['email']}> - Perfil: {u['role']}")
