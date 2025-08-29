from bs4 import BeautifulSoup
import requests
import os
import pandas as pd
from datetime import datetime
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PropertyScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.properties_data = []
        
    def collect_property_data(self, url):
        """Collect detailed property data from individual property page"""
        try:
            logger.info(f"Collecting detailed data from: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            property_data = {}
            
            # Find title - it's in h1 with class 'styles_desktop_title__j0uNx'
            title = soup.find("h1", class_="styles_desktop_title__j0uNx")
            property_data["detailed_title"] = title.text.strip() if title else "No title found"
            
            # Find subtitle - look for location info
            subtitle = soup.find("p", class_="styles-module_map__title__M2mBC")
            property_data["detailed_location"] = subtitle.text.strip() if subtitle else "No subtitle found"
            
            # Find description - it's in article with class 'styles_description__tKGaD'
            description = soup.find("article", class_="styles_description__tKGaD")
            property_data["description"] = description.text.strip() if description else "No description found"
            
            # Find price
            price = soup.find("p", class_="styles_desktop_navigator__price__BYvcC")
            property_data["detailed_price"] = price.text.strip() if price else "No price found"
            
            # Count images without storing URLs (no image download needed)
            images = soup.find_all("img")
            image_count = 0
            
            for img in images:
                src = img.get("src")
                if src and "propertyfinder.ae" in src:
                    image_count += 1
            
            property_data["detailed_image_count"] = image_count
            
            logger.info(f"Successfully collected detailed data for: {property_data['detailed_title']}")
            return property_data
            
        except Exception as e:
            logger.error(f"Error collecting property data from {url}: {e}")
            return {}

    def scrape_single_page(self, page_url, page_number):
        """Scrape properties from a single page"""
        try:
            logger.info(f"Scraping page {page_number}: {page_url}")
            response = self.session.get(page_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            logger.info(f"Response status: {response.status_code}")
            
            # Try different possible selectors for property containers
            containers = [
                soup.find("ul", class_="styles_desktop_containerV85pq"),
                soup.find("ul", class_=lambda x: x and "container" in x.lower()),
                soup.find("div", class_=lambda x: x and "property" in x.lower()),
                soup.find_all("li", attrs={"data-testid": "list-item"}),
                soup.find_all("li", attrs={"data-id": True}),
                soup.find_all("article", class_=lambda x: x and "property-card" in x),
            ]
            
            lands = []
            for i, container in enumerate(containers):
                if container:
                    if hasattr(container, 'find_all'):
                        lands = container.find_all("li")
                    elif isinstance(container, list):
                        lands = container
                    else:
                        lands = [container]
                    break
            
            if not lands:
                logger.warning(f"No property listings found on page {page_number}")
                return 0
            
            logger.info(f"Found {len(lands)} property listings on page {page_number}")
            
            page_properties = []
            
            for i, land in enumerate(lands):
                try:
                    property_info = {
                        'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'page_number': page_number,
                        'property_index_on_page': i + 1,
                        'global_property_index': len(self.properties_data) + i + 1
                    }
                    
                    # Property Type
                    property_type = land.find("p", {"data-testid": "property-card-type"})
                    property_info["property_type"] = property_type.text.strip() if property_type else "N/A"
                    
                    # Price
                    price = land.find("p", {"data-testid": "property-card-price"})
                    property_info["price"] = price.text.strip() if price else "N/A"
                    
                    # Title
                    title = land.find("h2", class_=lambda x: x and "title" in x) or land.find("h2")
                    property_info["title"] = title.text.strip() if title else "N/A"
                    
                    # Location
                    location = land.find("p", class_=lambda x: x and "location" in x)
                    property_info["location"] = location.text.strip() if location else "N/A"
                    
                    # Area/Size
                    area = land.find("p", {"data-testid": "property-card-spec-area"})
                    property_info["area"] = area.text.strip() if area else "N/A"
                    
                    # Property Link
                    property_link = land.find("a", {"data-testid": "property-card-link"}) or land.find("a")
                    link = property_link.get("href") if property_link else "N/A"
                    full_link = f"https://www.propertyfinder.ae{link}" if link != "N/A" and not link.startswith("http") else link
                    property_info["property_url"] = full_link
                    
                    # Listing Status
                    listing_status = land.find("p", class_=lambda x: x and "listing-level" in x)
                    property_info["listing_status"] = listing_status.text.strip() if listing_status else "N/A"
                    
                    # New Tag
                    new_tag = land.find("button", {"data-testid": "property-card-tag"})
                    property_info["is_new"] = new_tag.text.strip() if new_tag else "N/A"
                    
                    # Listed time
                    publish_info = land.find("p", class_=lambda x: x and "publish-info" in x)
                    property_info["listed_time"] = publish_info.text.strip() if publish_info else "N/A"
                    
                    # Phone number
                    call_link = land.find("a", {"data-testid": "property-card-contact-action-CALL"})
                    property_info["phone"] = call_link.get("href").replace("tel:", "") if call_link else "N/A"
                    
                    # Image count from listing
                    image_count = land.find("span", class_=lambda x: x and "image-count" in x)
                    property_info["listing_image_count"] = image_count.text.strip() if image_count else "N/A"
                    
                    # Bedrooms and Bathrooms
                    specs = land.find_all("p", {"data-testid": lambda x: x and "property-card-spec" in x})
                    property_info["bedrooms"] = "N/A"
                    property_info["bathrooms"] = "N/A"
                    
                    for spec in specs:
                        spec_text = spec.text.strip().lower()
                        if "bed" in spec_text:
                            property_info["bedrooms"] = spec.text.strip()
                        elif "bath" in spec_text:
                            property_info["bathrooms"] = spec.text.strip()
                    
                    # Property ID
                    property_info["property_id"] = land.get("data-id", f"prop_p{page_number}_{i+1}")
                    
                    # Collect detailed property data (optional, can be disabled for faster scraping)
                    if full_link != "N/A" and self.collect_detailed_data:
                        detailed_data = self.collect_property_data(full_link)
                        property_info.update(detailed_data)
                        time.sleep(0.5)  # Small delay between detailed requests
                    
                    page_properties.append(property_info)
                    
                except Exception as e:
                    logger.error(f"Error processing property {i+1} on page {page_number}: {e}")
                    continue
            
            # Add all properties from this page to the main list
            self.properties_data.extend(page_properties)
            logger.info(f"Successfully processed {len(page_properties)} properties from page {page_number}")
            
            return len(page_properties)
            
        except Exception as e:
            logger.error(f"Error scraping page {page_number}: {e}")
            return 0

    def scrape_multiple_pages(self, base_url="https://www.propertyfinder.ae/en/search?c=1&t=5&fu=0&ob=mr", 
                            start_page=1, max_pages=None, collect_detailed_data=False, auto_detect_end=True):
        """Scrape property listings from multiple pages with no limits"""
        self.collect_detailed_data = collect_detailed_data
        total_properties = 0
        consecutive_empty_pages = 0
        max_consecutive_empty = 3  # Stop after 3 consecutive empty pages
        
        if max_pages is None:
            logger.info(f"Starting unlimited multi-page scraping from page {start_page}")
        else:
            logger.info(f"Starting multi-page scraping: {max_pages} pages from page {start_page}")
        
        logger.info(f"Detailed data collection: {'Enabled' if collect_detailed_data else 'Disabled'}")
        logger.info(f"Auto-detect end: {'Enabled' if auto_detect_end else 'Disabled'}")
        
        page_num = start_page
        
        while True:
            # Check if we've reached max_pages (if specified)
            if max_pages is not None and (page_num - start_page) >= max_pages:
                logger.info(f"Reached maximum page limit: {max_pages}")
                break
                
            try:
                # Construct page URL
                page_url = f"{base_url}&page={page_num}"
                
                # Scrape the page
                properties_count = self.scrape_single_page(page_url, page_num)
                
                if properties_count == 0:
                    consecutive_empty_pages += 1
                    logger.warning(f"No properties found on page {page_num}. Empty pages count: {consecutive_empty_pages}")
                    
                    if auto_detect_end and consecutive_empty_pages >= max_consecutive_empty:
                        logger.info(f"Stopping after {consecutive_empty_pages} consecutive empty pages")
                        break
                else:
                    consecutive_empty_pages = 0  # Reset counter
                    total_properties += properties_count
                
                # Progress update every 10 pages
                if page_num % 10 == 0:
                    logger.info(f"📊 Progress: Page {page_num} completed. Total properties: {total_properties}")
                
                # Add delay between pages to be respectful
                logger.info(f"Waiting 1.5 seconds before next page...")
                time.sleep(1.5)
                
                page_num += 1
                
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {e}")
                page_num += 1
                continue
        
        pages_scraped = page_num - start_page
        logger.info(f"✅ Multi-page scraping completed!")
        logger.info(f"📊 Total properties scraped: {total_properties} from {pages_scraped} pages")
        logger.info(f"📄 Page range: {start_page} to {page_num - 1}")
        
        return self.properties_data

    def save_to_excel(self, filename=None):
        """Save scraped property data to Excel file"""
        if not self.properties_data:
            logger.warning("No property data to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"property_data_{timestamp}.xlsx"
        
        try:
            # Create DataFrame
            df = pd.DataFrame(self.properties_data)
            
            # Reorder columns for better readability
            preferred_columns = [
                'scrape_date', 'page_number', 'property_index_on_page', 'global_property_index', 
                'property_id', 'title', 'property_type', 'price', 'location', 'area', 
                'bedrooms', 'bathrooms', 'listing_status', 'is_new', 'listed_time', 
                'phone', 'property_url', 'listing_image_count'
            ]
            
            # Add detailed data columns if they exist
            if 'detailed_title' in df.columns:
                preferred_columns.extend([
                    'detailed_title', 'detailed_location', 'detailed_price', 
                    'description', 'detailed_image_count'
                ])
            
            # Reorder columns, keeping any extra columns at the end
            existing_columns = [col for col in preferred_columns if col in df.columns]
            extra_columns = [col for col in df.columns if col not in preferred_columns]
            final_columns = existing_columns + extra_columns
            df = df[final_columns]
            
            # Save to Excel with formatting
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Property_Data', index=False)
                
                # Summary sheet
                summary_data = {
                    'Metric': [
                        'Total Properties Scraped',
                        'Total Pages Scraped',
                        'Properties with Detailed Data',
                        'Properties with Images',
                        'Most Common Property Type',
                        'Most Common Location',
                        'Scrape Date'
                    ],
                    'Value': [
                        len(df),
                        df['page_number'].nunique() if 'page_number' in df.columns else 1,
                        len(df[df['detailed_title'].notna()]) if 'detailed_title' in df.columns else 0,
                        len(df[df['listing_image_count'] != 'N/A']),
                        df['property_type'].mode().iloc[0] if not df['property_type'].mode().empty else 'N/A',
                        df['location'].mode().iloc[0] if not df['location'].mode().empty else 'N/A',
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Format the main sheet
                worksheet = writer.sheets['Property_Data']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"Property data saved to: {filename}")
            logger.info(f"Total properties saved: {len(df)}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving to Excel: {e}")
            return None

def main():
    """Main function to run the scraper"""
    scraper = PropertyScraper()
    
    print("🏠 Property Finder Multi-Page Scraper (UNLIMITED)")
    print("=" * 60)
    
    # Configuration options
    print("\nConfiguration Options:")
    print("1. Quick scrape (3 pages, no detailed data)")
    print("2. Standard scrape (5 pages, no detailed data)")
    print("3. Comprehensive scrape (10 pages, no detailed data)")
    print("4. UNLIMITED scrape (all pages, no detailed data)")
    print("5. UNLIMITED with detailed data (WARNING: VERY SLOW)")
    print("6. Custom configuration")
    
    choice = input("\nSelect option (1-6): ").strip()
    
    # Default values
    start_page = 1
    max_pages = None
    collect_detailed = False
    auto_detect_end = True
    base_url = "https://www.propertyfinder.ae/en/search?c=1&t=5&fu=0&ob=mr"
    
    if choice == "1":
        max_pages = 3
        print("✅ Quick scrape selected: 3 pages")
    elif choice == "2":
        max_pages = 5
        print("✅ Standard scrape selected: 5 pages")
    elif choice == "3":
        max_pages = 10
        print("✅ Comprehensive scrape selected: 10 pages")
    elif choice == "4":
        max_pages = None
        print("✅ UNLIMITED scrape selected: All available pages")
        print("⚡ This will scrape until no more properties are found")
    elif choice == "5":
        max_pages = None
        collect_detailed = True
        print("✅ UNLIMITED with detailed data selected")
        print("⚠️  WARNING: This will be VERY SLOW but collect maximum data")
        confirm = input("This could take hours. Continue? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Operation cancelled")
            return
    elif choice == "6":
        try:
            start_page = int(input("Enter starting page number (default 1): ") or "1")
            
            max_pages_input = input("Enter number of pages to scrape (leave empty for unlimited): ").strip()
            if max_pages_input:
                max_pages = int(max_pages_input)
            else:
                max_pages = None
                print("✅ Unlimited pages selected")
            
            detailed_input = input("Collect detailed data from each property? (y/n, default n): ").lower().strip()
            collect_detailed = detailed_input == 'y'
            
            if collect_detailed and max_pages is None:
                print("⚠️  WARNING: Unlimited pages + detailed data = EXTREMELY SLOW")
                confirm = input("This could take many hours. Continue? (y/n): ").lower().strip()
                if confirm != 'y':
                    collect_detailed = False
                    print("Detailed data collection disabled")
            
            auto_input = input("Auto-detect when no more pages? (y/n, default y): ").lower().strip()
            auto_detect_end = auto_input != 'n'
                    
        except ValueError:
            print("Invalid input, using defaults")
    else:
        max_pages = 5
        print("Invalid choice, using defaults: 5 pages")
    
    print(f"\n🚀 Starting scraper with:")
    print(f"   📄 Pages: {start_page} to {'UNLIMITED' if max_pages is None else start_page + max_pages - 1}")
    print(f"   📊 Detailed data: {'Enabled' if collect_detailed else 'Disabled'}")
    print(f"   🔍 Auto-detect end: {'Enabled' if auto_detect_end else 'Disabled'}")
    print(f"   🔗 Base URL: {base_url}")
    
    if max_pages is None:
        print(f"   ⚡ Mode: UNLIMITED - Will scrape until no more properties found")
        estimated_time = "Several hours" if collect_detailed else "30-60 minutes"
        print(f"   ⏱️  Estimated time: {estimated_time}")
    
    # Confirmation for large scrapes
    if max_pages is None or (max_pages and max_pages > 20):
        confirm = input(f"\n⚠️  Large scrape detected. Continue? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Operation cancelled")
            return
    
    # Start scraping
    start_time = datetime.now()
    print(f"\n🎯 Scraping started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    properties = scraper.scrape_multiple_pages(
        base_url=base_url,
        start_page=start_page, 
        max_pages=max_pages,
        collect_detailed_data=collect_detailed,
        auto_detect_end=auto_detect_end
    )
    end_time = datetime.now()
    
    if properties:
        # Save to Excel
        excel_file = scraper.save_to_excel()
        
        if excel_file:
            duration = (end_time - start_time).total_seconds()
            duration_formatted = f"{duration//3600:.0f}h {(duration%3600)//60:.0f}m {duration%60:.0f}s" if duration > 3600 else f"{duration//60:.0f}m {duration%60:.0f}s"
            
            print(f"\n🎉 SUCCESS!")
            print(f"📊 {len(properties)} properties scraped in {duration_formatted}")
            print(f"📁 Data saved to: {excel_file}")
            print(f"💾 Excel file contains comprehensive property information")
            
            # Additional statistics
            if 'page_number' in scraper.properties_data[0]:
                pages_scraped = len(set(prop['page_number'] for prop in scraper.properties_data))
                avg_per_page = len(properties) / pages_scraped if pages_scraped > 0 else 0
                print(f"📈 Statistics:")
                print(f"   • Pages scraped: {pages_scraped}")
                print(f"   • Average properties per page: {avg_per_page:.1f}")
                print(f"   • Properties with detailed data: {sum(1 for p in properties if p.get('detailed_title', 'N/A') != 'N/A')}")
        else:
            print("❌ Failed to save Excel file")
    else:
        print("❌ No properties were scraped")

def unlimited_scrape(start_page=1, with_detailed_data=False):
    """Quick function for unlimited scraping"""
    scraper = PropertyScraper()
    base_url = "https://www.propertyfinder.ae/en/search?c=1&t=5&fu=0&ob=mr"
    
    print(f"🚀 Starting unlimited scrape from page {start_page}")
    print(f"📊 Detailed data: {'Enabled' if with_detailed_data else 'Disabled'}")
    
    properties = scraper.scrape_multiple_pages(
        base_url=base_url,
        start_page=start_page,
        max_pages=None,  # Unlimited
        collect_detailed_data=with_detailed_data,
        auto_detect_end=True
    )
    
    if properties:
        excel_file = scraper.save_to_excel()
        print(f"✅ Scraped {len(properties)} properties and saved to {excel_file}")
        return excel_file
    else:
        print("❌ No properties scraped")
        return None

if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import pandas as pd
        import openpyxl
    except ImportError:
        print("Installing required packages...")
        os.system("pip install pandas openpyxl")
        import pandas as pd
        import openpyxl
    
    main()

# Example usage for programmatic access:
# 
# # Unlimited scrape from page 1
# unlimited_scrape(start_page=1, with_detailed_data=False)
# 
# # Unlimited scrape starting from page 100
# unlimited_scrape(start_page=100, with_detailed_data=False)
# 
# # Custom unlimited scrape with detailed data
# scraper = PropertyScraper()
# properties = scraper.scrape_multiple_pages(
#     start_page=100, 
#     max_pages=None,  # Unlimited
#     collect_detailed_data=True,
#     auto_detect_end=True
# )
# excel_file = scraper.save_to_excel("properties_from_page_100.xlsx")