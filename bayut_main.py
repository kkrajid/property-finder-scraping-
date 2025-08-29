from bs4 import BeautifulSoup
import requests
import os
import pandas as pd
from datetime import datetime
import time
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



class BayutPropertyScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.properties_data = []


    def fetch_properties(self, page=1):
        url = f"https://www.bayut.com/for-sale/residential-plots/uae/"
        logger.info(f"Fetching properties from {url}")
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            bayut_lands = soup.find("ul", class_="e20beb46").find_all("li")
            
            for land in bayut_lands[:3]:
                data_dict = {}

                # --- 1. From JSON-LD <script>
                script_tag = land.find("script", type="application/ld+json")
                if script_tag:
                    try:
                        json_data = json.loads(script_tag.string)
                        data_dict["Title"] = json_data.get("name")
                        data_dict["URL"] = json_data.get("url", "")
                        data_dict["Latitude"] = json_data.get("geo", {}).get("latitude")
                        data_dict["Longitude"] = json_data.get("geo", {}).get("longitude")
                        data_dict["Size"] = json_data.get("floorSize", {}).get("value")
                        data_dict["Unit"] = json_data.get("floorSize", {}).get("unitText")
                        data_dict["Rooms"] = json_data.get("numberOfRooms", {}).get("value")
                        data_dict["Bathrooms"] = json_data.get("numberOfBathroomsTotal")
                        data_dict["Locality"] = json_data.get("address", {}).get("addressLocality")
                        data_dict["Region"] = json_data.get("address", {}).get("addressRegion")
                        data_dict["Image"] = json_data.get("image")
                    except:
                        pass

                # --- 2. From visible HTML
                try:
                    data_dict["Price"] = land.find("span", class_="f343d9ce").get_text(strip=True)
                except:
                    data_dict["Price"] = None

                try:
                    data_dict["Location"] = land.find("div", class_="_7e396fc3").get_text(strip=True)
                except:
                    data_dict["Location"] = None

                try:
                    data_dict["Reference"] = land.find("span", string=lambda s: s and "Ref" in s).get_text(strip=True)
                except:
                    data_dict["Reference"] = None
                
                internal_link_response  = self.session.get(data_dict["URL"])
                internal_link_response.raise_for_status()
                internal_soup = BeautifulSoup(internal_link_response.text, "html.parser")

                print(internal_soup)

                break 


            
            return soup
        except requests.RequestException as e:
            logger.error(f"Error fetching properties: {e}")
            return None



if __name__ == "__main__":
    scraper = BayutPropertyScraper()
    soup = scraper.fetch_properties()