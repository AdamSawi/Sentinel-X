from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sqlite3
from datetime import datetime

import pandas as pd
from sklearn.linear_model import LinearRegression


app = FastAPI(title="SENTINEL-X Thermal Monitoring")

DB_NAME = "sentinel.db"



class TemperatureData(BaseModel):
    temperature: float


def init_database():

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temperature_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


init_database()



def predict_temperature():

    connection = sqlite3.connect(DB_NAME)

    df = pd.read_sql_query("""
        SELECT temperature
        FROM temperature_logs
        ORDER BY id ASC
    """, connection)

    connection.close()

    
    if len(df) < 3:

        return {
            "prediction": None,
            "risk": False,
            "message": "Pas assez de données"
        }

  
    df["time_index"] = range(len(df))

    X = df[["time_index"]]
    y = df["temperature"]

  
    model = LinearRegression()

    
    model.fit(X, y)

   
    next_index = [[len(df)]]

    prediction = model.predict(next_index)[0]

    current_temperature = float(df["temperature"].iloc[-1])

    SEUIL = 70.0

    if current_temperature > SEUIL:

        risk = True
        message = "ALERTE : température actuelle critique"

    elif prediction > SEUIL:

        risk = True
        message = "ALERTE : risque de surchauffe prévu"

    else:

        risk = False
        message = "Situation normale"

    return {
        "prediction": round(float(prediction), 2),
        "risk": risk,
        "message": message
    }

app.mount(
    "/dashboard",
    StaticFiles(directory="dashboard", html=True),
    name="dashboard"
)


@app.get("/")
def home():

    return {
        "system": "SENTINEL-X",
        "status": "Server running"
    }


@app.post("/temperature")
def receive_temperature(data: TemperatureData):

    temperature = data.temperature

    if temperature > 70:

        status = "ALERTE SURCHAUFFE"

    else:

        status = "NORMAL"


    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO temperature_logs
        (timestamp, temperature, status)
        VALUES (?, ?, ?)
    """, (timestamp, temperature, status))

    connection.commit()
    connection.close()


    prediction = predict_temperature()


    print(f"Temperature : {temperature} °C")
    print(f"Etat : {status}")
    print(f"Heure : {timestamp}")
    print(f"Prediction IA : {prediction}")
    print("--------------------")


    return {

        "temperature": temperature,

        "status": status,

        "timestamp": timestamp,

        "ai_prediction": prediction
    }



@app.get("/temperatures")
def get_temperatures():

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, timestamp, temperature, status
        FROM temperature_logs
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    connection.close()


    temperatures = []


    for row in rows:

        temperatures.append({

            "id": row[0],

            "timestamp": row[1],

            "temperature": row[2],

            "status": row[3]
        })


    return temperatures



@app.get("/ai/prediction")
def get_ai_prediction():

    return predict_temperature()