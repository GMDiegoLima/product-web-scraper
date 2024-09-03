import sys
import csv
import time
import locale
import logging
import requests
import numpy as np
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

remove_currency_from_csv:bool = True
locale.setlocale(locale.LC_ALL, '')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
api_all_currencies:dict = requests.get('https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies.json').json()
headers:dict = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0'} # Define the user agent header for your requests
symbols_hash_map:dict = {
    '$': 'usd',
    '€': 'eur',
    '£': 'gbp',
    '¥': 'jpy',
    '₩': 'krw',
    '₹': 'inr',
    '₽': 'rub',
    '₱': 'php',
    'R$': 'brl',
    '₿': 'btc'
} # supported currencies, used to convert from symbols to currency code and vice versa

def convert_price(price_data:str, source_url:str) -> str | None:
    original_symbol:str = ''.join([symbol for symbol in price_data if not symbol.isdigit() and symbol not in ('.', ',', 'a', 'to')])[:2]
    original_currency:str = symbols_hash_map[original_symbol]
    value_without_symbol:str = price_data.replace(original_symbol, '')
    if remove_currency_from_csv:
        if 'aliexpress' == source_url:
            return f'{locale.atof(value_without_symbol)/api_url_for_currencies[currency][original_currency]:.2f}'
        if 'ebay' == source_url:
            price_value:list[str] = value_without_symbol.replace(' ', '').replace('a', ';').replace('to', ';').replace(u'\xa0', '').split(';')
            return ', '.join(map(lambda x: f"{locale.atof(x)/api_url_for_currencies[currency][original_currency]:.2f}", price_value))
        if 'amazon' == source_url:
            return f"{float(value_without_symbol if ',' not in value_without_symbol else value_without_symbol.replace(',', ''))/api_url_for_currencies[currency][original_currency]:.2f}"
    else:
        if 'aliexpress' == source_url:
            return f'{currency_symbol} {locale.atof(value_without_symbol)/api_url_for_currencies[currency][original_currency]:.2f}'
        if 'ebay' == source_url:
            price_value:list[str] = value_without_symbol.replace(' ', '').replace('a', ';').replace('to', ';').replace(u'\xa0', '').split(';')
            return ', '.join(map(lambda x: f"{currency_symbol} {locale.atof(x)/api_url_for_currencies[currency][original_currency]:.2f}", price_value))
        if 'amazon' == source_url:
            return f"{currency_symbol} {float(value_without_symbol if ',' not in value_without_symbol else value_without_symbol.replace(',', ''))/api_url_for_currencies[currency][original_currency]:.2f}"

def parse_amazon(target_url) -> list[dict]:
    data:list = []
    with sync_playwright() as pw:
        # Launch new browser
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to Amazon URL and extract data
        page.goto(target_url)
        try:
            items = page.query_selector_all('div.a-section.a-spacing-small')
            for item in items:
                if item.query_selector('h2.a-size-mini > a > span'):
                    item_data = {
                        'Name': item.query_selector('h2.a-size-mini > a > span').inner_text(),
                        'Price': convert_price(item.query_selector('span.a-price > span.a-offscreen').inner_text(), 'amazon'),
                        'Link': f'https://amazon.com{item.query_selector('h2.a-size-mini > a').get_attribute('href')}'
                    }
                    data.append(item_data)
            browser.close()
        except AttributeError as e:
            logging.warning(f"Skipping item due to missing data: {e}")
    return data

def parse_aliexpress(soup: BeautifulSoup) -> list[dict]:
    # check if the href url from the item has https at the begin
    def check_https(href_url:str) -> str:
        if href_url.startswith('https:'):
            return href_url
        return f'https:{href_url}'

    data:list = []
    items = soup.find_all('div', class_='list--gallery--C2f2tvm search-item-card-wrapper-gallery')
    for item in items:
        try:
            item_data = {
                'Name': item.find('h3', class_='multi--titleText--nXeOvyr').text.strip(),
                'Price': convert_price(item.find('div', class_='multi--price-sale--U-S0jtj').text.strip(), 'aliexpress'),
                'Link': check_https(item.find('a', href=True)['href'])
            }
            data.append(item_data)
        except AttributeError as e:
            logging.warning(f"Skipping item due to missing data: {e}")
    return data

def parse_ebay(soup: BeautifulSoup) -> list[dict]:
    data:list = []
    items = soup.find_all('li', class_='s-item s-item__pl-on-bottom')
    for item in items:
        # Check if it is a valid product with a valid price (price bigger than 0.00)
        if item.find('div', class_='s-item__title').text.strip() != 'Shop on eBay':
            try:
                item_data = {
                    'Name': item.find('div', class_='s-item__title').text.strip(),
                    'Price': convert_price(item.find('span', class_='s-item__price').text.strip(), 'ebay'),
                    'Link': item.find('a', href=True)['href']
                }
                data.append(item_data)
            except AttributeError as e:
                logging.warning(f"Skipping item due to missing data: {e}")
    return data

