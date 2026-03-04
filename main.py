from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Railway provides DATABASE_URL for PostgreSQL; fall back to SQLite locally
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///cookbook.db')
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
    prep_time    = db.Column(db.Integer)   # minutes
    cook_time    = db.Column(db.Integer)   # minutes
    servings     = db.Column(db.Integer)
    ingredients  = db.Column(db.Text)      # newline-separated
    instructions = db.Column(db.Text)      # newline-separated steps
    image_url    = db.Column(db.String(500))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

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

    query = Recipe.query
    if search:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f'%{search}%'),
                Recipe.description.ilike(f'%{search}%'),
                Recipe.ingredients.ilike(f'%{search}%'),
            )
        )
    if category:
        query = query.filter(Recipe.category == category)

    recipes        = query.order_by(Recipe.created_at.desc()).all()
    all_categories = db.session.query(Recipe.category).distinct().all()
    all_categories = sorted([c[0] for c in all_categories if c[0]])

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


@app.route('/api/recipes/<int:id>', methods=['DELETE'])
def delete_recipe(id):
    recipe = db.session.get(Recipe, id)
    if recipe is None:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(recipe)
    db.session.commit()
    return jsonify({'message': 'Recipe deleted'})


@app.route('/api/categories', methods=['GET'])
def list_categories():
    rows = db.session.query(Recipe.category).distinct().all()
    categories = sorted([r[0] for r in rows if r[0]])
    return jsonify({'categories': categories})


def seed_sample_recipes():
    if Recipe.query.count() > 0:
        return
    samples = [
        {
            'title':        'Spaghetti Carbonara',
            'description':  'A classic Italian pasta dish made with eggs, cheese, pancetta, and pepper. Rich, creamy, and incredibly satisfying.',
            'category':     'Dinner',
            'prep_time':    10,
            'cook_time':    20,
            'servings':     4,
            'ingredients':  '400g spaghetti\n200g pancetta or guanciale, diced\n4 large eggs\n100g Pecorino Romano, grated\n100g Parmesan, grated\n2 cloves garlic\nFreshly ground black pepper\nSalt',
            'instructions': 'Bring a large pot of heavily salted water to boil and cook spaghetti until al dente.\nFry pancetta in a large skillet over medium heat until crispy.\nWhisk eggs with most of the grated cheese and plenty of black pepper in a bowl.\nReserve 1 cup of pasta water before draining.\nRemove pan from heat, add drained pasta and toss to coat.\nQuickly add egg mixture, tossing constantly and adding pasta water a splash at a time to create a creamy sauce.\nServe immediately with remaining cheese and extra black pepper.',
            'image_url':    'https://images.unsplash.com/photo-1608756687911-aa1599ab3bd9?w=800',
        },
        {
            'title':        'Classic Chocolate Chip Cookies',
            'description':  'Perfectly chewy on the inside, slightly crispy on the edges. The quintessential comfort cookie.',
            'category':     'Dessert',
            'prep_time':    15,
            'cook_time':    12,
            'servings':     24,
            'ingredients':  '2 1/4 cups all-purpose flour\n1 tsp baking soda\n1 tsp salt\n1 cup (2 sticks) butter, softened\n3/4 cup granulated sugar\n3/4 cup packed brown sugar\n2 large eggs\n2 tsp vanilla extract\n2 cups chocolate chips',
            'instructions': 'Preheat oven to 375°F (190°C) and line baking sheets with parchment paper.\nWhisk together flour, baking soda, and salt in a bowl.\nBeat butter and both sugars until light and fluffy, about 3 minutes.\nAdd eggs one at a time, then vanilla, and beat well.\nGradually mix in flour mixture until just combined.\nStir in chocolate chips by hand.\nDrop rounded tablespoons onto prepared sheets, 2 inches apart.\nBake 9–11 minutes until edges are golden but centers look slightly underdone.\nCool on sheets 2 minutes, then transfer to a wire rack.',
            'image_url':    'https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=800',
        },
        {
            'title':        'Greek Salad',
            'description':  'A fresh, vibrant salad packed with Mediterranean flavors. Perfect as a light lunch or side dish.',
            'category':     'Salad',
            'prep_time':    15,
            'cook_time':    0,
            'servings':     4,
            'ingredients':  '1 English cucumber, cut into chunks\n4 Roma tomatoes, quartered\n1 red onion, thinly sliced\n1 cup Kalamata olives\n200g feta cheese, cubed\n1 green bell pepper, sliced\n3 tbsp extra-virgin olive oil\n1 tbsp red wine vinegar\n1 tsp dried oregano\nSalt and pepper to taste',
            'instructions': 'Cut cucumber, tomatoes, onion, and pepper into bite-sized pieces.\nCombine all vegetables in a large bowl.\nScatter olives and feta cheese over the top.\nWhisk together olive oil, red wine vinegar, oregano, salt, and pepper.\nDrizzle dressing over salad and toss gently.\nLet sit 5 minutes before serving so flavors meld.',
            'image_url':    'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800',
        },
        {
            'title':        'Thai Green Curry',
            'description':  'A fragrant, creamy Thai curry with tender chicken and vegetables. Aromatic and full of complex flavors.',
            'category':     'Dinner',
            'prep_time':    20,
            'cook_time':    25,
            'servings':     4,
            'ingredients':  '2 tbsp green curry paste\n400ml coconut milk\n300g chicken breast, sliced thin\n2 zucchini, sliced\n1 cup green beans, trimmed\n1 red bell pepper, sliced\n2 tbsp fish sauce\n1 tbsp brown sugar\n1 cup fresh Thai basil leaves\n3 kaffir lime leaves, torn\n1 tbsp vegetable oil\nJasmine rice, to serve',
            'instructions': 'Heat oil in a wok over medium-high heat.\nFry curry paste 1–2 minutes until fragrant.\nAdd half the coconut milk and stir to combine.\nAdd chicken and cook until sealed on all sides.\nAdd remaining coconut milk, vegetables, fish sauce, and sugar.\nSimmer 10–15 minutes until vegetables are tender and chicken is cooked through.\nStir in kaffir lime leaves and most of the basil.\nAdjust seasoning with fish sauce or sugar.\nServe over jasmine rice, garnished with remaining basil.',
            'image_url':    'https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=800',
        },
        {
            'title':        'Avocado Toast with Poached Eggs',
            'description':  'A vibrant, nutritious breakfast that comes together in minutes. Creamy avocado on crusty sourdough topped with perfectly poached eggs.',
            'category':     'Breakfast',
            'prep_time':    10,
            'cook_time':    5,
            'servings':     2,
            'ingredients':  '2 thick slices sourdough bread\n2 ripe avocados\n2 large eggs\n1 tbsp white wine vinegar\nJuice of half a lemon\nRed pepper flakes\nFlaky sea salt\nFreshly ground black pepper',
            'instructions': 'Toast sourdough until golden and crispy.\nHalve and pit avocados, scoop flesh into a bowl.\nMash with lemon juice, salt, and pepper to your preferred texture.\nBring a small saucepan of water to a gentle simmer and add vinegar.\nCreate a gentle swirl, crack an egg into a small cup, and slide into the center.\nPoach 3–4 minutes for a runny yolk, then remove with a slotted spoon.\nRepeat for the second egg.\nSpread mashed avocado on each toast.\nTop with a poached egg, flaky salt, black pepper, and red pepper flakes.',
            'image_url':    'https://images.unsplash.com/photo-1525351484163-7529414344d8?w=800',
        },
    ]
    for sample in samples:
        db.session.add(Recipe(**sample))
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_sample_recipes()

if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
