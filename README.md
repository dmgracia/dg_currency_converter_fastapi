# 💱 Currency Converter (FastAPI)

A **currency conversion API** built with **FastAPI** and **Python**, using live BTC-based exchange rates from the **Binance public API**.  
It computes USD/EUR/GBP cross rates via BTC as an intermediary and caches results to avoid redundant API calls.

Note: Binance’s GBP exchange rates are systematically incorrect, which causes inaccurate results in every conversion that includes GBP.

## 🚀 Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/dmgracia/dg_currency_converter_fastapi.git
cd dg_currency_converter_fastapi
pip install -r requirements.txt

▶️ Running the Application

To start the API using uvicorn:

uvicorn app:app --reload


Once running, open your browser at:

http://127.0.0.1:8000/docs


This interactive Swagger UI lets you test the endpoints directly.

🧭 Quick start

# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API
uvicorn app:app --reload

# 3. Open this URL in your browser
http://127.0.0.1:8000/docs


🔍 Endpoints
/convert

Converts an amount between USD, EUR, and GBP.

Example:

GET /convert?ccy_from=USD&ccy_to=EUR&quantity=100


Response:

{
  "quantity": 91.58,
  "ccy": "EUR"
}

⚠️ Notes on GBP Data

The GBP quotes provided by Binance are consistently inaccurate,
which causes incorrect conversion values for any pairs involving GBP.
The application deliberately uses Binance’s raw data, as specified in the assignment,
without applying external corrections.

🔍 Endpoints
/convert

Converts an amount between USD, EUR, and GBP.

Example:

GET /convert?ccy_from=USD&ccy_to=EUR&quantity=100


Response:

{
  "quantity": 91.58,
  "ccy": "EUR"
}

/rates

Returns the cached raw Binance prices and the derived cross rates.
Useful for debugging and development.

⚠️ Notes on GBP Data

The GBP quotes provided by Binance are consistently inaccurate,
which causes incorrect conversion values for any pairs involving GBP.
The application deliberately uses Binance’s raw data, as specified in the assignment,
without applying external corrections.


