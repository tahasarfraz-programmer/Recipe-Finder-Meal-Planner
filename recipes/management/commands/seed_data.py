"""Populate the database with demo recipes, ingredients, reviews and a demo user.

Usage:  python manage.py seed_data [--reset] [--no-demo-user]

All recipes and nutrition figures are rough sample data for demonstration only.
"""
import datetime
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from planner.models import MealPlan
from planner.services import generate_plan
from recipes.models import (
    Category, Cuisine, DietaryPreference, Favorite, Ingredient, IngredientCategory,
    Instruction, Recipe, RecipeIngredient, Review,
)

CATEGORIES = [("Breakfast", "🍳"), ("Lunch", "🥪"), ("Dinner", "🍝"), ("Dessert", "🍰"), ("Snack", "🥨"),
              ("Appetizer", "🧆"), ("Soup", "🍲"), ("Salad", "🥗"), ("Drinks", "🥤")]
CUISINES = ["Pakistani", "Indian", "Italian", "Chinese", "Mexican", "American", "Mediterranean", "Japanese", "Korean", "Thai", "Other"]
DIETS = ["Vegetarian", "Vegan", "Halal", "Gluten Free", "Dairy Free", "Low Carb", "High Protein"]

_ING = {
    "vegetables": "Onion|Red onion|Garlic|Tomato|Potato|Sweet potato|Carrot|Spinach|Cucumber|Bell pepper|Green chili|Ginger|Cauliflower|Green peas|Lettuce|Mushrooms|Broccoli|Zucchini|Fresh coriander|Fresh mint|Avocado|Corn|Cabbage|Spring onion|Fresh basil",
    "fruits": "Lemon|Lime|Banana|Mixed berries|Mango|Apple",
    "meat": "Chicken breast|Chicken thighs|Ground beef|Beef strips|Chicken drumsticks",
    "seafood": "Salmon fillet|Shrimp",
    "dairy": "Milk|Butter|Eggs|Plain yogurt|Cheddar cheese|Mozzarella|Parmesan|Paneer|Heavy cream|Feta cheese",
    "grains": "Basmati rice|Spaghetti|Penne|Rolled oats|Flour tortillas|Chickpeas|Red lentils|Black beans|Quinoa|Bread slices|Egg noodles|Sushi rice|All-purpose flour|Whole wheat flour",
    "spices": "Salt|Black pepper|Cumin powder|Turmeric|Red chili powder|Garam masala|Coriander powder|Paprika|Dried oregano|Cinnamon|Biryani masala|Chili flakes|Cardamom",
    "pantry": "Olive oil|Vegetable oil|Soy sauce|Honey|Sugar|Tomato paste|Canned tomatoes|Coconut milk|Peanut butter|Baking powder|Vanilla extract|Cocoa powder|Chicken stock|Vegetable stock|Sesame oil|Rice vinegar|Gochujang|Fish sauce|Tahini|Green curry paste|Salsa|Dark chocolate|Water",
}
INGREDIENT_CATEGORY = {name: cat for cat, names in _ING.items() for name in names.split("|")}

FEATURED = {"Chicken Biryani", "Chicken Karahi", "Spaghetti Aglio e Olio", "Palak Paneer", "Salmon with Lemon Butter",
            "Thai Green Curry with Chicken", "Greek Salad", "Fudgy Cocoa Brownies"}

