from flask import Flask, render_template, jsonify, request
from scripts.mock_llm_api import llm_api
import lancedb
import pandas as pd

uri = "data/lancedb"
db = lancedb.connect(uri)

def recipe_to_hash(recipe):
    return recipe_to_fancy(sorted(recipe))

def recipe_to_fancy(recipe):
    v = recipe[0]
    for r in recipe[1:]: v +=  f" + {r}"
    return v

# Set initial entries in items vector database
def _reset_tables():
    items = {
        'Fire': {
            'description': "Strength: 10\nCost: 300\nCategory: Element",
            'recipe': ['Wood', 'Spark'],
        },
        'Rust': {
            'description': "Strength: 7\nCost: 30\nCategory: Metal",
            'recipe': ['Copper', 'Oxygen'],
        },
        'Water': {
            'description': "Strength: 3\nCost: 10\nCategory: Element",
            'recipe': ['Hydrogen', 'Oxygen'],
        },
        'Poisonous Gas': {
            'description': "Strength: 20\nCost: 100\nCategory: Weapon",
            'recipe': ['Gas', 'Poison'],
        }
    }
    item_names = items.keys()
    descriptions = [item['description'] for item in items.values()]
    recipes = [recipe_to_hash(item['recipe']) for item in items.values()]
    vectors = [llm_api.embedding_request(recipe_to_fancy(item['recipe'])) for item in items.values()]

    df = pd.DataFrame({
        "item": item_names, 
        "vector": vectors, 
        "description": descriptions,
        "recipe": recipes,
        })
    db.create_table("items", mode="overwrite", data=df)

if not db.table_names():
    print("No DB set up, creating initial tables")
    _reset_tables()

app = Flask(__name__)

@app.route("/")
def hello_world():
    table = db.open_table("items")
    return render_template(
        'index.html', 
        items=table.to_pandas()['item'].values.tolist(),
        recipes=table.to_pandas()['recipe'].values.tolist(),
        )


@app.route('/generate')
def generate():
    item_1 = request.args.get('item_1', type=str)
    item_2 = request.args.get('item_2', type=str)
    recipe = [item_1, item_2]

    # Check if recipe already exists.
    existing_item = try_get_item_exists('recipe', recipe_to_hash(recipe))
    if existing_item is not None:
        return jsonify(
            result=existing_item,
            info="Recipe already exists.",
            new_item_created=False,
            new_item_recipe="",
            )

    # Create recipe embedding
    recipe_embed = llm_api.embedding_request(recipe_to_fancy(recipe))
    n_nearest_recipes = find_n_nearest_items(recipe_embed, n=3)

    # Create example prompt information.
    examples_prompt = build_example_prompt(n_nearest_recipes, 'recipe', 'item')

    # Generate combination
    prompt_template = open("prompt_templates/basic_prompt.txt").read().strip()
    prompt = prompt_template.format(
        examples=examples_prompt,
        item_1=item_1,
        item_2=item_2,
        )
    item_combined = llm_api.completion_request(prompt, max_tokens=30).strip().split('\n')[0]

    # Check if item already exists.
    existing_item = try_get_item_exists('item', item_combined)
    if existing_item is not None:
        return jsonify(
            result=existing_item,
            info="Generated item already exists.",
            new_item_created=False,
            new_item_recipe="",
            )

    # Create example prompt information.
    examples_prompt = build_example_prompt(n_nearest_recipes, 'item', 'description')

    # Generate description for combination
    prompt_template = open("prompt_templates/basic_description_prompt.txt").read().strip()
    prompt = prompt_template.format(
        examples=examples_prompt,
        item=item_combined,
        )
    description = llm_api.completion_request(prompt, max_tokens=100)

    # Add result to vector database
    table = db.open_table("items")
    table.add(pd.DataFrame([{
        "item": item_combined,
        "vector": recipe_embed,
        "description": description,
        "recipe": recipe_to_hash(recipe),
        }]))

    info = "!NEW ITEM FOUND!\n---\nMost similar recipes were:\n"
    for i in n_nearest_recipes.index:
        data = n_nearest_recipes.iloc[i]
        info += data['recipe'] + '\n'

    return jsonify(
        result=item_combined,
        info=info,
        new_item_created=True,
        new_item_recipe=recipe_to_fancy(recipe),
        )


@app.route('/get_item_info')
def get_item_info():
    item = request.args.get('item', type=str)
    table = db.open_table("items")
    
    # Get description
    # TODO: Important! This retrieves the whole database, which is very inefficient
    # You may be tempted to do something like
    #   df = table.search(llm_api.embedding_request(item)).limit(1).to_df()
    #   description = df['description'].values.tolist()[0]
    # instead. However, LanceDB is a bit unstable and will occasionally crash if you do this
    # The ideal setup would be to have a standard SQL database for this lookup
    df = table.to_pandas()
    item_selected = df[df["item"] == item]

    return jsonify(
        description=item_selected['description'].values[0],
        recipe=item_selected['recipe'].values[0],
    )

def try_get_item_exists(key, value):
    table = db.open_table("items")
    df = table.to_pandas()
    item_selected = df[df[key] == value]
    return None if len(item_selected) == 0 else item_selected['item'].values[0]

def find_n_nearest_items(recipe_embedded, n=5):
    table = db.open_table("items")
    n_nearest_items = table.search(recipe_embedded).limit(n).to_df()
    return n_nearest_items

def build_example_prompt(examples_df, input_key, output_key):
    examples_prompt = ""
    examples_prompt_template = open("prompt_templates/example_subprompt.txt").read().strip()
    last_index = len(examples_df) - 1
    for i in examples_df.index:
        data = examples_df.iloc[i]
        examples_prompt += examples_prompt_template.format(
            input=data[input_key],
            output=data[output_key],
        ) + ("\n\n" if i != last_index else "\n")
    return examples_prompt
