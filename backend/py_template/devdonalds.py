from collections import Counter
from dataclasses import dataclass
from typing import (
    Annotated,
    Iterable,
    List,
    Dict,
    Literal,
    Optional,
    Union,
)
from flask import Flask, request, jsonify
import re

from pydantic import BaseModel, Field, TypeAdapter, ValidationError


# ==== Type Definitions, feel free to add or modify ===========================


class Item(BaseModel):
    name: str
    quantity: int


class Recipe(BaseModel):
    type: Literal["recipe"]
    name: str
    requiredItems: List[Item]


class Ingredient(BaseModel):
    type: Literal["ingredient"]
    name: str
    cookTime: Annotated[int, Field(strict=True, ge=0)]


class RecipeSummary(BaseModel):
    name: str
    cookTime: int
    ingredients: List[Item]


Entry = Annotated[Union[Recipe, Ingredient], Field(discriminator="type")]

# A name uniquely identifies an entry.
EntryName = str

IngredientQuantities = Dict[str, int]


@dataclass
class Cookbook:
    recipes: Dict[EntryName, Recipe]
    ingredients: Dict[EntryName, Ingredient]

    def __init__(self, recipes=dict(), ingredients=dict()):
        self.recipes = recipes
        self.ingredients = ingredients

    def add_entry(self, entry: Entry) -> bool:
        """
        Return whether adding the entry was successful.
        """
        entry_name_exists = any(
            entry.name in entry_names
            for entry_names in [self.recipes.keys(), self.ingredients.keys()]
        )
        if entry_name_exists:
            return False

        match entry:
            case Recipe() as recipe:
                self.recipes[recipe.name] = recipe
            case Ingredient() as ingredient:
                self.ingredients[ingredient.name] = ingredient

        return True

    def all_ingredient_quantities(self, recipe_name: str) -> Optional[Counter]:
        if (recipe := self.recipes.get(recipe_name, None)) is None:
            # A recipe with the corresponding name cannot be found.
            return None

        if recipe_name in self.ingredients:
            # The searched name is NOT a recipe name (ie. an ingredient).
            return None

        # Map ingredient name to quantity.
        all_ingredients: Counter[str] = Counter()

        for item in recipe.requiredItems:
            # Check if required item is an ingredient or another (child) recipe.
            if (
                ingredient := self.ingredients.get(item.name, None)
            ) is not None:
                all_ingredients[ingredient.name] += item.quantity
            elif (
                child_recipe := self.recipes.get(item.name, None)
            ) is not None:
                if (
                    new_ingredients := self.all_ingredient_quantities(
                        child_recipe.name
                    )
                ) is not None:
                    # Merge new ingredients into total/all.
                    all_ingredients += new_ingredients
                else:
                    return None
            else:
                # Item is neither ingredient nor recipe.
                return None

        return all_ingredients

    def summary(self, recipe_name: str) -> Optional[RecipeSummary]:
        if (
            ingredient_quantities := self.all_ingredient_quantities(recipe_name)
        ) is None:
            return None

        # Invariant: We know all ingredients exist in the cookbook.
        total_cook_time = sum(
            (
                self.ingredients[ingredient_name].cookTime * quantity
                for ingredient_name, quantity in ingredient_quantities.items()
            ),
            start=0,
        )
        total_ingredients: List[Item] = [
            Item(name=name, quantity=quantity)
            for name, quantity in ingredient_quantities.items()
        ]
        summary = RecipeSummary(
            name=recipe_name,
            cookTime=total_cook_time,
            ingredients=total_ingredients,
        )

        return summary


def test_cookbook_add_entry():
    # Test 'entry names must be unique'.
    cookbook = Cookbook(
        recipes={
            "Burger": Recipe(type="recipe", name="Burger", requiredItems=[]),
            "Fries": Recipe(type="recipe", name="Fries", requiredItems=[]),
        }
    )
    assert (
        cookbook.add_entry(
            Recipe(type="recipe", name="Burger", requiredItems=[])
        )
        == False
    )

    # Test 'entry names must be unique'.
    cookbook = Cookbook(
        recipes={
            "Burger": Recipe(type="recipe", name="Burger", requiredItems=[]),
            "Fries": Recipe(
                type="recipe",
                name="Fries",
                requiredItems=[Item(name="Potato", quantity=5)],
            ),
        },
        ingredients={
            "Potato": Ingredient(type="ingredient", name="Potato", cookTime=6),
        },
    )
    # Entry names must be unique, so adding a "Potato" recipe when a "Potato"
    # ingredient already exists is not allowed.
    assert (
        cookbook.add_entry(
            Recipe(type="recipe", name="Potato", requiredItems=[])
        )
        == False
    )


