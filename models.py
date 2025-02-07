from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Configuración de usuarios: se utiliza un solo usuario "Davalos"
users = {
    "Davalos": User("1", "Davalos", "EchoStudio1234")
}

def get_user(username):
    return users.get(username)
