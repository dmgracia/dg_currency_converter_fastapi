# 💱 Currency Converter (FastAPI)

A **currency conversion API** built with **FastAPI** and **Python**, using live BTC-based exchange rates from the **Binance public API**.  
It computes USD/EUR/GBP cross rates via BTC as an intermediary and caches results to avoid redundant API calls.

Note: Binance’s GBP exchange rates are systematically incorrect, which causes inaccurate results in every conversion that includes GBP.

---


