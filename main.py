from flask import Flask, render_template, request, redirect, url_for, flash
import requests as http
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5001')
API_KEY      = os.environ.get('API_KEY', '')


def api_headers():
    return {'X-API-Key': API_KEY}


# ---------------------------------------------------------------------------
# Lightweight DTO so templates can use recipe.ingredient_list etc. unchanged
# ---------------------------------------------------------------------------

class RecipeDTO:
    def __init__(self, data):
        self.id           = data.get('id')
        self.title        = data.get('title', '')
        self.description  = data.get('description')
        self.category     = data.get('category')
        self.prep_time    = data.get('prep_time')
        self.cook_time    = data.get('cook_time')
        self.servings     = data.get('servings')
        self.ingredients  = data.get('ingredients')
        self.instructions = data.get('instructions')
        self.image_url    = data.get('image_url')
        self.created_at   = data.get('created_at')

    @property
    def ingredient_list(self):
        if self.ingredients:
            return [i.strip() for i in self.ingredients.strip().split('\n') if i.strip()]
        return []

    @property
    def instruction_list(self):
        if self.instructions:
            return [i.strip() for i in self.instructions.strip().split('\n') if i.strip()]
        return []

    @property
    def total_time(self):
        return (self.prep_time or 0) + (self.cook_time or 0)


# ---------------------------------------------------------------------------

CATEGORY_ICONS = {
    'Breakfast':  '',
    'Lunch':      '',
    'Dinner':     '',
    'Dessert':    '',
    'Snack':      '',
    'Soup':       '',
    'Salad':      '',
    'Bread':      '',
    'Drinks':     '',
    'Vegetarian': '',
    'Seafood':    '',
    'Chicken':    '',
    'Other':      '',
}

CATEGORIES = list(CATEGORY_ICONS.keys())


API_KEY = os.environ.get('API_KEY', '')

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///cookbook_api.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Recipe(db.Model):
    __tablename__ = 'recipes'

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text)
    category     = db.Column(db.String(50))
    prep_time    = db.Column(db.Integer)
    cook_time    = db.Column(db.Integer)
    servings     = db.Column(db.Integer)
    ingredients  = db.Column(db.Text)
    instructions = db.Column(db.Text)
    image_url    = db.Column(db.String(500))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'title':        self.title,
            'description':  self.description,
            'category':     self.category,
            'prep_time':    self.prep_time,
            'cook_time':    self.cook_time,
            'servings':     self.servings,
            'ingredients':  self.ingredients,
            'instructions': self.instructions,
            'image_url':    self.image_url,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
        }


@app.before_request
def require_api_key():
    if request.path == '/health':
        return
    if not API_KEY:
        return
    if request.headers.get('X-API-Key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/recipes', methods=['GET'])
def list_recipes():
    search   = request.args.get('search', '')
    category = request.args.get('category', '')

    params = {}
    if search:
        params['search'] = search
    if category:
        params['category'] = category

    resp = http.get(f'{API_BASE_URL}/api/recipes', params=params, headers=api_headers())
    resp.raise_for_status()
    data = resp.json()

    recipes        = [RecipeDTO(r) for r in data.get('recipes', [])]
    all_categories = data.get('categories', [])

    return jsonify({
        'recipes':    [r.to_dict() for r in recipes],
        'categories': all_categories,
    })


@app.route('/api/recipes/<int:id>', methods=['GET'])
def get_recipe(id):
    recipe = db.session.get(Recipe, id)
    if recipe is None:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(recipe.to_dict())


@app.route('/api/recipes', methods=['POST'])
def create_recipe():
    data = request.get_json(force=True)
    if not data or not data.get('title'):
        return jsonify({'error': 'title is required'}), 400

    recipe = Recipe(
        title        = data['title'].strip(),
        description  = data.get('description', '').strip() or None,
        category     = data.get('category', 'Other'),
        prep_time    = data.get('prep_time'),
        cook_time    = data.get('cook_time'),
        servings     = data.get('servings'),
        ingredients  = data.get('ingredients', '').strip() or None,
        instructions = data.get('instructions', '').strip() or None,
        image_url    = data.get('image_url', '').strip() or None,
    )
    db.session.add(recipe)
    db.session.commit()
    return jsonify(recipe.to_dict()), 201


