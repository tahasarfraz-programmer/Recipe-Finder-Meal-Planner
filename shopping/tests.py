import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planner.models import MealPlan
from recipes.factories import add_ingredient, make_recipe

from .models import ShoppingListItem

User = get_user_model()


class ShoppingListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "a@example.com", "pass12345!")
        self.other = User.objects.create_user("bob", "b@example.com", "pass12345!")
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("shopping:list")).status_code, 302)

    def test_add_item_and_grouping(self):
        self.client.post(reverse("shopping:add"), {"name": "Milk", "quantity": "2", "unit": "l", "category": "dairy"})
        item = ShoppingListItem.objects.get()
        self.assertEqual(item.user, self.user)
        response = self.client.get(reverse("shopping:list"))
        self.assertEqual(response.context["groups"][0]["label"], "Dairy & Eggs")
        self.assertContains(response, "Milk")

    def test_edit_item(self):
        item = ShoppingListItem.objects.create(user=self.user, name="Rice", category="grains")
        self.client.post(reverse("shopping:edit", args=[item.pk]), {"name": "Basmati rice", "quantity": "1", "unit": "kg", "category": "grains"})
        item.refresh_from_db()
        self.assertEqual(item.name, "Basmati rice")

    def test_toggle_purchased_and_clear_purchased(self):
        keep = ShoppingListItem.objects.create(user=self.user, name="Eggs")
        done = ShoppingListItem.objects.create(user=self.user, name="Butter")
        self.client.post(reverse("shopping:toggle", args=[done.pk]))
        done.refresh_from_db()
        self.assertTrue(done.is_purchased)
        self.client.post(reverse("shopping:clear_purchased"))
        self.assertEqual(list(ShoppingListItem.objects.all()), [keep])

    def test_delete_item_and_clear_all(self):
        a = ShoppingListItem.objects.create(user=self.user, name="A")
        ShoppingListItem.objects.create(user=self.user, name="B")
        self.client.post(reverse("shopping:delete", args=[a.pk]))
        self.assertEqual(ShoppingListItem.objects.count(), 1)
        self.client.post(reverse("shopping:clear_all"))
        self.assertEqual(ShoppingListItem.objects.count(), 0)

    def test_cannot_touch_other_users_items(self):
        item = ShoppingListItem.objects.create(user=self.other, name="Secret")
        self.assertEqual(self.client.post(reverse("shopping:toggle", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("shopping:delete", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("shopping:edit", args=[item.pk])).status_code, 404)
        self.client.post(reverse("shopping:clear_all"))
        self.assertTrue(ShoppingListItem.objects.filter(pk=item.pk).exists())

    def test_generate_from_plan_merges_quantities_and_is_repeatable(self):
        monday = datetime.date(2030, 1, 7)
        r1 = make_recipe("Recipe One", servings=4)
        r2 = make_recipe("Recipe Two", "Lunch", servings=4)
        add_ingredient(r1, "Tomato", "2", "", "vegetables")
        add_ingredient(r2, "Tomato", "3", "", "vegetables")
        add_ingredient(r1, "Salt", "1", "tsp", "spices")
        MealPlan.objects.create(user=self.user, date=monday, meal_type="dinner", recipe=r1)
        MealPlan.objects.create(user=self.user, date=monday, meal_type="lunch", recipe=r2)
        payload = {"start": "2030-01-07", "end": "2030-01-13"}
        for _ in range(2):  # generating twice must not double quantities
            self.client.post(reverse("shopping:generate"), payload)
        tomato = ShoppingListItem.objects.get(name="Tomato")
        self.assertEqual(tomato.quantity, Decimal("5.00"))
        self.assertEqual(tomato.category, "vegetables")
        self.assertEqual(ShoppingListItem.objects.count(), 2)

    def test_generate_with_empty_plan(self):
        response = self.client.post(reverse("shopping:generate"), {"start": "2030-01-07", "end": "2030-01-13"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ShoppingListItem.objects.count(), 0)
