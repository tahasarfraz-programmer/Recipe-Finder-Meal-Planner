from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .factories import add_ingredient, add_step, make_recipe
from .models import Favorite, Review

User = get_user_model()


class RecipeBrowsingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pasta = make_recipe("Chicken Pasta", "Dinner", "Italian", diets=["Halal"], calories=600, difficulty="easy")
        cls.curry = make_recipe("Veggie Curry", "Dinner", "Indian", diets=["Vegetarian", "Vegan"], prep_time=20, cook_time=50, difficulty="medium")
        cls.oats = make_recipe("Morning Oats", "Breakfast", "American", diets=["Vegetarian"], prep_time=5, cook_time=5)
        cls.cake = make_recipe("Chocolate Cake", "Dessert", "American", diets=["Vegetarian"], prep_time=30, cook_time=40, difficulty="hard")
        add_ingredient(cls.pasta, "Penne", category="grains")
        add_ingredient(cls.curry, "Chickpeas", category="grains")

    def titles(self, response):
        return {r.title for r in response.context["page_obj"]}

    def test_listing_renders_all_recipes(self):
        response = self.client.get(reverse("recipes:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.titles(response)), 4)

    def test_pagination(self):
        for i in range(15):
            make_recipe(f"Extra Recipe {i}")
        response = self.client.get(reverse("recipes:list"))
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertTrue(response.context["page_obj"].has_next())
        page2 = self.client.get(reverse("recipes:list"), {"page": 2})
        self.assertEqual(page2.status_code, 200)

    def test_detail_uses_slug_and_shows_content(self):
        add_step(self.pasta, 1, "Boil the pasta.")
        response = self.client.get(self.pasta.get_absolute_url())
        self.assertEqual(self.pasta.get_absolute_url(), "/recipes/chicken-pasta/")
        self.assertContains(response, "Boil the pasta.")
        self.assertContains(response, "Penne")
        self.assertContains(response, "<title>Chicken Pasta | Recipe Finder</title>", html=True)

    def test_detail_missing_returns_custom_404(self):
        response = self.client.get("/recipes/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "couldn't find that page", status_code=404)

    def test_nutrition_fallback_when_unavailable(self):
        bare = make_recipe("Bare Recipe", calories=None)
        response = self.client.get(bare.get_absolute_url())
        self.assertContains(response, "Nutrition information isn't available")

    def test_placeholder_image(self):
        response = self.client.get(reverse("recipes:placeholder", args=[self.pasta.slug]))
        self.assertEqual(response["Content-Type"], "image/svg+xml")

    # --- search ---
    def test_search_by_title(self):
        self.assertEqual(self.titles(self.client.get(reverse("recipes:search"), {"q": "chicken pasta"})), {"Chicken Pasta"})

    def test_search_by_ingredient(self):
        self.assertEqual(self.titles(self.client.get(reverse("recipes:search"), {"q": "chickpeas"})), {"Veggie Curry"})

    def test_search_by_cuisine_ignores_filler_words(self):
        self.assertEqual(self.titles(self.client.get(reverse("recipes:search"), {"q": "Italian recipes"})), {"Chicken Pasta"})

    def test_search_diet_and_category(self):
        result = self.titles(self.client.get(reverse("recipes:search"), {"q": "vegetarian dinner"}))
        self.assertEqual(result, {"Veggie Curry"})

    def test_search_plural_and_category(self):
        self.assertEqual(self.titles(self.client.get(reverse("recipes:search"), {"q": "desserts"})), {"Chocolate Cake"})

    def test_search_quick_keyword_limits_time(self):
        self.assertEqual(self.titles(self.client.get(reverse("recipes:search"), {"q": "quick breakfast"})), {"Morning Oats"})

    def test_search_no_results(self):
        response = self.client.get(reverse("recipes:search"), {"q": "zzzz"})
        self.assertContains(response, "No recipes match")

    # --- filters ---
    def test_filter_category_and_cuisine_combine(self):
        r = self.client.get(reverse("recipes:list"), {"category": "dinner", "cuisine": "indian"})
        self.assertEqual(self.titles(r), {"Veggie Curry"})

    def test_filter_multiple_diets_are_and(self):
        r = self.client.get(reverse("recipes:list"), {"diet": ["vegetarian", "vegan"]})
        self.assertEqual(self.titles(r), {"Veggie Curry"})

    def test_filter_difficulty(self):
        r = self.client.get(reverse("recipes:list"), {"difficulty": "hard"})
        self.assertEqual(self.titles(r), {"Chocolate Cake"})

    def test_filter_time(self):
        self.assertEqual(self.titles(self.client.get(reverse("recipes:list"), {"time": "15"})), {"Morning Oats"})
        self.assertEqual(self.titles(self.client.get(reverse("recipes:list"), {"time": "60plus"})), {"Veggie Curry", "Chocolate Cake"})

    def test_sort_by_calories(self):
        r = self.client.get(reverse("recipes:list"), {"sort": "calories"})
        self.assertEqual(len(r.context["page_obj"]), 4)


class FavoriteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "a@example.com", "pass12345!")
        self.other = User.objects.create_user("bob", "b@example.com", "pass12345!")
        self.recipe = make_recipe("Fav Recipe")

    def test_login_required(self):
        url = reverse("recipes:favorite_toggle", args=[self.recipe.slug])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
        self.assertEqual(Favorite.objects.count(), 0)

    def test_add_and_remove_favorite(self):
        self.client.force_login(self.user)
        url = reverse("recipes:favorite_toggle", args=[self.recipe.slug])
        self.client.post(url)
        self.assertTrue(Favorite.objects.filter(user=self.user, recipe=self.recipe).exists())
        self.client.post(url)
        self.assertFalse(Favorite.objects.filter(user=self.user, recipe=self.recipe).exists())

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("recipes:favorite_toggle", args=[self.recipe.slug])).status_code, 405)

    def test_favorites_page_only_shows_own(self):
        Favorite.objects.create(user=self.other, recipe=self.recipe)
        self.client.force_login(self.user)
        response = self.client.get(reverse("recipes:favorites"))
        self.assertEqual(len(response.context["page_obj"]), 0)
        Favorite.objects.create(user=self.user, recipe=self.recipe)
        response = self.client.get(reverse("recipes:favorites"), {"q": "fav"})
        self.assertEqual(len(response.context["page_obj"]), 1)

    def test_duplicate_favorite_blocked_by_constraint(self):
        Favorite.objects.create(user=self.user, recipe=self.recipe)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=self.user, recipe=self.recipe)

    def test_open_redirect_is_ignored(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("recipes:favorite_toggle", args=[self.recipe.slug]), {"next": "https://evil.example/"})
        self.assertEqual(response["Location"], self.recipe.get_absolute_url())


class ReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "a@example.com", "pass12345!")
        self.other = User.objects.create_user("bob", "b@example.com", "pass12345!")
        self.recipe = make_recipe("Reviewed Recipe")
        self.url = reverse("recipes:review_save", args=[self.recipe.slug])

    def test_create_review_and_average(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"rating": 4, "comment": "Nice"})
        Review.objects.create(user=self.other, recipe=self.recipe, rating=5)
        response = self.client.get(self.recipe.get_absolute_url())
        self.assertEqual(response.context["recipe"].review_count, 2)
        self.assertAlmostEqual(response.context["recipe"].avg_rating, 4.5)

    def test_posting_again_updates_instead_of_duplicating(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"rating": 2, "comment": "Meh"})
        self.client.post(self.url, {"rating": 5, "comment": "Better on second try"})
        self.assertEqual(Review.objects.filter(user=self.user, recipe=self.recipe).count(), 1)
        self.assertEqual(Review.objects.get(user=self.user).rating, 5)

    def test_duplicate_blocked_at_database_level(self):
        Review.objects.create(user=self.user, recipe=self.recipe, rating=3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(user=self.user, recipe=self.recipe, rating=4)

    def test_invalid_rating_rejected(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"rating": 9})
        self.assertEqual(Review.objects.count(), 0)

    def test_delete_own_review(self):
        Review.objects.create(user=self.user, recipe=self.recipe, rating=3)
        self.client.force_login(self.user)
        self.client.post(reverse("recipes:review_delete", args=[self.recipe.slug]))
        self.assertEqual(Review.objects.count(), 0)

    def test_cannot_delete_someone_elses_review(self):
        Review.objects.create(user=self.other, recipe=self.recipe, rating=3)
        self.client.force_login(self.user)
        response = self.client.post(reverse("recipes:review_delete", args=[self.recipe.slug]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Review.objects.count(), 1)

    def test_anonymous_cannot_review(self):
        response = self.client.post(self.url, {"rating": 5})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_review_comment_is_escaped(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"rating": 5, "comment": "<script>alert(1)</script>"})
        response = self.client.get(self.recipe.get_absolute_url())
        self.assertNotContains(response, "<script>alert(1)</script>")