def test_cookbook_summary():
    # Test success.
    cookbook = Cookbook(
        recipes={
            "Burger": Recipe(
                type="recipe",
                name="Burger",
                requiredItems=[
                    Item(name="Bun", quantity=1),
                    Item(name="Patty", quantity=1),
                    Item(name="Tomato", quantity=2),
                ],
            ),
            "Patty": Recipe(
                type="recipe",
                name="Patty",
                requiredItems=[
                    Item(name="Beef", quantity=3),
                ],
            ),
            "Fries": Recipe(
                type="recipe",
                name="Fries",
                requiredItems=[Item(name="Potato", quantity=5)],
            ),
        },
        ingredients={
            "Bun": Ingredient(type="ingredient", name="Bun", cookTime=1),
            "Beef": Ingredient(type="ingredient", name="Beef", cookTime=5),
            "Tomato": Ingredient(type="ingredient", name="Tomato", cookTime=2),
            "Potato": Ingredient(type="ingredient", name="Potato", cookTime=6),
        },
    )
    assert cookbook.summary("Burger") == RecipeSummary(
        name="Burger",
        cookTime=20,
        ingredients=[
            Item(name="Bun", quantity=1),
            Item(name="Beef", quantity=3),
            Item(name="Tomato", quantity=2),
        ],
    )

    # Test 'A recipe with the corresponding name cannot be found.'
    cookbook = Cookbook(
        recipes={
            "Burger": Recipe(type="recipe", name="Burger", requiredItems=[]),
        },
        ingredients={},
    )
    assert cookbook.summary("Non existant") == None

    # Test 'The searched name is NOT a recipe name (ie. an ingredient).'
    cookbook = Cookbook(
        recipes={
            "Burger": Recipe(type="recipe", name="Burger", requiredItems=[]),
        },
        ingredients={
            "Potato": Ingredient(type="ingredient", name="Potato", cookTime=6),
        },
    )
    assert cookbook.summary("Potato") == None

    # Test 'The recipe contains recipes or ingredients that aren't in the cookbook.'
    cookbook = Cookbook(
        recipes={
            "Burger": Recipe(
                type="recipe",
                name="Burger",
                requiredItems=[
                    Item(name="Bun", quantity=1),
                    Item(name="Patty", quantity=1),
                    Item(name="Tomato", quantity=2),
                ],
            ),
            "Patty": Recipe(
                type="recipe",
                name="Patty",
                requiredItems=[
                    Item(name="Beef", quantity=3),
                ],
            ),
            "Fries": Recipe(
                type="recipe",
                name="Fries",
                requiredItems=[Item(name="Potato", quantity=5)],
            ),
        },
        ingredients={
            "Bun": Ingredient(type="ingredient", name="Bun", cookTime=1),
            "Beef": Ingredient(type="ingredient", name="Beef", cookTime=5),
            "Potato": Ingredient(type="ingredient", name="Potato", cookTime=6),
        },
    )
    assert cookbook.summary("Burger") == None

    cookbook = Cookbook(
        recipes={
            "Burger": Recipe(
                type="recipe",
                name="Burger",
                requiredItems=[
                    Item(name="Bun", quantity=1),
                    Item(name="Patty", quantity=1),
                    Item(name="Tomato", quantity=2),
                ],
            ),
            "Patty": Recipe(
                type="recipe",
                name="Patty",
                requiredItems=[
                    Item(name="Beef", quantity=3),
                ],
            ),
            "Fries": Recipe(
                type="recipe",
                name="Fries",
                requiredItems=[Item(name="Potato", quantity=5)],
            ),
        },
        ingredients={
            "Bun": Ingredient(type="ingredient", name="Bun", cookTime=1),
            "Tomato": Ingredient(type="ingredient", name="Tomato", cookTime=2),
            "Potato": Ingredient(type="ingredient", name="Potato", cookTime=6),
        },
    )
    assert cookbook.summary("Burger") == None


# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
cookbook = Cookbook()


# Task 1 helper (don't touch)
@app.route("/parse", methods=["POST"])
def parse():
    data = request.get_json()
    recipe_name = data.get("input", "")
    parsed_name = parse_handwriting(recipe_name)
    if parsed_name is None:
        return "Invalid recipe name", 400
    return jsonify({"msg": parsed_name}), 200


# [TASK 1] ====================================================================
# Takes in a recipeName and returns it in a form that
def parse_handwriting(recipe_name: str) -> Union[str | None]:
    # Replace all hyphens (-) and underscores (_) with a whitespace.
    recipe_name = re.sub(r"-|_", " ", recipe_name)

    # Keep only alphabetic and whitespace characters.
    recipe_name = "".join(
        filter(lambda c: c.isalpha() or c.isspace(), recipe_name)
    )

    # Captialise all words.
    recipe_name = " ".join(map(str.capitalize, recipe_name.split()))

    if len(recipe_name) > 0:
        return recipe_name
    else:
        return None


