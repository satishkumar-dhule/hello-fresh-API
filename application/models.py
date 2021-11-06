from enum import unique
import statistics
from datetime import datetime
from peewee import *
from playhouse.hybrid import hybrid_property
from playhouse.postgres_ext import PostgresqlExtDatabase, HStoreField
from playhouse.shortcuts import model_to_dict
# from flask import current_app, g

import os

pg_database=os.environ['POSTGRES_DB']
pg_user=os.environ['POSTGRES_USER']
pg_password=os.environ['POSTGRES_PASSWORD']
pg_host=os.environ['POSTGRES_HOSTNAME']


db = PostgresqlExtDatabase(pg_database, register_hstore=True,
                           user=pg_user,
                           password=pg_password,
                           host=pg_host,
                           )

def migrate(db):
    pass


class BaseModel(Model):
    """Basemodel for peewee"""

    class Meta:
        database = db


class RecipeClassification(BaseModel):
    """RecipeClassification Model"""
    name = CharField(max_length=35,unique=True)
    is_publish = BooleanField(default=False)

    @property
    def serialize(self):
        data = {
            'id': self.id,
            'name': self.name,
            'is_publish': self.is_publish

        }
        return data

    def __str__(self):
        return self.id + ":" + self.name


class Recipe(BaseModel):
    """Recipe Model"""
    delete_recursive = True
    recipe_name = CharField(default='')
    description = TextField(default='')
    num_of_servings = SmallIntegerField(default=2)
    cook_time = SmallIntegerField(default=30)
    directions = TextField(default='')
    is_publish = BooleanField(default=False)
    nutrition = HStoreField()
    classification = ForeignKeyField(RecipeClassification, backref='backref_recipe_classification')

    @hybrid_property
    def ingredients(self):
        return [i.serialize for i in Ingredient.select().where(Ingredient.recipe == self)]

    @property
    def serialize(self):
        data = {'ingredients': self.ingredients}
        data.update(model_to_dict(self))
        return data

    def __str__(self):
        return "{} : {} ".format(
            self.id,
            self.recipe_name,
        )


class Ingredient(BaseModel):
    """Ingredients Model"""
    ingredient_name = CharField(default='')
    unit = CharField(default='')
    count = IntegerField(default=0)
    recipe = ForeignKeyField(Recipe, backref='backref_recipe')

    class Meta:
        indexes = (
            (("ingredient_name", "recipe"), True),
        )

    @classmethod
    def getIngredientByRecipe(cls, recipe_id):
        Ingredient.select().where(Ingredient.recipe.id == recipe_id)

    @property
    def serialize(self):
        data = {
            'id': self.id,
            'ingredient_name': str(self.ingredient_name).strip(),
            'unit': str(self.unit).strip(),
            'count': str(self.count).strip(),
            'recipe': str(self.recipe).strip(),
        }
        return data


class WeeklyMenu(BaseModel):
    """WeeklyMenu Model"""
    week_number = SmallIntegerField(unique=True)
    is_publish = BooleanField(default=True)

    @property
    def averageScore(self):
        try:
            return statistics.mean((i.score for i in WeeklyMenuReview.select().where(WeeklyMenuReview.menu == self)))
        except statistics.StatisticsError as e:
            return 0

    @property
    def recipes(self):
        return [i.serialize for i in WeeklyRecipeMap.select().where(WeeklyRecipeMap.week == self)]

    @classmethod
    def addRecipe(cls, weekly_menu, recipe):
        """Add recipe to weekly menu"""
        if WeeklyRecipeMap.select().where(WeeklyRecipeMap.week == weekly_menu, WeeklyRecipeMap.recipe == recipe):
            return False, f"{recipe} is already part of weekly menu {weekly_menu}"
        recipe_map = WeeklyRecipeMap()
        recipe_map.recipe = recipe
        try:
            recipe_map.week = weekly_menu

            recipe_map.save()
            return True, None
        except Exception as e:
            return False, e

    @classmethod
    def removeRecipe(cls, weekly_menu, recipe):
        """RemoveRecipe from weekly Menu"""
        recipe_map = WeeklyRecipeMap.get(WeeklyRecipeMap.recipe == recipe, WeeklyRecipeMap.week == weekly_menu)
        try:
            recipe_map.delete_instance()
            return True, None
        except Exception as e:
            return False, e

    @property
    def serialize(self):
        data = model_to_dict(self)
        data.update({"recipes": self.recipes, "score": self.averageScore})
        return data


class WeeklyRecipeMap(BaseModel):
    """M:M relation for weekly Menu and Recipes"""
    week = ForeignKeyField(WeeklyMenu)
    recipe = ForeignKeyField(Recipe)

    @property
    def serialize(self):
        return model_to_dict(self)


class Users(BaseModel):
    public_id = UUIDField()
    name = CharField(unique=True)
    password = CharField()
    admin = BooleanField(default=False)

    @property
    def serialize(self):
        data = model_to_dict(self)
        return data



    def __str__(self):
        return f"id:{self.id}, name:{self.name}"


class Customer(Users):
    """Cusotmer model for tracking feedbacks and reviews(Recipes and Weekly Menu)"""
    is_active = BooleanField(default=False)

    @property
    def serialize(self):
        data = {
            'id': self.id,
            'is_active': self.is_active,
            'name': self.name,
            'admin': self.admin,

        }
        return data


class RecipeReview(BaseModel):
    """1:M relation for recipe reviews"""
    review = TextField()
    recipe = ForeignKeyField(Recipe, backref='backref_recipe')
    customer = ForeignKeyField(Customer, backref='backref_customer')
    is_publish = BooleanField(default=True)
    score = IntegerField(
        choices=(
            (1, 'Very Dissatisfied'),
            (2, 'Dissatisfied'),
            (3, 'Good'),
            (4, 'Very Good'),
            (5, 'Excellent'),
        ),
        default=5)
    summary = CharField()
    pub_date = DateTimeField(default=datetime.now)

    @property
    def serialize(self):
        data = {
            'id': self.id,
            'recipe': str(self.recipe.recipe_name).strip(),
            'review': str(self.review).strip(),
            'customer': str(self.customer).strip(),
            'score': str(self.score).strip(),
            'summary': str(self.summary).strip(),
            'pub_date': str(self.pub_date).strip(),
        }
        # return model_to_dict(self)
        return data


class WeeklyMenuReview(BaseModel):
    """Weekly Menu review Model"""
    review = TextField()
    menu = ForeignKeyField(WeeklyMenu, backref='backref_recipe')
    customer = ForeignKeyField(Customer, backref='backref_customer')
    is_publish = BooleanField(default=True)
    score = IntegerField(
        choices=(
            (1, 'Very Dissatisfied'),
            (2, 'Dissatisfied'),
            (3, 'Good'),
            (4, 'Very Good'),
            (5, 'Excellent'),
        ),
        default=5)
    summary = CharField()
    pub_date = DateTimeField(default=datetime.now)

    @property
    def serialize(self):
        data = {
            'id': self.id,
            'menu': str(self.menu.week_number).strip(),
            'review': str(self.review).strip(),
            'customer': str(self.customer).strip(),
            'score': str(self.score).strip(),
            'summary': str(self.summary).strip(),
            'pub_date': str(self.pub_date).strip(),
        }
        # return model_to_dict(self)
        return data
