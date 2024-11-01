import pandas as pd
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm
from time import sleep
from typing import Dict


class AutoTraderScraper:
    def __init__(self, cars: Dict) -> None:
        self.cars = cars

        chrome_options = Options()
        chrome_options.add_argument("_tt_enable_cookie=1")
        self.driver = webdriver.Chrome()
        self.base_url = "https://www.autotrader.co.uk/car-search?postcode=PO7%203AP&make={make}&model={model}&advertising-location=at_cars"
        self.wait = 2

    def scrape(self) -> pd.DataFrame:
        data = []
        for make, model in self.cars.items():
            url = self.base_url.format(make=make, model=model)
            self.driver.get(url)
            sleep(self.wait)

            content = BeautifulSoup(self.driver.page_source, "html.parser")
            try:
                pagination_next_element = content.find("a", attrs={"data-testid": "pagination-next"})
                number_of_pages = int(pagination_next_element.get("aria-label").split()[-1])
            except:
                print("No results found.")
                continue

            for i in tqdm(range(0, number_of_pages)):
                self.driver.get(url + f"&page={str(i + 1)}")
                sleep(self.wait)

                content = BeautifulSoup(self.driver.page_source, "html.parser")
                articles = content.findAll("section", attrs={"data-testid": "trader-seller-listing"})

                for article in articles:
                    details = {
                        "name": make + " " + model,
                        "price": int(re.search(r"(?:[£](\d+(\,\d{3})?))", article.text).group(1).replace(",","")),
                        "year": None,
                        "reg": None,
                        "mileage": None,
                        "body_type": None,
                        "transmission": None,
                        "fuel": None,
                        "engine": None,
                        "owners": None,
                        "location": None,
                        "distance": None,
                        "link": "https://www.autotrader.co.uk/" + article.find(
                            "a", {"href": re.compile(r'/car-details/')}
                        ).get("href")
                    }

                    try:
                        seller_info = article.find("p", attrs={"data-testid": "search-listing-seller"}).text
                        location = seller_info.split("Dealer location")[1]
                        details["location"] = location.split("(")[0]
                        details["distance"] = location.split("(")[1].replace(" mile)", "").replace(" miles)", "")
                    except:
                        print("Seller information not found.")

                    specs_list = article.find("ul", attrs={"data-testid": "search-listing-specs"})
                    if specs_list:
                        for spec in specs_list:
                            if "reg" in spec.text:
                                details["year"] = re.search(r"\d{4}", spec.text).group(0)
                                details["reg"] = re.search(r"(?:\((\d\d) reg\))", spec.text).group(1)

                            if "miles" in spec.text:
                                details["mileage"] = re.search(r"(?:(\d+(\,\d{3})?) miles)", spec.text).group(1).replace(",","")

                            if spec.text in ["Manual", "Automatic"]:
                                details["transmission"] = spec.text

                            if spec.text in ["Hatchback", "Estate"]:
                                details["body_type"] = spec.text

                            if "." in spec.text and "L" in spec.text:
                                details["engine"] = spec.text

                            if spec.text in ["Petrol", "Diesel"]:
                                details["fuel"] = spec.text

                            if "owner" in spec.text:
                                details["owners"] = spec.text[0]

                    data.append(details)

        return pd.DataFrame.from_dict(data)


if __name__ == "__main__":
    scraper = AutoTraderScraper(cars={"Skoda": "Superb"})
    df = scraper.scrape()
    df.to_csv("skoda_superb_autotrader.csv", index=False)
    print("Done!")
