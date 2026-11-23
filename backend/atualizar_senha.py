# Script temporário para criptografar a senha do admin no banco
# Execute uma vez e depois pode deletar esse arquivo

import bcrypt
from config import conectar, fechar

# Criptografa a senha '123456'
senha = "123456"
senha_hash = bcrypt.hashpw(
    senha.encode("utf-8"),
    bcrypt.gensalt()
).decode("utf-8")

# Atualiza no banco
conexao = conectar()
cursor = conexao.cursor()
cursor.execute("UPDATE usuarios SET senha = %s WHERE email = 'admin@almoxarifado.com'", (senha_hash,))
conexao.commit()
fechar(conexao, cursor)

print("Senha do admin atualizada com sucesso!")
print(f"Login: admin@almoxarifado.com")
print(f"Senha: 123456")