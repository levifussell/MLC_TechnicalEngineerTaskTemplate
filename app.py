from flask import Flask, render_template, jsonify, request
from scripts.mock_llm_api import llm_api
import lancedb
import pandas as pd

uri = "data/lancedb"
db = lancedb.connect(uri)

# Set initial entries in items vector database
def _reset_tables():
    items = [item for item in ['Fire', 'Earth', 'Water', 'Wind']]
    descriptions = ["Strength: 10\nCost: 300\nCategory: Element", 
                    "Strength: 7\nCost: 100\nCategory: Element",
                    "Strength: 3\nCost: 50\nCategory: Element",
                    "Strength: 1\nCost: 10\nCategory: Element"
    ]
    vectors = [llm_api.embedding_request(item) for item in ['Fire', 'Earth', 'Water', 'Wind']]

    df = pd.DataFrame({"item": items, "vector": vectors, "description": descriptions})
    db.create_table("items", mode="overwrite", data=df)

if not db.table_names():
    print("No DB set up, creating initial tables")
    _reset_tables()

app = Flask(__name__)

@app.route("/")
def hello_world():
    table = db.open_table("items")
    return render_template('index.html', items=table.to_pandas()['item'].values.tolist())


@app.route('/generate')
def generate():
    item_1 = request.args.get('item_1', type=str)
    item_2 = request.args.get('item_2', type=str)
    
    # Generate prompt embedding
    embedding_prompt_template = open("prompt_templates/basic_embedding_prompt.txt").read().strip()
    embeddding_prompt = embedding_prompt_template.format(item_1=item_1, item_2=item_2)
    prompt_embedding = llm_api.embedding_request(embeddding_prompt)

    # Generate combination
    prompt_template = open("prompt_templates/basic_prompt.txt").read().strip()
    prompt = prompt_template.format(item_1=item_1, item_2=item_2)
    combination = llm_api.completion_request(prompt, max_tokens=30)

    # Generate description for combination
    prompt_template = open("prompt_templates/basic_description_prompt.txt").read().strip()
    prompt = prompt_template.format(item=combination)
    description = llm_api.completion_request(prompt, max_tokens=100)

    # Add result to vector database
    table = db.open_table("items")
    table.add(pd.DataFrame([{"item": combination, "vector": llm_api.embedding_request(combination), "description": description}]))

    return jsonify(result=combination)


@app.route('/get_description')
def get_description():
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
    description = df[df["item"] == item]["description"].values[0]

    return jsonify(result=description)
