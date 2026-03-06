# AirVue: Real-Time Air Quality Prediction & Health Advisory

AirVue is an advanced, real-time Air Quality Index (AQI) monitoring and forecasting platform designed for India. It integrates live monitoring data with four distinct Artificial Intelligence models to predict pollution levels up to 48 hours in advance, providing dynamic health advisories based on the user's selected demographic.

## 🚀 Features

*   **Live AQI Dashboard:** Real-time air quality tracking for major Indian cities using the AQICN API.
*   **Interactive Map:** A dynamic Leaflet.js map with color-coded markers pinpointing individual monitoring stations across the country.
*   **Multi-Model Forecasting:** Switch seamlessly between four predictive models to view 48-hour AQI forecasts:
    *   **XGBoost (Default):** Lightning-fast gradient boosting for detecting immediate, non-linear pollution spikes.
    *   **CNN-LSTM:** Deep learning hybrid that identifies complex, hidden temporal patterns in recent pollution sequences.
    *   **BiLSTM:** Advanced neural network that analyzes pollution momentum in both forward and backward time directions to map cyclonical trends.
    *   **ARIMAX:** Classical statistical model ensuring mathematically stable, linear forecasting against historical variance.
*   **Personalized Health Advisory:** Select from demographic profiles (General Public, Asthmatics, Elderly, Athletes, etc.) to receive tailored, actionable health recommendations based on both current and predicted AQI levels.

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

## 📌 Architecture

The frontend requests prediction data via REST API endpoints (`/api/predict/<city>`). The Flask backend uses a lazy-loading multi-model registry to instantly serve predictions from the selected pre-trained AI architecture stored in `backend/models/`.

## 📜 License
@VictorVikram007