@app.route('/api/recipes/<int:id>', methods=['PUT'])
def update_recipe(id):
    recipe = db.session.get(Recipe, id)
    if recipe is None:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json(force=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    recipe.title        = data.get('title', recipe.title).strip()
    recipe.description  = data.get('description', recipe.description or '').strip() or None
    recipe.category     = data.get('category', recipe.category)
    recipe.prep_time    = data.get('prep_time', recipe.prep_time)
    recipe.cook_time    = data.get('cook_time', recipe.cook_time)
    recipe.servings     = data.get('servings', recipe.servings)
    recipe.ingredients  = data.get('ingredients', recipe.ingredients or '').strip() or None
    recipe.instructions = data.get('instructions', recipe.instructions or '').strip() or None
    recipe.image_url    = data.get('image_url', recipe.image_url or '').strip() or None
    db.session.commit()
    return jsonify(recipe.to_dict())


@app.route('/recipe/new', methods=['GET', 'POST'])
def new_recipe():
    if request.method == 'POST':
        payload = {
            'title':        request.form['title'].strip(),
            'description':  request.form.get('description', '').strip(),
            'category':     request.form.get('category', 'Other'),
            'prep_time':    int(request.form['prep_time'])  if request.form.get('prep_time')  else None,
            'cook_time':    int(request.form['cook_time'])  if request.form.get('cook_time')  else None,
            'servings':     int(request.form['servings'])   if request.form.get('servings')   else None,
            'ingredients':  request.form.get('ingredients',  '').strip(),
            'instructions': request.form.get('instructions', '').strip(),
            'image_url':    request.form.get('image_url',    '').strip(),
        }
        resp = http.post(f'{API_BASE_URL}/api/recipes', json=payload, headers=api_headers())
        resp.raise_for_status()
        recipe = RecipeDTO(resp.json())
        flash('Recipe added successfully!', 'success')
        return redirect(url_for('recipe_detail', id=recipe.id))

    return render_template('recipe_form.html', recipe=None, categories=CATEGORIES, action='Add New Recipe')


@app.route('/recipe/<int:id>')
def recipe_detail(id):
    resp = http.get(f'{API_BASE_URL}/api/recipes/{id}', headers=api_headers())
    if resp.status_code == 404:
        return render_template('404.html'), 404
    resp.raise_for_status()
    recipe = RecipeDTO(resp.json())
    return render_template('recipe_detail.html', recipe=recipe, category_icons=CATEGORY_ICONS)


@app.route('/recipe/<int:id>/edit', methods=['GET', 'POST'])
def edit_recipe(id):
    if request.method == 'POST':
        payload = {
            'title':        request.form['title'].strip(),
            'description':  request.form.get('description', '').strip(),
            'category':     request.form.get('category', 'Other'),
            'prep_time':    int(request.form['prep_time'])  if request.form.get('prep_time')  else None,
            'cook_time':    int(request.form['cook_time'])  if request.form.get('cook_time')  else None,
            'servings':     int(request.form['servings'])   if request.form.get('servings')   else None,
            'ingredients':  request.form.get('ingredients',  '').strip(),
            'instructions': request.form.get('instructions', '').strip(),
            'image_url':    request.form.get('image_url',    '').strip(),
        }
        resp = http.put(f'{API_BASE_URL}/api/recipes/{id}', json=payload, headers=api_headers())
        if resp.status_code == 404:
            return render_template('404.html'), 404
        resp.raise_for_status()
        flash('Recipe updated!', 'success')
        return redirect(url_for('recipe_detail', id=id))

    resp = http.get(f'{API_BASE_URL}/api/recipes/{id}', headers=api_headers())
    if resp.status_code == 404:
        return render_template('404.html'), 404
    resp.raise_for_status()
    recipe = RecipeDTO(resp.json())
    return render_template('recipe_form.html', recipe=recipe, categories=CATEGORIES, action='Edit Recipe')


@app.route('/recipe/<int:id>/delete', methods=['POST'])
def delete_recipe(id):
    resp = http.delete(f'{API_BASE_URL}/api/recipes/{id}', headers=api_headers())
    if resp.status_code not in (200, 404):
        resp.raise_for_status()
    flash('Recipe deleted.', 'info')
    return redirect(url_for('index'))


@app.route('/api/categories', methods=['GET'])
def list_categories():
    rows = db.session.query(Recipe.category).distinct().all()
    categories = sorted([r[0] for r in rows if r[0]])
    return jsonify({'categories': categories})


if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
