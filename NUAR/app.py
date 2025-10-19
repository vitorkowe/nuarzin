from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Função para conectar ao banco de dados
def get_db():
    conn = sqlite3.connect('nuar.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criar tabelas no banco de dados
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de favoritos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            year TEXT,
            rating TEXT,
            image TEXT,
            tipo TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, item_id, tipo)
        )
    ''')
    
    conn.commit()
    conn.close()

# ==================== ROTAS DE PÁGINAS ====================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/cadastro')
def cadastro_page():
    return render_template('cadastro.html')

@app.route('/favoritos')
def favoritos():
    return render_template('favoritos.html')

@app.route('/termos')
def termos_page():
    return render_template('termos.html')

# NOVAS ROTAS ADICIONADAS
@app.route('/filmes')
def filmes_page():
    return render_template('filmes.html')

@app.route('/series')
def series_page():
    return render_template('series.html')

@app.route('/animes')
def animes_page():
    return render_template('animes.html')

# OU se você tiver apenas um arquivo demo.html com tudo:
@app.route('/demo')
def demo_page():
    return render_template('demo.html')

@app.route('/inicio')
def inicio_page():
    return render_template('inicio.html')

# ==================== ROTAS DE API ====================

# Rota de cadastro
@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                      (username, email, hashed_password))
        conn.commit()
        
        # Criar sessão automaticamente após cadastro
        user = cursor.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['email'] = user['email']
        
        return jsonify({
            'success': True, 
            'message': 'Cadastro realizado com sucesso!',
            'user': {
                'username': user['username'],
                'email': user['email']
            }
        })
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email ou usuário já cadastrado'}), 400
    finally:
        conn.close()

# Rota de login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    user = cursor.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['email'] = user['email']
        
        return jsonify({
            'success': True, 
            'message': 'Login realizado com sucesso!',
            'user': {
                'username': user['username'],
                'email': user['email']
            }
        })
    
    return jsonify({'error': 'Email ou senha incorretos'}), 401

# Rota de logout
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso!'})

# Rota para verificar se está logado
@app.route('/api/check-auth')
def check_auth():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True, 
            'username': session['username'],
            'email': session['email']
        })
    return jsonify({'authenticated': False}), 401

# Rota para adicionar favorito
@app.route('/api/favoritos/add', methods=['POST'])
def add_favorito():
    if 'user_id' not in session:
        return jsonify({'error': 'Você precisa estar logado'}), 401
    
    data = request.json
    user_id = session['user_id']
    
    # Validar dados recebidos
    if not data or 'item_id' not in data:
        return jsonify({'error': 'Dados inválidos'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO favoritos (user_id, item_id, title, year, rating, image, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, data['item_id'], data['title'], data['year'], 
              data['rating'], data['image'], data['tipo']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Adicionado aos favoritos!'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Item já está nos favoritos'}), 400
    except Exception as e:
        print(f"Erro ao adicionar favorito: {e}")
        return jsonify({'error': 'Erro ao processar favorito'}), 500
    finally:
        conn.close()

# Rota para listar favoritos do usuário
@app.route('/api/favoritos', methods=['GET'])
def get_favoritos():
    if 'user_id' not in session:
        return jsonify({'error': 'Você precisa estar logado'}), 401
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        favoritos = cursor.execute('''
            SELECT * FROM favoritos WHERE user_id = ? ORDER BY created_at DESC
        ''', (user_id,)).fetchall()
        
        # Organizar por tipo
        result = {
            'filmes': [],
            'series': [],
            'animes': []
        }
        
        for fav in favoritos:
            item = {
                'id': fav['id'],
                'item_id': fav['item_id'],
                'title': fav['title'],
                'year': fav['year'],
                'rating': fav['rating'],
                'image': fav['image']
            }
            
            if fav['tipo'] == 'filme':
                result['filmes'].append(item)
            elif fav['tipo'] == 'serie':
                result['series'].append(item)
            elif fav['tipo'] == 'anime':
                result['animes'].append(item)
        
        return jsonify(result)
    except Exception as e:
        print(f"Erro ao listar favoritos: {e}")
        return jsonify({'error': 'Erro ao carregar favoritos'}), 500
    finally:
        conn.close()

# CORRIGIDO: Rota para remover favorito usando item_id
@app.route('/api/favoritos/remove/<int:item_id>', methods=['DELETE'])
def remove_favorito(item_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Você precisa estar logado'}), 401
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Remover usando item_id ao invés de id
        cursor.execute('DELETE FROM favoritos WHERE item_id = ? AND user_id = ?', 
                      (item_id, user_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': 'Removido dos favoritos!'})
        return jsonify({'error': 'Favorito não encontrado'}), 404
    except Exception as e:
        print(f"Erro ao remover favorito: {e}")
        return jsonify({'error': 'Erro ao processar favorito'}), 500
    finally:
        conn.close()

# Rota para verificar se item está favoritado
@app.route('/api/favoritos/check/<tipo>/<int:item_id>')
def check_favorito(tipo, item_id):
    if 'user_id' not in session:
        return jsonify({'favorited': False})
    
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        fav = cursor.execute('''
            SELECT id FROM favoritos WHERE user_id = ? AND item_id = ? AND tipo = ?
        ''', (user_id, item_id, tipo)).fetchone()
        
        return jsonify({'favorited': fav is not None, 'fav_id': fav['id'] if fav else None})
    except Exception as e:
        print(f"Erro ao verificar favorito: {e}")
        return jsonify({'favorited': False})
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()  # Inicializar banco de dados
    print("=" * 50)
    print("🚀 Servidor Nuar iniciado!")
    print("=" * 50)
    print("📍 Acesse: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)