def parse_html(html: str|bytes, target_url:str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    if 'aliexpress' in target_url:
        return parse_aliexpress(soup)
    elif 'ebay' in target_url:
        return parse_ebay(soup)
    else:
        logging.warning(f"No parsing logic for {target_url}")
        return []

# Fetch the HTML content of a webpage
def fetch_html(url:str|bytes, headers:dict|None = None) -> str | None:
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

# Orchestrate the scraping
def scrape_website(target_url:str, headers:dict|None = None, pages:int = 1, sleep_time:int = 1) -> list:
    all_data:list = []
    for page in range(1, pages + 1):
        url = f"{target_url}&page={page}"
        logging.info(f"Scraping {url}")
        if url.startswith('https://amazon'):
            all_data.extend(parse_amazon(url))
        else:
            html = fetch_html(url, headers)
            if html:
                data = parse_html(html, target_url)
                all_data.extend(data)
                logging.info(f"Page {page} scraped successfully, {len(data)} items found.")
        time.sleep(sleep_time)
    return all_data

def save_to_csv(data:list[dict], filename:str = 'output.csv'):
    if not data:
        logging.warning("No data to save.")
        return

    def check_keys(data:dict|None) -> list | None:
        if isinstance(data, dict):
            return data.keys()
        return None

    keys = check_keys(data[0])
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if keys:
            writer.writerow(keys)  # Write headers if the data is a list of dicts
            for row in data:
                writer.writerow(row.values())
        else:
            writer.writerows(data)  # Otherwise, write data directly

    logging.info(f"Data saved to {filename}")

def pie_graph(data:list[dict], filename:str):
    if not data:
        logging.warning("No data to create a pie graph.")
        return

    logging.info("Making a pie graph from the data scraped...")
    names:list[str] = []
    prices:list[float] = []
    for item in data:
        if ',' in item['Price']:
            for value in item['Price'].replace(currency_symbol, '').split(', '):
                names.append(item['Name'])
                prices.append(float(value))
        else:
            names.append(item['Name'])
            prices.append(float(item['Price'].replace(currency_symbol, '')))

    numpy_prices:np.array = np.array(prices).reshape(-1, 1)
    kmeans = KMeans(n_clusters=5, random_state=0).fit(prices)
    labels = kmeans.predict(numpy_prices)
    # Count the number of data in each cluster
    unique_labels, counts = np.unique(labels, return_counts=True)
    price_ranges:list[tuple] = [
        (int(numpy_prices[labels == label].min()), int(numpy_prices[labels == label].max()))
        for label in unique_labels]

    labels = [f'Around {currency_symbol}{price_min}-{price_max}' for price_min, price_max in price_ranges]
    plt.figure(figsize=(12, 9), facecolor='black')
    plt.pie(counts, labels=None, autopct='%1.1f%%', startangle=140, textprops={'color': 'black', 'fontsize': 16}, wedgeprops={'edgecolor':'black'})
    plt.title(f'Distribuition of prices (in {currency}) for {search_field} (using K-Means)', color='white', size=22)
    plt.legend(bbox_to_anchor=(1.2, 1), labels=labels, loc='upper right', fontsize='x-large', labelcolor='white', frameon=True, edgecolor='white', facecolor='none')
    plt.tight_layout()
    plt.savefig(filename)
    logging.info(f"Pie graph saved as {filename}")
    return

if __name__ == "__main__":
    search_field:str = str(input(
        '\nPlease, type the product name that you wanna to look for:\n'
        )).lower() # Product name to search for
    if search_field == '':
        print(f'{"-="*35}\n')
        logging.error('Sorry, i need at least one letter to start looking for a product on the websites.')
        sys.exit()

    # Ask for the currency the user wanna to use, check if its a supported one and get the symbol
    supported_currencies:str = "\n".join(f'{abbreviation} ({name})' for abbreviation, name in zip(api_all_currencies.keys(), api_all_currencies.values()) if abbreviation in symbols_hash_map.values())
    currency:str = str(input(
        f'\nPlease, type the abbreviation code of the currency you wanna to use on the price comlumn of the csv file (e.g., usd, gbp, eur, brl)\nThe valid currencies codes are:\n{supported_currencies}\n'
        )).lower()
    if currency not in dict(symbols_hash_map).values():
        print(f'\n{"-="*35}\n')
        logging.error(f'Sorry, i could not find the currency code you typed, please run the script again and make sure you typed the currency abbreviation code right.\nThe currencies code that we support are:\n{supported_currencies}')
        sys.exit()
    currency_symbol:str = [k for k, v in symbols_hash_map.items() if v == currency][0]

    choose_to_remove_currency:str = str(input(
        '\nDo you wanna to remove the currency symbol of each cell of the price comlumn on the csv file?\n Y (Yes) or N (No), default is Y (Yes):\n'
        )).lower()
    if choose_to_remove_currency not in ('no', 'n', 'not', 'na', 'nah' 'y', 'yes', 'yep', 'ye', ''):
        print(f'\n{"-="*35}\n')
        logging.error('Sorry, i only accept Yes, Y, No and N as possible answers')
        sys.exit()
    if choose_to_remove_currency in ('no', 'n', 'not', 'na', 'nah'):
        remove_currency_from_csv = False
    
    pages_to_scrape:int = 3
    try:
        pages_to_scrape:int = int(input('\nHow much page for each website do you wanna to scrap data? (the default is 3):\n'))
    except:
        print(f'\n{"-="*35}\n')
        logging.error('Sorry, i only accept numbers as possible answer')
        sys.exit()

    urls_to_scrape:list[str] = [
    f'https://amazon.com/s?k={search_field}&s=exact-aware-popularity-rank',
    f'https://aliexpress.com/w/wholesale-{search_field}.html?sortType=total_tranpro_desc',
    f'https://ebay.com/sch/i.html?_nkw={search_field}'
    ] # Target websites | aliexpress, amazon and ebay |

    all_scraped_data:list[dict] = []
    api_url_for_currencies:dict = requests.get(f'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{currency}.json').json()
    for url in urls_to_scrape:
        scraped_data = scrape_website(url, headers=headers, pages=pages_to_scrape)
        all_scraped_data.extend(scraped_data)

    save_to_csv(all_scraped_data, 'scraped_data.csv')
    pie_graph(all_scraped_data, 'scraped_data_graph.png')
