# AirVue: Real-Time Air Quality Prediction & Health Advisory

AirVue is an advanced, real-time Air Quality Index (AQI) monitoring and forecasting platform designed for India. It integrates live monitoring data with four distinct Artificial Intelligence models to predict pollution levels up to 48 hours in advance, providing dynamic health advisories based on the user's selected demographic.

## 🚀 Features

*   **Live AQI & Weather Dashboard:** Real-time air quality and weather tracking for major Indian cities using AQICN and WeatherAPI.com.
*   **Aesthetic Glassmorphism UI:** A premium, modern interface with dynamic weather widgets, glass-effect cards, and smooth micro-animations.
*   **Interactive Map:** A dynamic Leaflet.js map with color-coded markers and nearby station detection.
*   **Multi-Model Forecasting:** Switch seamlessly between four predictive models to view 48-hour AQI forecasts with integrated weather data:
    *   **XGBoost (Default):** Lightning-fast gradient boosting for detecting immediate, non-linear pollution spikes.
    *   **CNN-LSTM:** Deep learning hybrid that identifies complex, hidden temporal patterns in recent pollution sequences.
    *   **BiLSTM:** Advanced neural network that analyzes pollution momentum in both forward and backward time directions.
    *   **ARIMAX:** Classical statistical model ensuring mathematically stable, linear forecasting against historical variance.
*   **Weather-Integrated Predictions:** Real-time and forecasted weather (temperature, humidity, precipitation) are displayed alongside AQI forecasts for a holistic environmental view.
*   **Personalized Health Advisory:** Select from demographic profiles to receive tailored, actionable health recommendations.

## 🛠️ Technology Stack

*   **Frontend:** HTML5, CSS3, Vanilla JavaScript (Chart.js, Leaflet.js).
*   **Backend:** Python 3.10+, Flask, RESTful APIs.
*   **Machine Learning:** Scikit-Learn (XGBoost), TensorFlow/Keras (Deep Learning), Statsmodels (ARIMAX).
*   **Data Processing:** Pandas, NumPy.

## ⚙️ Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/VictorVikram007/realm-1.git
    cd realm-1
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # On Windows
    source venv/bin/activate  # On Mac/Linux
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download the Datasets:**
    *   Due to GitHub file size limits, the core datasets (`station_day.csv`, `city_day.csv`) are not included in this repository.
    *   You must download the historical Indian AQI datasets and place them in the root directory.

5.  **Train the Models (Optional):**
    *   If the pre-trained models exist in `backend/models`, you can skip this step.
    *   To retrain: `python backend/train.py --model all`

6.  **Run the Server:**
    ```bash
    python backend/app.py
    ```
    The application will automatically open in your browser at `http://localhost:5000/`.

## 🚀 Deploy on Render

This repository includes a `render.yaml` and `Procfile` for deploying the backend as a Render web service.

1.  In Render, create a new Web Service and connect this GitHub repository.
2.  Use the repository root as the project root.
3.  Render will install dependencies from `backend/requirements.txt`.
4.  The service will start with `gunicorn backend.app:app --bind 0.0.0.0:$PORT`.
5.  Make sure the dataset CSV files remain in the repository root so the API can load city and station data.

If you deploy without the datasets, the API will still start, but endpoints like `/api/cities` and `/api/predict/<city>` will return empty or not-found responses until the CSV files are added.

## 📌 Architecture

The frontend requests prediction data via REST API endpoints (`/api/predict/<city>`). The Flask backend uses a lazy-loading multi-model registry to instantly serve predictions from the selected pre-trained AI architecture stored in `backend/models/`.

## 📜 License
@VictorVikram007
