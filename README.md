# Product Web Scraper
Product Web Scraper is a Python tool designed to extract product data from three major e-commerce websites: **Aliexpress, Amazon, and eBay**. This scraper gathers detailed information such as product name, price, and link, saving the data in a CSV file. Additionally, it generates a PNG pie chart visualizing different price groups, facilitating easy price comparisons.

### Features
- **Multi-Website Scraping**: Supports data extraction from Aliexpress, Amazon, and eBay.
- **Price Conversion**: Automatically converts all collected prices to your selected currency.
- **CSV Export**: Saves the scraped data in a well-structured CSV format.
- **Visual Analysis**: Generates a pie chart image for a quick comparison of price distributions.

### Currencies supported
Choose your preferred currency, and the script will convert all price data accordingly using a api
- **USD** - US Dollar ($)
- **EUR** - Euro (€)
- **GBP** - British Pound (£)
- **JPY** - Japanese Yen (¥)
- **KRW** - South Korean Won (₩)
- **INR** - Indian Rupee (₹)
- **RUB** - Russian Ruble (₽)
- **PHP** - Philippine Peso (₱)
- **BRL** - Brazilian Real (R$)
- **BTC** - Bitcoin (₿)

### Installation
To get started, clone this repository and install the required dependencies:
1. `git clone https://github.com/yourusername/product-web-scraper.git`<br>
2. `cd product-web-scraper`<br>
3. `pip install -r requirements.txt`

### How to use
Run the products_webscrap.py script:
`python3 products_webscrap.py`<br><br>
You will be prompted to provide the following information:
1. **Product Name**: The name of the product you want to search for.
2. **Currency Code**: The abbreviation of your preferred currency (e.g., USD, EUR).
3. **Remove Currency Symbol**: Choose whether to remove the currency symbol in the CSV output (yes/no).
4. **Number of Pages**: Specify the number of pages to scrape from each website.

Once you've provided the required information, the script will start scraping the data and will generate a CSV file and a PNG pie chart at the end.

### Currency Conversion
This project uses the [Exchange-API by Fawaz Ahmed](https://github.com/fawazahmed0/exchange-api) for real-time currency conversion. This allows the script to accurately convert product prices to your selected currency during the scraping process.

### Requirements
- Python 3.x<br>
- **Libraries**: beautifulsoup4, matplotlib, numpy, playwright, Requests, scikit_learn

### License
This project is licensed under the Apache-2.0 license.