# title, category, cuisine, diets, difficulty, prep, cook, servings, (kcal, protein, carbs, fat, fiber), description, ingredients, steps
RECIPES = [
    ("Oatmeal with Fruits", "Breakfast", "American", ["Vegetarian"], "easy", 5, 10, 2, (320, 9, 52, 8, 7),
     "Creamy stovetop oats topped with banana and berries for a filling start to the day.",
     [(1, "cup", "Rolled oats"), (2, "cups", "Milk"), (1, "", "Banana"), (0.5, "cup", "Mixed berries"), (1, "tbsp", "Honey"), (0.5, "tsp", "Cinnamon")],
     ["Simmer the oats with the milk, stirring, for 5 to 7 minutes until thick.", "Stir in the cinnamon.", "Slice the banana.", "Spoon into bowls and top with banana, berries and honey."]),
    ("Masala Omelette", "Breakfast", "Indian", ["Vegetarian", "Gluten Free", "High Protein", "Low Carb"], "easy", 5, 8, 2, (290, 18, 5, 21, 1),
     "A fluffy omelette packed with onion, tomato, green chili and coriander.",
     [(4, "", "Eggs"), (0.5, "", "Onion"), (1, "", "Tomato"), (1, "", "Green chili"), (2, "tbsp", "Fresh coriander"), (0.5, "tsp", "Turmeric"), (1, "tbsp", "Vegetable oil"), (0.5, "tsp", "Salt")],
     ["Finely chop the onion, tomato, chili and coriander.", "Beat the eggs with the salt and turmeric, then stir in the vegetables.", "Heat the oil in a pan and pour in the mixture.", "Cook until set, fold and serve hot."]),
    ("Aloo Paratha", "Breakfast", "Pakistani", ["Vegetarian"], "medium", 25, 15, 4, (340, 8, 48, 13, 4),
     "Whole wheat flatbread stuffed with spiced mashed potato, served with yogurt.",
     [(2, "cups", "Whole wheat flour"), (3, "", "Potato"), (1, "tsp", "Cumin powder"), (1, "tsp", "Red chili powder"), (2, "tbsp", "Fresh coriander"), (1, "tsp", "Salt"), (3, "tbsp", "Butter"), (1, "cup", "Plain yogurt")],
     ["Boil and mash the potatoes, then mix with the spices, salt and coriander.", "Knead the flour with water into a soft dough and rest for 15 minutes.", "Fill balls of dough with the potato mixture and roll flat.", "Cook on a hot pan with butter until golden on both sides.", "Serve with yogurt."]),
    ("Banana Pancakes", "Breakfast", "American", ["Vegetarian"], "easy", 10, 15, 4, (310, 8, 52, 8, 3),
     "Soft, lightly sweet pancakes made with ripe bananas.",
     [(1.5, "cups", "All-purpose flour"), (2, "tsp", "Baking powder"), (2, "", "Banana"), (1, "cup", "Milk"), (1, "", "Eggs"), (1, "tbsp", "Sugar"), (1, "tbsp", "Butter"), (2, "tbsp", "Honey")],
     ["Mash the bananas and whisk in the milk and egg.", "Fold in the flour, baking powder and sugar until just combined.", "Cook scoops of batter in a buttered pan until bubbles form, then flip.", "Serve drizzled with honey."]),
    ("Avocado Toast with Egg", "Breakfast", "American", ["Vegetarian", "Dairy Free"], "easy", 5, 5, 2, (340, 14, 26, 20, 8),
     "Crisp toast, smashed avocado with lemon and a soft fried egg.",
     [(2, "", "Bread slices"), (1, "", "Avocado"), (2, "", "Eggs"), (1, "tsp", "Lemon"), (0.5, "tsp", "Chili flakes"), (0.5, "tsp", "Salt"), (1, "tsp", "Olive oil")],
     ["Toast the bread.", "Mash the avocado with lemon juice and salt.", "Fry the eggs in olive oil.", "Spread avocado on the toast, top with an egg and chili flakes."]),
    ("Chicken Biryani", "Dinner", "Pakistani", ["Halal", "High Protein", "Gluten Free"], "hard", 30, 60, 6, (560, 32, 62, 19, 3),
     "Fragrant layered rice with spiced, yogurt-marinated chicken and fried onions.",
     [(1, "kg", "Chicken thighs"), (3, "cups", "Basmati rice"), (1, "cup", "Plain yogurt"), (3, "", "Onion"), (2, "", "Tomato"), (1, "tbsp", "Ginger"), (6, "cloves", "Garlic"), (3, "tbsp", "Biryani masala"), (1, "tsp", "Turmeric"), (0.5, "cup", "Vegetable oil"), (0.5, "cup", "Fresh mint"), (2, "tsp", "Salt")],
     ["Marinate the chicken in yogurt, ginger, garlic, biryani masala and salt for at least 30 minutes.", "Slice the onions and fry until deep golden; set half aside.", "Cook the marinated chicken with the tomatoes and remaining onions until tender.", "Parboil the rice with salt until 70 percent cooked and drain.", "Layer rice over chicken with mint and reserved onions, cover tightly and steam on low heat for 20 minutes.", "Fluff gently and serve."]),
    ("Chicken Karahi", "Dinner", "Pakistani", ["Halal", "Gluten Free", "High Protein", "Low Carb", "Dairy Free"], "medium", 15, 35, 4, (380, 34, 9, 23, 2),
     "A bold wok-style chicken curry built on fresh tomatoes, ginger and green chilies.",
     [(800, "g", "Chicken thighs"), (5, "", "Tomato"), (2, "tbsp", "Ginger"), (5, "cloves", "Garlic"), (3, "", "Green chili"), (1, "tsp", "Red chili powder"), (1, "tsp", "Coriander powder"), (1, "tsp", "Garam masala"), (0.25, "cup", "Vegetable oil"), (2, "tbsp", "Fresh coriander"), (1.5, "tsp", "Salt")],
     ["Heat the oil and sear the chicken until lightly browned.", "Add ginger and garlic and cook for a minute.", "Add the chopped tomatoes, chili powder, coriander powder and salt; cook until the tomatoes break down.", "Cover and simmer until the chicken is tender and the oil separates.", "Finish with green chili, garam masala and fresh coriander."]),
    ("Spaghetti Aglio e Olio", "Dinner", "Italian", ["Vegetarian", "Vegan", "Dairy Free"], "easy", 5, 15, 2, (520, 14, 78, 17, 4),
     "The classic Roman pasta of garlic, olive oil and chili flakes, ready in 20 minutes.",
     [(200, "g", "Spaghetti"), (5, "cloves", "Garlic"), (0.25, "cup", "Olive oil"), (1, "tsp", "Chili flakes"), (2, "tbsp", "Fresh basil"), (1, "tsp", "Salt")],
     ["Boil the spaghetti in salted water until al dente; reserve a cup of pasta water.", "Gently cook sliced garlic in olive oil until pale gold.", "Add chili flakes, then the drained pasta and a splash of pasta water.", "Toss until glossy and finish with basil."]),
    ("Chicken Alfredo Penne", "Dinner", "Italian", ["Halal", "High Protein"], "medium", 10, 25, 4, (690, 38, 62, 32, 3),
     "Penne in a rich parmesan cream sauce with seared chicken.",
     [(400, "g", "Penne"), (500, "g", "Chicken breast"), (1, "cup", "Heavy cream"), (1, "cup", "Parmesan"), (3, "cloves", "Garlic"), (2, "tbsp", "Butter"), (1, "tsp", "Black pepper"), (1, "tsp", "Salt")],
     ["Season and sear the chicken, then slice.", "Cook the penne until al dente and drain.", "Melt the butter, cook the garlic, then add cream and simmer for 3 minutes.", "Stir in parmesan until smooth.", "Toss with the pasta and chicken and finish with pepper."]),
    ("Beef Tacos", "Dinner", "Mexican", ["Dairy Free"], "easy", 10, 15, 4, (450, 26, 36, 22, 5),
     "Quick spiced beef tacos with fresh tomato, lettuce and lime.",
     [(500, "g", "Ground beef"), (8, "", "Flour tortillas"), (1, "", "Onion"), (2, "", "Tomato"), (1, "cup", "Lettuce"), (2, "tsp", "Cumin powder"), (1, "tsp", "Paprika"), (1, "", "Lime"), (1, "cup", "Salsa")],
     ["Brown the beef with the chopped onion.", "Add cumin, paprika and salt and cook for 2 minutes.", "Warm the tortillas.", "Fill with beef, tomato and lettuce; serve with salsa and lime."]),
    ("Chicken Stir-Fry with Vegetables", "Dinner", "Chinese", ["Halal", "Dairy Free", "High Protein"], "easy", 15, 10, 3, (360, 34, 20, 15, 5),
     "A fast, glossy stir-fry with chicken, broccoli, peppers and carrots.",
     [(400, "g", "Chicken breast"), (1, "", "Broccoli"), (1, "", "Bell pepper"), (2, "", "Carrot"), (3, "tbsp", "Soy sauce"), (1, "tbsp", "Ginger"), (3, "cloves", "Garlic"), (1, "tbsp", "Sesame oil"), (1, "tbsp", "Vegetable oil")],
     ["Slice the chicken and vegetables thinly.", "Stir-fry the chicken in hot oil until cooked; remove.", "Stir-fry ginger, garlic and vegetables for 3 minutes.", "Return the chicken, add soy sauce and finish with sesame oil."]),
    ("Palak Paneer", "Dinner", "Indian", ["Vegetarian", "Gluten Free"], "medium", 15, 25, 4, (340, 17, 12, 24, 4),
     "Cubes of paneer in a silky spiced spinach sauce.",
     [(400, "g", "Paneer"), (500, "g", "Spinach"), (1, "", "Onion"), (2, "", "Tomato"), (1, "tbsp", "Ginger"), (4, "cloves", "Garlic"), (1, "tsp", "Cumin powder"), (1, "tsp", "Garam masala"), (0.25, "cup", "Heavy cream"), (2, "tbsp", "Butter"), (1, "tsp", "Salt")],
     ["Blanch the spinach for 2 minutes, then blend to a purée.", "Cook the onion, ginger and garlic in butter until soft.", "Add tomatoes and spices and cook until thick.", "Stir in the spinach purée and cream and simmer for 5 minutes.", "Add the paneer and warm through."]),
    ("Chana Masala", "Lunch", "Indian", ["Vegetarian", "Vegan", "Gluten Free", "Dairy Free", "Halal"], "easy", 10, 30, 4, (330, 13, 52, 8, 13),
     "Chickpeas simmered in a tangy tomato and onion gravy with warm spices.",
     [(2, "cups", "Chickpeas"), (2, "", "Onion"), (3, "", "Tomato"), (1, "tbsp", "Ginger"), (4, "cloves", "Garlic"), (2, "tsp", "Coriander powder"), (1, "tsp", "Cumin powder"), (1, "tsp", "Garam masala"), (1, "tsp", "Red chili powder"), (3, "tbsp", "Vegetable oil"), (1, "tsp", "Salt")],
     ["Fry the chopped onions in oil until golden.", "Add ginger, garlic and spices and stir for a minute.", "Add tomatoes and cook down to a paste.", "Add chickpeas and a cup of water and simmer for 20 minutes.", "Finish with garam masala."]),
    ("Salmon with Lemon Butter", "Dinner", "Mediterranean", ["Gluten Free", "Low Carb", "High Protein", "Halal"], "easy", 10, 15, 2, (430, 34, 3, 31, 1),
     "Pan-seared salmon in a bright lemon garlic butter sauce.",
     [(2, "", "Salmon fillet"), (2, "tbsp", "Butter"), (2, "cloves", "Garlic"), (1, "", "Lemon"), (1, "tbsp", "Olive oil"), (1, "tbsp", "Fresh basil"), (0.5, "tsp", "Salt"), (0.5, "tsp", "Black pepper")],
     ["Season the salmon and sear skin-side down in olive oil for 4 minutes.", "Flip and cook 3 more minutes.", "Add butter, garlic and lemon juice and spoon over the fish.", "Finish with basil."]),
    ("Beef Bulgogi Bowl", "Dinner", "Korean", ["Dairy Free"], "medium", 15, 15, 4, (520, 30, 58, 18, 3),
     "Sweet and savory marinated beef over rice with quick cucumber.",
     [(500, "g", "Beef strips"), (2, "cups", "Sushi rice"), (4, "tbsp", "Soy sauce"), (2, "tbsp", "Sugar"), (1, "tbsp", "Sesame oil"), (4, "cloves", "Garlic"), (2, "", "Spring onion"), (1, "", "Cucumber"), (1, "tbsp", "Gochujang")],
     ["Marinate the beef in soy sauce, sugar, sesame oil and garlic for 20 minutes.", "Cook the rice.", "Sear the beef in a hot pan in batches.", "Serve over rice with sliced cucumber, spring onion and gochujang."]),
    ("Thai Green Curry with Chicken", "Dinner", "Thai", ["Halal", "Gluten Free", "Dairy Free", "High Protein"], "medium", 15, 25, 4, (470, 30, 14, 33, 3),
     "Creamy coconut curry with tender chicken and vegetables.",
     [(500, "g", "Chicken breast"), (3, "tbsp", "Green curry paste"), (400, "ml", "Coconut milk"), (1, "", "Zucchini"), (1, "", "Bell pepper"), (1, "tbsp", "Fish sauce"), (1, "tbsp", "Sugar"), (0.25, "cup", "Fresh basil"), (1.5, "cups", "Basmati rice")],
     ["Fry the curry paste in a spoonful of coconut milk for 1 minute.", "Add the sliced chicken and cook until sealed.", "Pour in the remaining coconut milk and simmer for 10 minutes.", "Add vegetables, fish sauce and sugar and cook 5 more minutes.", "Finish with basil and serve with rice."]),
    ("Teriyaki Chicken Rice Bowl", "Lunch", "Japanese", ["Halal", "Dairy Free", "High Protein"], "easy", 10, 15, 3, (510, 33, 62, 12, 3),
     "Glazed chicken over steamed rice with broccoli.",
     [(450, "g", "Chicken thighs"), (1.5, "cups", "Sushi rice"), (4, "tbsp", "Soy sauce"), (2, "tbsp", "Honey"), (1, "tbsp", "Rice vinegar"), (2, "cloves", "Garlic"), (1, "", "Broccoli"), (1, "tbsp", "Vegetable oil")],
     ["Cook the rice.", "Mix soy sauce, honey, vinegar and garlic for the glaze.", "Sear the chicken, then add the glaze and cook until sticky.", "Steam the broccoli and serve everything over rice."]),
    ("Greek Salad", "Salad", "Mediterranean", ["Vegetarian", "Gluten Free", "Low Carb"], "easy", 15, 0, 4, (220, 6, 11, 18, 3),
     "Crisp cucumber, tomato and feta with olive oil and oregano.",
     [(3, "", "Tomato"), (1, "", "Cucumber"), (1, "", "Red onion"), (200, "g", "Feta cheese"), (3, "tbsp", "Olive oil"), (1, "tsp", "Dried oregano"), (1, "tbsp", "Lemon")],
     ["Cut the tomato, cucumber and onion into chunks.", "Top with feta.", "Dress with olive oil, lemon and oregano and serve immediately."]),
    ("Quinoa Chickpea Salad", "Salad", "Mediterranean", ["Vegetarian", "Vegan", "Dairy Free", "Gluten Free"], "easy", 15, 15, 4, (380, 14, 52, 13, 10),
     "A hearty make-ahead salad with quinoa, chickpeas, cucumber and lemon dressing.",
     [(1, "cup", "Quinoa"), (1.5, "cups", "Chickpeas"), (1, "", "Cucumber"), (2, "", "Tomato"), (0.25, "cup", "Fresh mint"), (3, "tbsp", "Olive oil"), (2, "tbsp", "Lemon"), (0.5, "tsp", "Salt")],
     ["Rinse and cook the quinoa; cool.", "Chop the vegetables and mint.", "Combine everything and dress with olive oil, lemon and salt."]),
    ("Red Lentil Soup", "Soup", "Mediterranean", ["Vegetarian", "Vegan", "Gluten Free", "Dairy Free"], "easy", 10, 25, 4, (290, 15, 46, 5, 12),
     "Silky lentil soup warmed with cumin and finished with lemon.",
     [(1.5, "cups", "Red lentils"), (1, "", "Onion"), (2, "", "Carrot"), (3, "cloves", "Garlic"), (1, "tsp", "Cumin powder"), (4, "cups", "Vegetable stock"), (1, "tbsp", "Olive oil"), (1, "", "Lemon"), (1, "tsp", "Salt")],
     ["Soften the onion, carrot and garlic in olive oil.", "Add cumin, lentils and stock and simmer for 20 minutes.", "Blend until smooth.", "Season and finish with lemon juice."]),
    ("Chicken Noodle Soup", "Soup", "American", ["Halal", "Dairy Free", "High Protein"], "easy", 15, 30, 4, (310, 26, 30, 9, 3),
     "Comforting broth with shredded chicken, noodles, carrots and onion.",
     [(300, "g", "Chicken breast"), (150, "g", "Egg noodles"), (2, "", "Carrot"), (1, "", "Onion"), (5, "cups", "Chicken stock"), (2, "cloves", "Garlic"), (1, "tsp", "Black pepper"), (1, "tsp", "Salt")],
     ["Simmer the chicken with the stock, onion, carrots and garlic for 20 minutes.", "Remove and shred the chicken.", "Cook the noodles in the broth.", "Return the chicken, season and serve."]),
    ("Fudgy Cocoa Brownies", "Dessert", "American", ["Vegetarian"], "medium", 15, 25, 9, (280, 4, 34, 15, 2),
     "Dense, chewy brownies with a crackly top.",
     [(0.5, "cup", "Butter"), (1, "cup", "Sugar"), (2, "", "Eggs"), (0.5, "cup", "Cocoa powder"), (0.5, "cup", "All-purpose flour"), (1, "tsp", "Vanilla extract"), (100, "g", "Dark chocolate"), (0.25, "tsp", "Salt")],
     ["Melt the butter and chocolate together and cool slightly.", "Whisk in the sugar, eggs and vanilla.", "Fold in the cocoa, flour and salt.", "Bake in a lined tin at 175°C (350°F) for 22 to 25 minutes.", "Cool before slicing."]),
    ("Kheer (Rice Pudding)", "Dessert", "Pakistani", ["Vegetarian", "Gluten Free"], "easy", 5, 40, 6, (260, 7, 42, 7, 1),
     "Slow-cooked rice pudding scented with cardamom.",
     [(0.5, "cup", "Basmati rice"), (1, "litre", "Milk"), (0.5, "cup", "Sugar"), (4, "", "Cardamom"), (1, "tbsp", "Butter")],
     ["Rinse the rice and sauté briefly in butter.", "Add milk and cardamom and simmer on low heat, stirring often, for 35 minutes.", "Stir in the sugar and cook 5 more minutes.", "Serve warm or chilled."]),
    ("Mango Lassi", "Drinks", "Indian", ["Vegetarian", "Gluten Free"], "easy", 5, 0, 2, (210, 6, 38, 4, 2),
     "A cooling yogurt and mango drink.",
     [(1, "cup", "Mango"), (1, "cup", "Plain yogurt"), (0.5, "cup", "Milk"), (1, "tbsp", "Honey"), (0.25, "tsp", "Cardamom")],
     ["Blend all ingredients until smooth.", "Chill and serve."]),
    ("Banana Berry Smoothie", "Drinks", "American", ["Vegetarian", "Gluten Free"], "easy", 5, 0, 2, (230, 8, 42, 4, 5),
     "A thick breakfast smoothie with banana, berries and yogurt.",
     [(1, "", "Banana"), (1, "cup", "Mixed berries"), (1, "cup", "Plain yogurt"), (0.5, "cup", "Milk"), (1, "tbsp", "Honey")],
     ["Add everything to a blender.", "Blend until smooth and pour into glasses."]),
    ("Hummus", "Appetizer", "Mediterranean", ["Vegetarian", "Vegan", "Dairy Free", "Gluten Free"], "easy", 10, 0, 6, (160, 6, 15, 9, 4),
     "Smooth chickpea dip with tahini, lemon and garlic.",
     [(2, "cups", "Chickpeas"), (0.25, "cup", "Tahini"), (2, "tbsp", "Lemon"), (1, "cloves", "Garlic"), (2, "tbsp", "Olive oil"), (0.5, "tsp", "Cumin powder"), (0.5, "tsp", "Salt"), (3, "tbsp", "Water")],
     ["Blend the tahini and lemon juice for a minute.", "Add the chickpeas, garlic, cumin and salt and blend until smooth, adding water as needed.", "Serve drizzled with olive oil."]),
    ("Chicken Quesadillas", "Lunch", "Mexican", ["Halal"], "easy", 10, 10, 2, (620, 38, 42, 32, 4),
     "Crisp tortillas filled with spiced chicken and melted cheddar.",
     [(2, "", "Flour tortillas"), (250, "g", "Chicken breast"), (1, "cup", "Cheddar cheese"), (0.5, "", "Bell pepper"), (1, "tsp", "Paprika"), (1, "tsp", "Cumin powder"), (1, "tbsp", "Vegetable oil"), (0.5, "cup", "Salsa")],
     ["Cook the diced chicken with paprika and cumin.", "Fill a tortilla with chicken, pepper and cheese; top with the second tortilla.", "Cook in a pan until golden on both sides.", "Slice and serve with salsa."]),
    ("Bean Burrito Bowl", "Lunch", "Mexican", ["Vegetarian", "Vegan", "Dairy Free", "Gluten Free"], "easy", 10, 20, 2, (540, 19, 88, 13, 17),
     "Rice, black beans, corn and avocado with salsa and lime.",
     [(1, "cup", "Basmati rice"), (1, "cup", "Black beans"), (0.5, "cup", "Corn"), (1, "", "Avocado"), (0.5, "cup", "Salsa"), (1, "", "Lime"), (1, "tsp", "Cumin powder")],
     ["Cook the rice.", "Warm the beans with cumin.", "Build bowls with rice, beans and corn.", "Top with avocado, salsa and lime juice."]),
    ("Roasted Spiced Chickpeas", "Snack", "Indian", ["Vegetarian", "Vegan", "Dairy Free", "Gluten Free", "High Protein"], "easy", 5, 25, 4, (180, 8, 24, 6, 7),
     "Crunchy oven-roasted chickpeas with chili and cumin.",
     [(2, "cups", "Chickpeas"), (1, "tbsp", "Olive oil"), (1, "tsp", "Cumin powder"), (1, "tsp", "Paprika"), (0.5, "tsp", "Red chili powder"), (0.5, "tsp", "Salt")],
     ["Drain and dry the chickpeas well.", "Toss with oil and spices.", "Roast at 200°C (400°F) for 25 minutes, shaking halfway, until crisp."]),
]

