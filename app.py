import urllib.parse
from flask import Flask, request, jsonify
import jwt
import urllib
import datetime
import requests
import json
from functools import wraps
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hehe muh secret'

# Connect to MongoDB
client = MongoClient("mongodb+srv://amch9605:" + urllib.parse.quote("Ambar@2024") + "@cluster0.tvir9.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")  # Update with your MongoDB URI
db = client['auth_db']
users_collection = db['users']

# Decorator for verifying the JWT token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one({'username': data['username']})
            if not current_user:
                raise ValueError("User not found")
        except Exception as e:
            return jsonify({'error': 'Token is invalid or expired!'}), 401

        kwargs['current_user'] = current_user
        return f(*args, **kwargs)
    return decorated

# Route for registering a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    if users_collection.find_one({'username': username}):
        return jsonify({'error': 'User already exists!'}), 400

    hashed_password = generate_password_hash(password)
    users_collection.insert_one({'username': username, 'password': hashed_password})
    return jsonify({'message': 'User registered successfully!'}), 201

# Route for logging in and getting a JWT token
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = users_collection.find_one({'username': username})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid credentials!'}), 401

    token = jwt.encode(
        {
            'username': username,
        },
        app.config['SECRET_KEY'],
        algorithm="HS256"
    )
    return jsonify({'token': token})

# Protected route
@app.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({
        'message': 'Welcome to the protected route!',
        'user': current_user['username']
    })




# routes per page - 
# Vault - Get recipes
# Pallete - Get similar recipes by category
# Profile - Just get user data
# Map - Get Recipe by region / subregion / continent
# Kitchen - Get Recipe by ingredients 

@app.route('/kitchen',methods=['POST'])
@token_required
def kitchen(current_user=None):
    data = request.get_json()
    ing_used = data.get("ingredients")
    print(ing_used) #string of ingredients used
    # ing_used = "cheese,beef,onion"
    payload = {
    "ingredientUsed": ing_used
    }
    params = {
        'page':'',
        'pageSize':'5'
    }

    res = requests.post("https://cosylab.iiitd.edu.in/recipe-search/recipesByIngredient",params=params,json=payload)
    resDict = res.json()
    _list = resDict.get('payload').get('data')
    id_list = [r.get('Recipe_id') for r in _list]
    return json.dumps(id_list)




@app.route('/map/<country>',methods=['GET']) #--done
@token_required
def map(country,current_user=None):
    endpoint = f"https://cosylab.iiitd.edu.in/recipe-search/sub-regions?searchText={country}&pageSize=6" #fetches the recipe id's country wise
    res = requests.get(endpoint)
    resDict = res.json()
    #get list of recipes
    _list = resDict.get('payload').get('data')
    #fetch all the recipe_ids
    id_list = [(r.get('Recipe_id'),r.get('Recipe_title'),r.get("img_url")) for r in _list]
  

    return json.dumps(id_list)

@app.route('/dishes/', methods=['GET'])
@token_required
def dishes(current_user=None):
    id_list = []

    for i in range(0, 6):
        id = 99930 + i
        res = requests.get(f"https://cosylab.iiitd.edu.in/recipe/{id}")

        # Check if the response status code is 200 (OK)
        if res.status_code == 200:
            try:
                resDict = res.json()  # Attempt to decode the JSON response
                if resDict:  # Ensure that the response is not empty
                    _list = resDict.get('payload')
                    if _list:  # Ensure 'payload' exists in the response
                        id_list.append((_list['Recipe_title'], _list['img_url'], _list['Sub_region'], _list['Recipe_id']))
                else:
                    print(f"Empty response body for ID {id}")
            except requests.exceptions.JSONDecodeError:
                # If the JSON decoding fails, log the error and the raw response body
                print(f"Failed to decode JSON for ID {id}")
                print(f"Response text: {res.text}")
        else:
            # If the request was not successful, log the status code
            print(f"Request failed for ID {id} with status code {res.status_code}")

    print(f"Fetched {len(id_list)} dishes.")
    return json.dumps(id_list)

