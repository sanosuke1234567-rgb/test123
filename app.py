from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from flask import Flask, redirect, render_template, request, url_for

DB_PATH = Path(__file__).with_name("data.db")

app = Flask(__name__)


@dataclass
class Ingredient:
    id: int
    name: str
    carbs: float
    protein: float
    fat: float
    calories: float


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                carbs REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL NOT NULL,
                calories REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                servings INTEGER NOT NULL,
                recipe_date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recipe_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                weight_g REAL NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipes(id),
                FOREIGN KEY(ingredient_id) REFERENCES ingredients(id)
            );
            """
        )

        cur = conn.execute("SELECT COUNT(*) FROM ingredients")
        if cur.fetchone()[0] == 0:
            seed_ingredients(conn)


def seed_ingredients(conn: sqlite3.Connection) -> None:
    ingredients = [
        ("白米饭", 28.6, 2.6, 0.3),
        ("鸡胸肉", 0.0, 31.0, 3.6),
        ("鸡蛋", 1.1, 13.0, 11.0),
        ("牛奶", 5.0, 3.4, 3.6),
        ("燕麦", 66.3, 16.9, 6.9),
        ("西兰花", 6.6, 2.8, 0.4),
        ("胡萝卜", 9.6, 0.9, 0.2),
        ("土豆", 17.6, 2.0, 0.1),
        ("苹果", 13.8, 0.3, 0.2),
        ("香蕉", 22.8, 1.1, 0.3),
        ("豆腐", 2.8, 8.1, 4.8),
        ("橄榄油", 0.0, 0.0, 100.0),
    ]
    with conn:
        conn.executemany(
            """
            INSERT INTO ingredients (name, carbs, protein, fat, calories)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (name, carbs, protein, fat, calculate_calories(carbs, protein, fat))
                for name, carbs, protein, fat in ingredients
            ],
        )


def calculate_calories(carbs: float, protein: float, fat: float) -> float:
    return round(carbs * 4 + protein * 4 + fat * 9, 1)


def load_ingredients(conn: sqlite3.Connection) -> list[Ingredient]:
    cur = conn.execute(
        "SELECT id, name, carbs, protein, fat, calories FROM ingredients ORDER BY name"
    )
    return [
        Ingredient(
            id=row["id"],
            name=row["name"],
            carbs=row["carbs"],
            protein=row["protein"],
            fat=row["fat"],
            calories=row["calories"],
        )
        for row in cur.fetchall()
    ]


def parse_date(value: str | None) -> str:
    if value:
        return value
    return dt.date.today().isoformat()


def compute_recipe_totals(conn: sqlite3.Connection, recipe_id: int) -> dict[str, float]:
    cur = conn.execute(
        """
        SELECT weight_g, carbs, protein, fat, calories
        FROM recipe_items
        JOIN ingredients ON ingredients.id = recipe_items.ingredient_id
        WHERE recipe_id = ?
        """,
        (recipe_id,),
    )
    totals = {"carbs": 0.0, "protein": 0.0, "fat": 0.0, "calories": 0.0}
    for row in cur.fetchall():
        factor = row["weight_g"] / 100
        totals["carbs"] += row["carbs"] * factor
        totals["protein"] += row["protein"] * factor
        totals["fat"] += row["fat"] * factor
        totals["calories"] += row["calories"] * factor
    return {key: round(value, 1) for key, value in totals.items()}


def fetch_day_recipes(conn: sqlite3.Connection, recipe_date: str) -> list[dict[str, object]]:
    cur = conn.execute(
        """
        SELECT id, name, servings
        FROM recipes
        WHERE recipe_date = ?
        ORDER BY id DESC
        """,
        (recipe_date,),
    )
    recipes: list[dict[str, object]] = []
    for row in cur.fetchall():
        totals = compute_recipe_totals(conn, row["id"])
        per_person = {
            key: round(value / row["servings"], 1) if row["servings"] else 0.0
            for key, value in totals.items()
        }
        recipes.append(
            {
                "id": row["id"],
                "name": row["name"],
                "servings": row["servings"],
                "totals": totals,
                "per_person": per_person,
                "items": fetch_recipe_items(conn, row["id"]),
            }
        )
    return recipes


def fetch_recipe_items(conn: sqlite3.Connection, recipe_id: int) -> list[dict[str, object]]:
    cur = conn.execute(
        """
        SELECT ingredients.name, weight_g, carbs, protein, fat, calories
        FROM recipe_items
        JOIN ingredients ON ingredients.id = recipe_items.ingredient_id
        WHERE recipe_id = ?
        """,
        (recipe_id,),
    )
    items = []
    for row in cur.fetchall():
        factor = row["weight_g"] / 100
        items.append(
            {
                "name": row["name"],
                "weight_g": row["weight_g"],
                "carbs": round(row["carbs"] * factor, 1),
                "protein": round(row["protein"] * factor, 1),
                "fat": round(row["fat"] * factor, 1),
                "calories": round(row["calories"] * factor, 1),
            }
        )
    return items


def compute_day_totals(recipes: Iterable[dict[str, object]]) -> dict[str, float]:
    totals = {"carbs": 0.0, "protein": 0.0, "fat": 0.0, "calories": 0.0}
    for recipe in recipes:
        recipe_totals = recipe["totals"]
        totals["carbs"] += recipe_totals["carbs"]
        totals["protein"] += recipe_totals["protein"]
        totals["fat"] += recipe_totals["fat"]
        totals["calories"] += recipe_totals["calories"]
    return {key: round(value, 1) for key, value in totals.items()}


init_db()


@app.route("/")
def index() -> str:
    recipe_date = parse_date(request.args.get("date"))
    conn = get_connection()
    ingredients = load_ingredients(conn)
    recipes = fetch_day_recipes(conn, recipe_date)
    day_totals = compute_day_totals(recipes)
    return render_template(
        "index.html",
        recipe_date=recipe_date,
        ingredients=ingredients,
        recipes=recipes,
        day_totals=day_totals,
    )


@app.route("/recipes", methods=["POST"])
def add_recipe() -> str:
    name = request.form.get("name", "").strip()
    servings = int(request.form.get("servings", 1))
    recipe_date = parse_date(request.form.get("recipe_date"))

    ingredient_ids = request.form.getlist("ingredient_id")
    weights = request.form.getlist("weight_g")

    if not name or not ingredient_ids:
        return redirect(url_for("index", date=recipe_date))

    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO recipes (name, servings, recipe_date) VALUES (?, ?, ?)",
            (name, servings, recipe_date),
        )
        recipe_id = cur.lastrowid

        for ingredient_id, weight in zip(ingredient_ids, weights):
            weight_value = float(weight)
            conn.execute(
                """
                INSERT INTO recipe_items (recipe_id, ingredient_id, weight_g)
                VALUES (?, ?, ?)
                """,
                (recipe_id, int(ingredient_id), weight_value),
            )

    return redirect(url_for("index", date=recipe_date))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