def test_parse_handwriting():
    assert parse_handwriting("Riz@z RISO00tto!") == "Rizz Risotto"

    assert parse_handwriting("meatball") == "Meatball"
    assert parse_handwriting("Skibidi spaghetti") == "Skibidi Spaghetti"
    assert parse_handwriting("alpHa alFRedo") == "Alpha Alfredo"

    assert parse_handwriting("Skibidi   spaghetti") == "Skibidi Spaghetti"
    assert parse_handwriting("Skibidi spaghetti    ") == "Skibidi Spaghetti"
    assert parse_handwriting("Skibidi___Spaghetti  ") == "Skibidi Spaghetti"

    assert parse_handwriting("  HellO-_ World") == "Hello World"


# [TASK 2] ====================================================================


def contains_duplicates(iterable: Iterable) -> bool:
    seen = set()
    for e in iterable:
        if e in seen:
            return True
        else:
            seen.add(e)
    return False


def test_contains_duplicates():
    assert contains_duplicates(iter([1, 2, 3])) == False
    assert contains_duplicates(iter([1, 2, 3, 1])) == True
    assert contains_duplicates(iter([])) == False
    assert contains_duplicates(iter([1, 1])) == True
    assert contains_duplicates(iter([1, 2, 1, 1])) == True


def parse_entry(json_data: Dict) -> Optional[Entry]:
    # TODO: Ideal return type would be `Error` (e.g. from Rust), but since
    # python doesn't have that, I prefer telling the caller this can fail with
    # the Optional than them maybe forgetting to catch an exception.

    try:
        entry: Entry = TypeAdapter(Entry).validate_python(json_data)
    except ValidationError:
        return None

    # Recipe requiredItems can only have one element per name.
    match entry:
        case Recipe() as recipe:
            item_names = (item.name for item in recipe.requiredItems)
            if contains_duplicates(item_names):
                return None

    return entry


def test_parse_entry():
    # Example of a 'recipe' entry containing a recipe and ingredient as requiredItems
    data = {
        "type": "recipe",
        "name": "Sussy Salad",
        "requiredItems": [
            {"name": "Mayonaise", "quantity": 1},
            {"name": "Lettuce", "quantity": 3},
        ],
    }
    assert parse_entry(data) == Recipe(
        type="recipe",
        name="Sussy Salad",
        requiredItems=[
            Item(name="Mayonaise", quantity=1),
            Item(name="Lettuce", quantity=3),
        ],
    )

    # Example of a 'recipe' entry, only requiring a single ingredient
    data = {
        "type": "recipe",
        "name": "Mayonaise",
        "requiredItems": [{"name": "Egg", "quantity": 1}],
    }
    assert parse_entry(data) == Recipe(
        type="recipe",
        name="Mayonaise",
        requiredItems=[
            Item(name="Egg", quantity=1),
        ],
    )

    # Example of an 'ingredient' entry
    data = {
        "type": "ingredient",
        "name": "Egg",
        "cookTime": 6,
    }
    assert parse_entry(data) == Ingredient(
        type="ingredient",
        name="Egg",
        cookTime=6,
    )

    # Example of an 'ingredient' entry
    data = {
        "type": "ingredient",
        "name": "Lettuce",
        "cookTime": 0,
    }
    assert parse_entry(data) == Ingredient(
        type="ingredient",
        name="Lettuce",
        cookTime=0,
    )

    # Test 'type can only be "recipe" or "ingredient".'
    data = {
        "type": "other",
        "name": "Lettuce",
        "cookTime": 0,
    }
    assert parse_entry(data) == None

    # Test 'cookTime can only be greater than or equal to 0'
    data = {
        "type": "ingredient",
        "name": "Lettuce",
        "cookTime": -1,
    }
    assert parse_entry(data) == None

    # Recipe requiredItems can only have one element per name.
    data = {
        "type": "recipe",
        "name": "Mayonaise",
        "requiredItems": [
            {"name": "Egg", "quantity": 1},
            {"name": "Other", "quantity": 2},
            {"name": "Egg", "quantity": 2},
        ],
    }
    assert parse_entry(data) == None


# Endpoint that adds a CookbookEntry to your magical cookbook
@app.route("/entry", methods=["POST"])
def create_entry():
    data = request.get_json()

    if (entry := parse_entry(data)) is None:
        # TODO: do better error handling, i.e. return what concretely went wrong
        return "failed to parse entry", 400

    if not cookbook.add_entry(entry):
        return "failed to add entry to cookbook", 400

    return "successfully added entry", 200


# [TASK 3] ====================================================================
# Endpoint that returns a summary of a recipe that corresponds to a query name
@app.route("/summary", methods=["GET"])
def summary():
    if (recipe_name := request.args.get("name")) is None:
        return "missing 'name' query parameter", 400

    if (summary := cookbook.summary(recipe_name)) is None:
        # TODO: once again, do better error handling
        return (
            "failed to get summary due to invalid cookbook state or provided name",
            400,
        )

    data = summary.model_dump_json()
    return data, 200


# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8080)