@app.route('/recipe/<recipeId>') 
@token_required
def pallete(recipeId,current_user=None):
    endpoint = f"https://cosylab.iiitd.edu.in/recipe/{recipeId}"
    res = requests.get(endpoint)
    resDict = res.json()
    _list = resDict.get('payload')

    #front of the card
    image_url = _list['img_url']
    name = _list['Recipe_title']
    category = _list['Sub_region']
    recipe_url = _list['url']
    ins = ""
    for s in _list["instructions"]:
        ins += s

    #back half
    protein = _list['Protein (g)']
    carbs = _list['Carbohydrate, by difference (g)']
    fats = _list['Total lipid (fat) (g)']
    cals = _list['Calories']
    nrg = _list['Energy (kcal)']    


    return json.dumps([image_url,name,category,recipe_url,ins,protein,carbs,fats,cals,nrg])


@app.route('/search/<title>',methods=['GET'])
@token_required
def search(title,current_user=None):
    # data = request.get_json()
    
    params = {
        'recipepageSize' : '2',
        'searchText': title 
    }
    
    endpoint = f"https://cosylab.iiitd.edu.in/recipe-search/recipe"
    response = requests.get(endpoint,params=params)
    resDir = response.json().get('payload').get('data')
    match = resDir[0]
    id = match['Recipe_id']
    d = requests.get(f"https://cosylab.iiitd.edu.in/recipe/{id}")
    res = d.json()
    resDir  = res.get('payload')
    ingredients = resDir['ingredients']
    ins = []
    ins.append(id)
    ins.append(match['img_url'])
    ins.append(match['Recipe_title'])
    ins.append(match['Calories'])

    protein = match['Protein (g)']
    carbs = match['Carbohydrate, by difference (g)']
    fats = match['Total lipid (fat) (g)']
    nrg = match['Energy (kcal)']    

    ins.append(protein)
    ins.append(carbs)
    ins.append(fats)
    ins.append(nrg)


    for i in ingredients:
        ins.append(i['ingredient'])
    return json.dumps(ins)

    

@app.route('/rotd/')
@token_required
def rotd(current_user=None):
    endpoint = f"https://cosylab.iiitd.edu.in/recipe/recipeOftheDay"
    res = requests.get(endpoint)

    resDict = res.json()
    _list = resDict.get('payload')

    id = _list['Recipe_id']
    image_url = _list['img_url']
    name = _list['Recipe_title']
    cat = _list['Sub_region']
    cal = _list['Calories']

    return json.dumps([id,image_url,name,cat])



@app.route('/replace/<name>',methods=['GET'])
@token_required
def replace(name,current_user=None):
    params = {
        "name": name
    }

    res = requests.get("https://cosylab.iiitd.edu.in/api/entity/getentities",params=params)
    e = res.json()
    entity = e[0]
    e_id = entity['entity_id']
    pair = requests.get(f'https://cosylab.iiitd.edu.in/api/foodPairingAnalysis/{e_id}')

    return json.dumps(pair.json())


@app.route('/adv/',methods=['POST'])
@token_required
def adv(current_user=None):
    data = request.get_json()

    body = {
    "energyMin": int(data.get('energy')) - 50,
    "energyMax": data.get('energy'),
    "carbohydratesMin": 0,
    "carbohydratesMax": 500,
    "fatMin": 0,
    "fatMax": 50,
    "proteinMin": 0,
    "proteinMax": 2323
    }

    params = {"page":1,"pageSize":4}

    res = requests.post("https://cosylab.iiitd.edu.in/recipe-search/recipesByNutrition",params=params,data=body)
    resDir = res.json()
    payload = resDir.get('payload')
    d = payload.get('data')
    id_list = [(r.get('Recipe_id'),r.get('Recipe_title'),r.get("img_url")) for r in d]

    return json.dumps(id_list)

    



    


@app.route('/vault/')
@token_required
def vault():
    return "rando recipes for the home screen"

@app.route('/profile/')
@token_required
def profile():
    return "user's profile"

if __name__ == '__main__':
    app.run(debug=True)
