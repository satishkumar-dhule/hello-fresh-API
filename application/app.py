import uuid
from datetime import datetime, timedelta
from functools import wraps
import jwt
from flask import Flask, jsonify, request, abort, make_response
from werkzeug.exceptions import NotFound
from werkzeug.security import generate_password_hash, check_password_hash
import application.models as models
import os

def create_app(config_name):
    config_name=str(config_name)
    app = Flask(__name__)

    config_module = f"application.config.{config_name.capitalize()}Config"
    app.config['SECRET_KEY']=os.environ.get('SECRET_KEY')

    app.config.from_object(config_module)

    from application.models import db, migrate

    # db.init_app(app)
    # migrate.init_app(app, db)


# app = Flask(__name__)
# config_module = f"application.config.{config_name.capitalize()}Config"
# 
# app.config.from_object(config_module)
# app.config['SECRET_KEY'] = 'Th1s1ss3cr3t'

    
    def token_required(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            token = None
            if 'x-access-tokens' in request.headers:
                token = request.headers['x-access-tokens']
                if not token:
                    app.logger.warning(f"valid token missing{' '.join(*args)}")
                    return jsonify({'message': 'a valid token is missing'})
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user = models.Users.select().where(models.Users.public_id == data['public_id']).get()
            except Exception as e:
                app.logger.warning(f"valid token missing {e}")
                return jsonify({'message': 'token is invalid'}), 403
            app.logger.info("token validation successful")
            return f(current_user, *args, **kwargs)
    
        return decorator

    
    @app.route('/api/v1/register', methods=['GET', 'POST'])
    def signup_user():
        data = request.get_json()
        app.logger.info('name' in data)
        app.logger.info('password' in data)
        app.logger.info(data)

        
        if 'name' in data and 'password' in data:
            try:
                hashed_password = generate_password_hash(data['password'], method='sha256')
                row = models.Users.create(public_id=uuid.uuid4(), name=data["name"], password=hashed_password, admin=False)
                app.logger.info(f"{row} created successfully")
                return jsonify({'message': f'{row.name} registered successfully'})
            except Exception as e:
                app.logger.error(f"{e}")
                return not_found(e, 403)
        else:
            return jsonify({'error': f'missing name and/or password in input.'}),422 
    
    
    @app.route('/api/v1/login', methods=['GET', 'POST'])
    def login_user():
        auth = request.authorization
    
        if not auth or not auth.username or not auth.password:
            app.logger.warning(
                make_response('could not verify', 401, {'WWW.Authentication': 'Basic realm: "login required"'}))
            app.logger.error("could not verify")
            return make_response('could not verify', 401, {'WWW.Authentication': 'Basic realm: "login required"'})

        app.logger.info(f"auth.username: {auth.username}")
        user = models.Users.select().where(models.Users.name == auth.username).first()
        app.logger.info(user)
        app.logger.info(f"{app.config['SECRET_KEY']} {user}")
    
        if user and check_password_hash(user.password, auth.password) :
            token = jwt.encode(
                {'public_id': str(user.public_id), 'exp': datetime.utcnow() + timedelta(minutes=30)},
                app.config['SECRET_KEY'])
            app.logger.info(f"token generated for user : {user}")
            return jsonify({'token': token})
        app.logger.warning(f"could not verify : {user}")
        return make_response({'error':'could not verify, check for valid credentials'}, 401, {'WWW.Authentication': 'Basic realm: "login required"'})
    
    
    @app.route('/api/v1/user', methods=['GET'])
    @token_required
    def get_all_users(user):
        users = models.Users.select()
        result = []
        for user in users:
            user_data = {'public_id': user.public_id, 'name': user.name, 'password': user.password, 'admin': user.admin}
            result.append(user_data)
        app.logger.info(f"get all users successful: {result}")
        return jsonify({'users': result, "meta": f"Logged in as : {user.name}"})
    
    
    # simple utility function to create tables
    def create_model_tables():
        try:
            with models.db:
                models.db.create_tables([models.RecipeClassification, models.Recipe, models.Ingredient, models.Customer,
                                        models.WeeklyMenuReview,
                                        models.WeeklyMenu, models.RecipeReview, models.WeeklyRecipeMap, models.Users])
                app.logger.info("model table creation successful")
        except Exception as e:
            app.logger.warning(e)
    
    
    create_model_tables()
    
    
    # error handling
    @app.errorhandler(404)
    def not_found(error=None, http_code=404):
        app.logger.warning(f"error: {error}, http_code: {http_code}")
        return make_response({
            'status': http_code,
            'url': request.url,
            'error': str(error)
        }), http_code
    
    
    # Endpoints
    
    @app.route('/api/v1/recipes', methods=['GET', 'POST'])
    @app.route('/api/v1/recipes/<int:page>', methods=['GET'])
    @app.route('/api/v1/recipes/id/<int:recipe_id>', methods=['GET', 'DELETE', 'PUT'])
    @token_required
    def recipes_endpoint(user, page=1, recipe_id=0):
        # get request
        if request.method == 'GET':
            per_page = 10
            query = models.Recipe.select().where(models.Recipe.is_publish).paginate(page, per_page) if recipe_id == 0 \
                else models.Recipe.select().where(models.Recipe.id == recipe_id)
            data = [i.serialize for i in query]
            if data:
                return make_response({'recipes': data, 'meta': {'page': page, 'per_page': per_page, 'page_url': request.url}}),200
            else:
                return not_found("Recipe does not exists",404)
        elif request.method == 'POST':  # post request
            # print(request.json)
            try:
                row = models.Recipe.create(**request.json)
            except Exception as e:
                app.logger.warning(f"{e}")
                return not_found(e)
            query = models.Recipe.select().where(
                models.Recipe.id == row.id,
            )
            data = [i.serialize for i in query]
            app.logger.info(f"{data}")
            return make_response({
                'Recipe': data,
                'meta': {'page_url': request.url}
            }), 201
    
        elif request.method == "DELETE":  # delete endpoint
            recipe = None
            try:
                recipe = models.Recipe.get(
                    models.Recipe.id == recipe_id
                )
            except Exception as e:
                app.logger.warning(f"recipe:{recipe}, {e}")
                return not_found(e, 404)
    
            if recipe and recipe.is_publish:
                recipe.is_publish = False
                recipe.save()
                return make_response(""), 204
            else:
                return not_found(NotFound("Recipe already deleted or does not exists"))
        elif request.method == "PUT":  # put endpoint
            try:
                c = models.Recipe.get(
                    models.Recipe.id == recipe_id
                )
            except Exception as e:
                return not_found(e, 400)
            if not request.json:
                abort(400)
            # print(request.json.items())
            try:
                for k, v in request.json.items():
                    if k in c.__dict__['__data__']:
                        setattr(c, k, v)
                    else:
                        app.logger.warning(f"'{k}' is not one of the attributes of {c}, ignoring {k}:{v}")
                c.save()
            except Exception as e:
                return not_found(e, 202)
            query = models.Recipe.select().where(
                models.Recipe.id == recipe_id,
            )
            data = [i.serialize for i in query]
            return make_response({
                'Recipe': data,
                'meta': {'page_url': request.url}
            }), 200
    
    
    @app.route('/api/v1/recipes-classification', methods=['GET', 'POST'])
    @app.route('/api/v1/recipes-classification/<int:page>', methods=['GET'])
    @app.route('/api/v1/recipes-classification/id/<int:recipe_classification_id>', methods=['GET', 'DELETE', 'PUT'])
    @token_required
    def recipes_classification_endpoint(user=None, page=1, recipe_classification_id=0):
        # get request
        if request.method == 'GET':
            per_page = 10
            try:
                query = models.RecipeClassification.select().where(
                    models.RecipeClassification.is_publish).paginate(
                    page, per_page) if recipe_classification_id == 0 else models.RecipeClassification.select().where(
                    models.RecipeClassification.id == recipe_classification_id)
            except Exception as e:
                return not_found(e, 404)
            data = [i.serialize for i in query]
            if data:
                return make_response(jsonify({
                    'recipes-classification': data,
                    'meta': {'page': page, 'per_page': per_page, 'page_url': request.url}
                })), 200
            else:
                return not_found("No records found", 404)
    
        elif request.method == 'POST':  # post request
            # print(request.json)
            try:
                row = models.RecipeClassification.create(**request.json)
            except Exception as e:
                return not_found(e, 400)
    
            query = models.RecipeClassification.select().where(
                models.RecipeClassification.id == row.id,
            )
            data = [i.serialize for i in query]
            return make_response(jsonify({
                'recipes-classification': data,
                'meta': {'page_url': request.url}
            })), 201
        elif request.method == "DELETE":  # delete endpoint
        
            try:
                recipeClassification = models.RecipeClassification.get(
                    models.RecipeClassification.id == recipe_classification_id,
                    models.RecipeClassification.is_publish
                )
            except Exception as e:
                return not_found(e, 404)
    
            if recipeClassification:
                recipeClassification.is_publish = False
                recipeClassification.save()
                return make_response(jsonify([recipeClassification.serialize])), 204
            else:
                return make_response(jsonify({
                    "Error": "The requested resource is no longer available at the "
                            "server and no forwarding address is known.",
                    "Status Code": 410,
                    "URL": request.url
                })), 410
    
        elif request.method == "PUT":  # put endpoint
            try:
                c = models.RecipeClassification.get(
                    models.RecipeClassification.id == recipe_classification_id
                )
            except Exception as e:
                return not_found(e, 400)
            if not request.json:
                abort(400)
            # print(request.json.items())
            try:
                for k, v in request.json.items():
                    if k in c.__dict__['__data__']:
                        setattr(c, k, v)
                    else:
                        app.logger.warning(f"'{k}' is not one of the attributes of {c}, ignoring {k}:{v}")
                c.save()
            except Exception as e:
                return not_found(e, 202)
            query = models.RecipeClassification.select().where(
                models.RecipeClassification.id == recipe_classification_id,
            )
            data = [i.serialize for i in query]
            return make_response(jsonify({
                'recipes-classification': data,
                'meta': {'page_url': request.url}
            })), 200
    
    
    @app.route('/api/v1/ingredient', methods=['GET', 'POST'])
    @app.route('/api/v1/ingredient/<int:page>', methods=['GET'])
    @app.route('/api/v1/ingredient/id/<int:ingredient_id>', methods=['GET', 'DELETE', 'PUT'])
    @token_required
    def ingredient_endpoint(user, page=1, ingredient_id=-1):
        # get request
        if request.method == 'GET':
            per_page = 10
            if ingredient_id == -1:
                query = models.Ingredient.select().paginate(page, per_page)
            else:
                query = models.Ingredient.select().where(models.Ingredient.id == ingredient_id)
            data = [i.serialize for i in query]
            if data:
                return make_response(jsonify({
                    'Ingredient': data,
                    'meta': {'page': page, 'per_page': per_page, 'page_url': request.url}
                })), 200
            else:
                # if no results are found.
                return make_response(jsonify({
                    "error": "No results found. Check url again",
                    "url": request.url,
                })), 404
    
        elif request.method == 'POST':  # post request
            try:
                row = models.Ingredient.create(**request.json)
                query = models.Ingredient.select().where(
                    models.Ingredient.id == row.id,
                )
                data = [i.serialize for i in query]
                return make_response(jsonify({
                    'Ingredient': data,
                    'meta': {'page_url': request.url}
                })), 201
            except Exception as e:
                return not_found(e, 409)
        elif request.method == "DELETE":  # delete endpoint
            try:
                ingredient = models.Ingredient.get(
                    models.Ingredient.id == ingredient_id
                )
            except Exception as e:
                return not_found(e, 404)
    
            if ingredient:
                ingredient.delete_instance()
                return make_response(jsonify({})), 204
    
            else:
                return (jsonify({
                    "Error": "The requested resource is no longer available at the "
                            "server and no forwarding address is known.",
                    "Status Code": 410,
                    "URL": request.url
                })), 410
    
        elif request.method == "PUT":  # put endpoint
            try:
                c = models.Ingredient.get(
                    models.Ingredient.id == ingredient_id
                )
            except Exception as e:
                return not_found(e, 404)
    
            if not request.json:
                abort(400)
            # print(request.json.items())
            try:
                for k, v in request.json.items():
                    if k in c.__dict__['__data__']:
                        setattr(c, k, v)
                    else:
                        app.logger.warning(f"'{k}' is not one of the attributes of {c}, ignoring {k}:{v}")
                c.save()
            except Exception as e:
                return not_found(e, 202)
    
            query = models.Ingredient.select().where(
                models.Ingredient.id == ingredient_id,
            )
            data = [i.serialize for i in query]
            return make_response(jsonify({
                'Ingredient': data,
                'meta': {'page_url': request.url}
            })), 200
    
    
    @app.route('/api/v1/recipe-review', methods=['GET', 'POST'])
    @app.route('/api/v1/recipe-review/<int:page>', methods=['GET'])
    @app.route('/api/v1/recipe-review/id/<int:recipe_review_id>', methods=['GET', 'DELETE', 'PUT'])
    @token_required
    def recipe_review_endpoint(user=None, page=1, recipe_review_id=0):
        # get request
        if request.method == 'GET':
            per_page = 10
            query = models.RecipeReview.select().where(models.RecipeReview.is_publish).paginate(page, per_page) \
                if recipe_review_id == 0 else models.RecipeReview.select().where(models.RecipeReview.id == recipe_review_id)
            data = [i.serialize for i in query]
            app.logger.info(f"data:{data}")
            if not data:
                return not_found(NotFound("No matching records found"), 404)
            return make_response({'recipe-review': data, 'meta': {'page': page,
                                                                'per_page': per_page,
                                                                'page_url': request.url}}), 200
        elif request.method == 'POST':  # post request
            # print(request.json)
            try:
                row = models.RecipeReview.create(**request.json)
            except Exception as e:
                return not_found(e, 409)
            query = models.RecipeReview.select().where(
                models.RecipeReview.id == row.id,
            )
            data = [i.serialize for i in query]
            app.logger.info(f"data:{data}")
            return make_response({
                'recipe-review': data,
                'meta': {'page_url': request.url}
            }), 201
    
        elif request.method == "DELETE":  # delete endpoint
        
            try:
                RecipeReview = models.RecipeReview.get(
                    models.RecipeReview.id == recipe_review_id
                )
            except Exception as e:
                return not_found(e, 404)
    
            if RecipeReview and RecipeReview.is_publish:
                RecipeReview.is_publish = False
                RecipeReview.save()
                return make_response(""), 204
            else:
                return not_found(NotFound("RecipeReview already deleted or does not exists"))
        elif request.method == "PUT":  # put endpoint
            try:
                c = models.RecipeReview.get(
                    models.RecipeReview.id == recipe_review_id
                )
            except Exception as e:
                return not_found(e, 400)
            if not request.json:
                abort(400)
            # print(request.json.items())
            try:
                for k, v in request.json.items():
                    if k in c.__dict__['__data__']:
                        setattr(c, k, v)
                    else:
                        app.logger.warning(f"'{k}' is not one of the attributes of {c}, ignoring {k}:{v}")
                c.save()
            except Exception as e:
                return not_found(e, 202)
            query = models.RecipeReview.select().where(
                models.RecipeReview.id == recipe_review_id,
            )
            data = [i.serialize for i in query]
            return make_response({
                'recipe-review': data,
                'meta': {'page_url': request.url}
            }), 200
    
    
    @app.route('/api/v1/weekly-menu-review', methods=['GET', 'POST'])
    @app.route('/api/v1/weekly-menu-review/<int:page>', methods=['GET'])
    @app.route('/api/v1/weekly-menu-review/id/<int:weekly_menu_review_id>', methods=['GET', 'DELETE', 'PUT'])
    @token_required
    def weekly_menu_review_endpoint(user=None, page=1, weekly_menu_review_id=0):
        # get request
        if request.method == 'GET':
            per_page = 10
            query = models.WeeklyMenuReview.select().where(models.WeeklyMenuReview.is_publish).paginate(page, per_page) \
                if weekly_menu_review_id == 0 else models.WeeklyMenuReview.select(). \
                where(models.WeeklyMenuReview.id == weekly_menu_review_id)
            data = [i.serialize for i in query]
            if not data:
                return not_found(NotFound("No matching records found"), 404)
            return make_response({'weekly-menu-review': data, 'meta': {'page': page,
                                                                    'per_page': per_page,
                                                                    'page_url': request.url}}), 200
        elif request.method == 'POST':  # post request
            # print(request.json)
            try:
                row = models.WeeklyMenuReview.create(**request.json)
            except Exception as e:
                return not_found(e, 409)
            query = models.WeeklyMenuReview.select().where(
                models.WeeklyMenuReview.id == row.id,
            )
            data = [i.serialize for i in query]
            return make_response({
                'weekly-menu-review': data,
                'meta': {'page_url': request.url}
            }), 201
    
        elif request.method == "DELETE":  # delete endpoint
        
            try:
                review_object = models.WeeklyMenuReview.get(
                    models.WeeklyMenuReview.id == weekly_menu_review_id
                )
            except Exception as e:
                return not_found(e, 404)
    
            if review_object and review_object.is_publish:
                review_object.is_publish = False
                review_object.save()
                return make_response(""), 204
            else:
                return not_found(NotFound("RecipeReview already deleted or does not exists"))
        elif request.method == "PUT":  # put endpoint
            try:
                c = models.WeeklyMenuReview.get(
                    models.WeeklyMenuReview.id == weekly_menu_review_id
                )
            except Exception as e:
                return not_found(e, 400)
            if not request.json:
                abort(400)
            # print(request.json.items())
            try:
                for k, v in request.json.items():
                    if k in c.__dict__['__data__']:
                        setattr(c, k, v)
                    else:
                        app.logger.warning(f"'{k}' is not one of the attributes of {c}, ignoring {k}:{v}")
                c.save()
            except Exception as e:
                return not_found(e, 202)
            query = models.WeeklyMenuReview.select().where(
                models.WeeklyMenuReview.id == weekly_menu_review_id,
            )
            data = [i.serialize for i in query]
            return make_response({
                'weekly-menu-review': data,
                'meta': {'page_url': request.url}
            }), 200
    
    
    @app.route('/api/v1/customer', methods=['GET', 'POST'])
    @app.route('/api/v1/customer/<int:page>', methods=['GET'])
    @app.route('/api/v1/customer/id/<int:customer_id>', methods=['GET', 'DELETE', 'PUT'])
    @token_required
    def customer_endpoint(user=None, page=1, customer_id=0):
        # get request
        if request.method == 'GET':
            customer = models.Customer.select() if customer_id == 0 else models.Customer.select(). \
                where(models.Customer.id == customer_id)
            result = []
            for user in customer:
                user_data = {"id": user.id, 'public_id': user.public_id, 'name': user.name, 'password': user.password,
                            'admin': user.admin,
                            "is_active": user.is_active}
                result.append(user_data)
            return make_response({'users': result, "meta": f"Logged in as : {user.name}"}), 200
        elif request.method == 'POST':  # post request
            # print(request.json)
            try:
                data = request.get_json()
                hashed_password = generate_password_hash(data['password'], method='sha256')
                row = models.Customer.create(public_id=uuid.uuid4(), name=data["name"], password=hashed_password,
                                            admin=False, is_active=True)
                return jsonify({'message': f'{row.name} registered successfully'})
            except Exception as e:
                return not_found(e, 409)
    
        elif request.method == "DELETE":  # delete endpoint
        
            try:
                Customer = models.Customer.get(
                    models.Customer.id == customer_id
                )
            except Exception as e:
                return not_found(e, 404)
    
            if Customer and Customer.is_active:
                Customer.is_active = False
                Customer.save()
                return make_response(""), 204
            else:
                return not_found(NotFound("Customer already deleted or does not exists"))
        elif request.method == "PUT":  # put endpoint
            try:
                c = models.Customer.get(
                    models.Customer.id == customer_id
                )
            except Exception as e:
                return not_found(e, 400)
            if not request.json:
                abort(400)
            # print(request.json.items())
            try:
                for k, v in request.json.items():
                    if k in c.__dict__['__data__']:
                        setattr(c, k, v)
                    else:
                        app.logger.warning(f"'{k}' is not one of the attributes of {c}, ignoring {k}:{v}")
                c.save()
            except Exception as e:
                return not_found(e, 202)
            query = models.Customer.select().where(
                models.Customer.id == customer_id,
            )
            data = [i.serialize for i in query]
            return make_response({
                'customer': data,
                'meta': {'page_url': request.url}
            }), 200
    
    
    @app.route('/api/v1/weekly-menu/id/<int:weekly_menu_id>/recipe/id/<int:recipe_id>', methods=['POST', 'DELETE'])
    @token_required
    def add_remove_recipe_to_weekly_menu_endpoint(user, weekly_menu_id, recipe_id):
        if request.method == 'POST':
            try:
                recipe = models.Recipe.get(models.Recipe.id == recipe_id)
                weekly_menu = models.WeeklyMenu.get(models.WeeklyMenu.id == weekly_menu_id)
                if not recipe or not weekly_menu:
                    return NotFound(f"no records found matching for given conditions, check recipe id and weekly menu id")
                success, error = weekly_menu.addRecipe(weekly_menu, recipe)
                if not success:
                    return make_response(jsonify({"msg": str(error)})), 409
                query = models.WeeklyMenu.select().where(
                    models.WeeklyMenu.id == weekly_menu.id,
                )
                data = [i.serialize for i in query]
                return make_response({
                    'WeeklyMenu': data,
                    'meta': {'page_url': request.url}
                }), 201
            except Exception as e:
                print(e)
                return not_found(e)
        elif request.method == 'DELETE':
            try:
                recipe = models.Recipe.get(models.Recipe.id == recipe_id)
                weekly_menu = models.WeeklyMenu.get(models.WeeklyMenu.id == weekly_menu_id)
                if not recipe or not weekly_menu:
                    return NotFound(
                        f"no records found matching for given conditions, check recipe id and weekly menu id")
                success, error = weekly_menu.removeRecipe(weekly_menu, recipe)
                if not success:
                    return NotFound(error)
                query = models.WeeklyMenu.select().where(
                    models.WeeklyMenu.id == weekly_menu.id,
                )
                data = [i.serialize for i in query]
                return make_response({
                    'WeeklyMenu': data,
                    'meta': {'page_url': request.url}
                }), 202
            except Exception as e:
                return not_found(e)
    
    
    @app.route('/api/v1/weekly-menu', methods=['GET', 'POST'])
    @app.route('/api/v1/weekly-menu/<int:page>', methods=['GET'])
    @app.route('/api/v1/weekly-menu/id/<int:weekly_menu_id>', methods=['GET', 'DELETE', 'PUT'])
    @token_required
    def weekly_menu_endpoint(user, page=1, weekly_menu_id=0):
        # get request
        if request.method == 'GET':
            per_page = 10
            query = models.WeeklyMenu.select().where(models.WeeklyMenu.is_publish).paginate(page,
                                                                                        per_page) if weekly_menu_id == 0 \
                else models.WeeklyMenu.select().where(models.WeeklyMenu.id == weekly_menu_id)
            data = [i.serialize for i in query]
            # print(data)
            if not data:
                return not_found(NotFound("No matching records found"), 404)
            return make_response({'weekly-menu': data, 'meta': {'page': page, 'per_page': per_page,
                                                                'page_url': request.url}}), 200
        elif request.method == 'POST':  # post request
            # print(request.json)
            try:
                row = models.WeeklyMenu.create(**request.json)
            except Exception as e:
                return not_found(e, 409)
            query = models.WeeklyMenu.select().where(
                models.WeeklyMenu.id == row.id,
            )
            data = [i.serialize for i in query]
            return make_response({
                'WeeklyMenu': data,
                'meta': {'page_url': request.url}
            }), 201
    
        elif request.method == "DELETE":  # delete endpoint
        
            try:
                recipe = models.WeeklyMenu.get(
                    models.WeeklyMenu.id == weekly_menu_id
                )
            except Exception as e:
                return not_found(e, 404)
    
            if recipe and recipe.is_publish:
                recipe.is_publish = False
                recipe.save()
                return make_response(""), 204
            else:
                return not_found(NotFound("WeeklyMenu already deleted or does not exists"))
        elif request.method == "PUT":  # put endpoint
            try:
                c = models.WeeklyMenu.get(
                    models.WeeklyMenu.id == weekly_menu_id
                )
            except Exception as e:
                return not_found(e, 400)
            if not request.json:
                abort(400)
            # print(request.json.items())
            try:
                for k, v in request.json.items():
                    if k in c.__dict__['__data__']:
                        setattr(c, k, v)
                    else:
                        app.logger.warning(f"'{k}' is not one of the attributes of {c}, ignoring {k}:{v}")
                c.save()
            except Exception as e:
                return not_found(e, 202)
            query = models.WeeklyMenu.select().where(
                models.WeeklyMenu.id == weekly_menu_id,
            )
            data = [i.serialize for i in query]
            return make_response({
                'WeeklyMenu': data,
                'meta': {'page_url': request.url}
            }), 204
    return app
    
# if __name__ == '__main__':
    # app.run(debug=True)
# 