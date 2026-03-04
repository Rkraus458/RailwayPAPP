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


@app.route('/')
def index():
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

    return render_template(
        'index.html',
        recipes=recipes,
        categories=all_categories,
        category_icons=CATEGORY_ICONS,
        search=search,
        active_category=category,
    )


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


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
