# itransition-task5

Mining extraction dashboard, statistical anomaly detection suite, and automated PDF audit report generator.

- **Google Spreadsheet (Formula Generator):** [Public Sheet](https://docs.google.com/spreadsheets/d/105EFki4awWcuEKCouSRobgXg-MvGx4xPOUaRTo05Shg/edit)
- **Live Streamlit Dashboard:** `https://itransition-task5.streamlit.app/`

### Features
- Dynamic extraction model with statistical distributions, weekday cycles, exponential trends, and compound event shocks.
- Multi-method anomaly detection: IQR rule, Z-score thresholding, Centered Moving Average deviation, and Grubbs' maximum normalized residual test.
- Interactive Plotly visualizations (Line, Bar, Stacked Area) with degree 1-4 polynomial trendlines.
- Production Typst PDF audit generator with corporate extraction tables and high-DPI rasterized charts.
- Strict architecture adhering to micro-functions (<= 5 lines per function) and 100% Ruff compliance.

### Local Setup & Execution
```bash
pip install -r requirements.txt
streamlit run app.py
```