REVIEWERS = ["amira", "bilal", "carla", "dev", "elena", "farhan"]
COMMENTS = [
    "Made this last night and it was a hit.", "Easy to follow and tasted great.", "Good base recipe. I added a little extra spice.",
    "My family asked for seconds.", "Came together faster than I expected.", "Solid weeknight option.", "Would make again.",
    "Turned out well, though I cooked it a bit longer.", "",
]


class Command(BaseCommand):
    help = "Seed the database with demo recipes, reviews and a demo user."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing recipes and ingredients first.")
        parser.add_argument("--no-demo-user", action="store_true", help="Do not create the demo user.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            Recipe.objects.all().delete()
            Ingredient.objects.all().delete()
            self.stdout.write("Existing recipes and ingredients deleted.")

        categories = {n: Category.objects.get_or_create(name=n, defaults={"slug": slugify(n), "emoji": e})[0] for n, e in CATEGORIES}
        cuisines = {n: Cuisine.objects.get_or_create(name=n, defaults={"slug": slugify(n)})[0] for n in CUISINES}
        diets = {n: DietaryPreference.objects.get_or_create(name=n, defaults={"slug": slugify(n)})[0] for n in DIETS}

        created = 0
        for (title, cat, cui, diet_names, diff, prep, cook, serv, nutri, desc, ings, steps) in RECIPES:
            if Recipe.objects.filter(title=title).exists():
                continue
            cal, prot, carb, fat, fib = nutri
            recipe = Recipe.objects.create(
                title=title, description=desc, category=categories[cat], cuisine=cuisines[cui], difficulty=diff,
                prep_time=prep, cook_time=cook, servings=serv, calories=cal, protein=prot, carbohydrates=carb,
                fat=fat, fiber=fib, featured=title in FEATURED,
            )
            recipe.diets.set([diets[d] for d in diet_names])
            for qty, unit, name in ings:
                if name not in INGREDIENT_CATEGORY:
                    raise CommandError(f"Unknown ingredient '{name}' in '{title}'")
                ingredient, _ = Ingredient.objects.get_or_create(name=name, defaults={"category": INGREDIENT_CATEGORY[name]})
                RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient, quantity=Decimal(str(qty)), unit=unit)
            Instruction.objects.bulk_create(
                [Instruction(recipe=recipe, step_number=i, instruction=text) for i, text in enumerate(steps, 1)])
            created += 1

        User = get_user_model()
        rng = random.Random(42)
        reviewers = []
        for name in REVIEWERS:
            user, made = User.objects.get_or_create(username=name, defaults={"email": f"{name}@example.com"})
            if made:
                user.set_unusable_password()
                user.save()
            reviewers.append(user)
        new_reviews = 0
        for recipe in Recipe.objects.all():
            if recipe.reviews.exists():
                continue
            for user in rng.sample(reviewers, rng.randint(2, 5)):
                Review.objects.create(user=user, recipe=recipe, rating=rng.choice([3, 4, 4, 5, 5, 5]), comment=rng.choice(COMMENTS))
                new_reviews += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new recipes ({Recipe.objects.count()} total) and {new_reviews} reviews."))

        if not opts["no_demo_user"]:
            demo, made = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com", "first_name": "Demo"})
            if made:
                demo.set_password("demo12345")
                demo.save()
                for recipe in Recipe.objects.filter(featured=True)[:3]:
                    Favorite.objects.get_or_create(user=demo, recipe=recipe)
                today = datetime.date.today()
                monday = today - datetime.timedelta(days=today.weekday())
                generate_plan(demo, {"meals_per_day": 3}, monday, 7)
                MealPlan.objects.filter(user=demo, date__lt=today).update(is_cooked=True)
                self.stdout.write(self.style.SUCCESS("Demo user created: username 'demo', password 'demo12345' (development only)."))
