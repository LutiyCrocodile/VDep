#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import os

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="video_hosting",
    user="user",
    password="password"
)

conn.autocommit = True
cursor = conn.cursor()

# Delete existing positions
cursor.execute("DELETE FROM support.positions")

# Insert positions with correct encoding
positions = [
    ('Руководитель департамента', 'vip', 1),
    ('Заместитель руководителя департамента', 'vip', 2),
    ('Советник руководителя департамента', 'vip', 3),
    ('Начальник управления', 'vip', 4),
    ('Заместитель начальника управления', 'high', 5),
    ('Консультант начальника управления', 'high', 6),
    ('Советник начальника управления', 'high', 7),
    ('Начальник отдела', 'high', 8),
    ('Заместитель начальника отдела', 'medium', 9),
    ('Консультант начальника отдела', 'medium', 10),
    ('Советник начальника отдела', 'medium', 11),
    ('Главный специалист', 'medium', 12),
    ('Специалисты 1-й, 2-й , 3-й категорий', 'low', 13),
    ('Документоведы', 'low', 14),
    ('Стажеры', 'low', 15),
]

for name, priority, sort_order in positions:
    cursor.execute(
        "INSERT INTO support.positions (name, priority, sort_order) VALUES (%s, %s, %s)",
        (name, priority, sort_order)
    )

# Verify
cursor.execute("SELECT id, name, priority FROM support.positions ORDER BY sort_order")
results = cursor.fetchall()
for row in results:
    print(row)

cursor.close()
conn.close()
print("Positions updated successfully!")
