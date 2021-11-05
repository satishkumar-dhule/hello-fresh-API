import datetime
import json
from application import *
import application
from application.models import Users,db
import pytest
import jwt
import os
 

@pytest.fixture
def client():
    app = application.app.create_app("Development")

    with app.test_client() as client:
        # with app.app_context():
            # init_db()
        yield client




def getLoginToken():
    """Login helper function"""
    user = Users.get(Users.name == 'user')
    token = jwt.encode(
        {'public_id': str(user.public_id), 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
        os.getenv('SECRET_KEY'))
    return token


auth_token = getLoginToken()
mock_request_headers = {"Content-Type": "application/json", "x-access-tokens": auth_token}


def test_root_404(client):
    url = '/'
    response = client.get(url)
    print(response.data)
    assert response.status_code == 404


def test_recipe(client):
    url = '/api/v1/recipes'
    response = client.get(url, headers=mock_request_headers)
    assert response.status_code == 200
    url = '/api/v1/recipes'

    mock_request_data = {
        "classification": 4,
        "cook_time": "15",
        "description": "Maggie",
        "directions": "Boil and Enjoy",
        "is_publish": "True",
        "num_of_servings": "2",
        "nutrition": {"Energy (kJ)": "1264kJ"},
        "recipe_name": "Maggie"
    }

    response = client.post(url, data=json.dumps(mock_request_data), headers=mock_request_headers)
    res = json.loads(response.data.decode())
    id = res["Recipe"][0]["id"]
    assert response.status_code == 201

    url = f'/api/v1/recipes/id/{id}'
    response = client.get(url, headers=mock_request_headers)
    assert response.status_code == 200

    url = f'/api/v1/recipes/id/{id}'
    response = client.delete(url, headers=mock_request_headers)
    assert response.status_code == 204


def test_ingredient(client):
    """Get all"""
    url = 'api/v1/ingredient'
    response = client.get(url, headers=mock_request_headers)
    assert response.status_code == 200

    '''post'''
    url = '/api/v1/ingredient'
    mock_request_data = {
        "ingredient_name": "makrut lime leaves",
        "unit": "leaves",
        "count": "2",
        "recipe": "7"

    }
    response = client.post(url, data=json.dumps(mock_request_data), headers=mock_request_headers)
    res = json.loads(response.data.decode())
    print(res)
    id = res["Ingredient"][0]["id"]
    assert response.status_code == 201

    '''get by id'''
    url = f'/api/v1/ingredient/id/{id}'
    response = client.get(url, headers=mock_request_headers)
    assert response.status_code == 200

    '''delete by id'''
    url = f'/api/v1/ingredient/id/{id}'
    response = client.delete(url, headers=mock_request_headers)
    assert response.status_code == 204


def test_classification(client):
    """Get all"""
    url = 'api/v1/recipes-classification'
    response = client.get(url, headers=mock_request_headers)
    assert response.status_code == 200

    '''post'''
    url = '/api/v1/recipes-classification'
    mock_request_data = {
        "is_publish": "True",
        "name": "Meat & Veggis"
    }
    response = client.post(url, data=json.dumps(mock_request_data), headers=mock_request_headers)
    res = json.loads(response.data.decode())
    print(res)
    id = res["recipes-classification"][0]["id"]
    assert response.status_code == 201

    '''get by id'''
    url = f'/api/v1/recipes-classification/id/{id}'
    response = client.get(url, headers=mock_request_headers)
    assert response.status_code == 200

    '''delete by id'''
    url = f'/api/v1/recipes-classification/id/{id}'
    response = client.delete(url, headers=mock_request_headers)
    assert response.status_code == 204


def test_user(client):
    """Get all"""
    url = '/api/v1/user'
    response = client.get(url, headers=mock_request_headers)
    assert response.status_code == 200

    '''post login to user'''
    url = '/api/v1/login'
    from requests.auth import _basic_auth_str
    
    mock_request_headers['Authorization'] =  _basic_auth_str("user", "password")
    response = client.post(url, headers=mock_request_headers)
    assert response.status_code == 200 
    print(response.status_code )

    # checking if token we have got from above is valid
    if  response.status_code==200:
        res = json.loads(response.data.decode())
        token = res["token"]
        url = '/api/v1/user'
        response = client.get(url, headers={"x-access-tokens": token, "Content-Type": "application/json"})
        assert response.status_code == 200
