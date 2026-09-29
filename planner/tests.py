import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from recipes.factories import make_recipe

from .models import MealPlan
from .services import generate_plan

User = get_user_model()
MONDAY = datetime.date(2030, 1, 7)  # a Monday


class MealPlannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "a@example.com", "pass12345!")
        self.other = User.objects.create_user("bob", "b@example.com", "pass12345!")
        self.breakfast = make_recipe("Oats", "Breakfast", calories=300)
        self.lunch = make_recipe("Salad Bowl", "Salad", calories=400)
        self.dinner = make_recipe("Roast Chicken", "Dinner", calories=700)
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("planner:week")).status_code, 302)

    def test_add_meal(self):
        response = self.client.post(reverse("planner:add"), {"recipe": self.dinner.pk, "date": "2030-01-08", "meal_type": "dinner"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MealPlan.objects.get().recipe, self.dinner)

    def test_adding_to_occupied_slot_replaces(self):
        MealPlan.objects.create(user=self.user, date=MONDAY, meal_type="dinner", recipe=self.dinner)
        self.client.post(reverse("planner:add"), {"recipe": self.lunch.pk, "date": MONDAY.isoformat(), "meal_type": "dinner"})
        self.assertEqual(MealPlan.objects.count(), 1)
        self.assertEqual(MealPlan.objects.get().recipe, self.lunch)

    def test_remove_meal(self):
        plan = MealPlan.objects.create(user=self.user, date=MONDAY, meal_type="lunch", recipe=self.lunch)
        self.client.post(reverse("planner:remove", args=[plan.pk]))
        self.assertEqual(MealPlan.objects.count(), 0)

    def test_cannot_remove_or_toggle_other_users_meal(self):
        plan = MealPlan.objects.create(user=self.other, date=MONDAY, meal_type="lunch", recipe=self.lunch)
        self.assertEqual(self.client.post(reverse("planner:remove", args=[plan.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("planner:cooked", args=[plan.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("planner:regenerate", args=[plan.pk])).status_code, 404)
        self.assertEqual(MealPlan.objects.count(), 1)

    def test_weekly_view_and_navigation(self):
        MealPlan.objects.create(user=self.user, date=MONDAY, meal_type="breakfast", recipe=self.breakfast)
        MealPlan.objects.create(user=self.other, date=MONDAY, meal_type="lunch", recipe=self.lunch)
        response = self.client.get(reverse("planner:week"), {"week": "2030-01-09"})  # a Wednesday
        self.assertEqual(response.context["week_start"], MONDAY)
        self.assertEqual(response.context["planned_count"], 1)
        self.assertContains(response, "Oats")
        self.assertNotContains(response, "Salad Bowl")
        self.assertEqual(response.context["next_week"], "2030-01-14")
        self.assertEqual(response.context["prev_week"], (MONDAY - datetime.timedelta(days=7)).isoformat())

    def test_toggle_cooked(self):
        plan = MealPlan.objects.create(user=self.user, date=MONDAY, meal_type="lunch", recipe=self.lunch)
        self.client.post(reverse("planner:cooked", args=[plan.pk]))
        plan.refresh_from_db()
        self.assertTrue(plan.is_cooked)

    def test_generate_plan_fills_slots_using_matching_categories(self):
        created, skipped = generate_plan(self.user, {"meals_per_day": 3}, MONDAY, 2)
        self.assertEqual((created, skipped), (6, 0))
        plans = {(p.date, p.meal_type): p.recipe for p in MealPlan.objects.filter(user=self.user)}
        self.assertEqual(plans[(MONDAY, "breakfast")], self.breakfast)
        self.assertEqual(plans[(MONDAY, "dinner")], self.dinner)

    def test_generate_keeps_existing_unless_replace(self):
        MealPlan.objects.create(user=self.user, date=MONDAY, meal_type="dinner", recipe=self.breakfast)
        created, skipped = generate_plan(self.user, {"meals_per_day": 3}, MONDAY, 1)
        self.assertEqual((created, skipped), (2, 1))
        self.assertEqual(MealPlan.objects.get(date=MONDAY, meal_type="dinner").recipe, self.breakfast)
        generate_plan(self.user, {"meals_per_day": 3}, MONDAY, 1, replace_existing=True)
        self.assertEqual(MealPlan.objects.get(date=MONDAY, meal_type="dinner").recipe, self.dinner)

    def test_generate_view_and_no_matches(self):
        response = self.client.post(reverse("planner:generate"), {
            "start_date": "2030-01-07", "days": 2, "meals_per_day": 3, "difficulty": "hard"})
        self.assertEqual(response.status_code, 200)  # nothing is hard -> error shown, stays on form
        self.assertContains(response, "No recipes match")
        response = self.client.post(reverse("planner:generate"), {
            "start_date": "2030-01-07", "days": 2, "meals_per_day": 3, "difficulty": ""})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MealPlan.objects.filter(user=self.user).count(), 6)

    def test_regenerate_single_meal(self):
        other_dinner = make_recipe("Beef Stew", "Dinner", calories=650)
        plan = MealPlan.objects.create(user=self.user, date=MONDAY, meal_type="dinner", recipe=self.dinner)
        self.client.post(reverse("planner:regenerate", args=[plan.pk]))
        plan.refresh_from_db()
        self.assertEqual(plan.recipe, other_dinner)
