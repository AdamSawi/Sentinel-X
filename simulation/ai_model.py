import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression

DB_NAME = "sentinel.db"

connection = sqlite3.connect(DB_NAME)

df = pd.read_sql_query("""
    SELECT timestamp, temperature
    FROM temperature_logs
    ORDER BY id ASC
""", connection)

connection.close()

if len(df) < 3:
    print("Pas assez de données pour entraîner le modèle.")
    print(f"Données disponibles : {len(df)}")
    exit()

df["time_index"] = range(len(df))


X = df[["time_index"]]
y = df["temperature"]

model = LinearRegression()

model.fit(X, y)

next_index = [[len(df)]]

prediction = model.predict(next_index)[0]

print("===================================")
print("     SENTINEL-X - IA PREDICTIVE")
print("===================================")

print(f"Nombre de mesures : {len(df)}")

print(f"Dernière température : {df['temperature'].iloc[-1]:.2f} °C")

print(f"Température prédite : {prediction:.2f} °C")

if prediction > 70:

    print("⚠️ PRÉ-ALERTE : risque de dépasser 70°C")

else:

    print("✅ Situation normale")