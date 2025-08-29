from bs4 import BeautifulSoup
import requests

try:
    response = requests.get("https://www.propertyfinder.ae/en/search?c=1&t=5&fu=0&ob=mr&page=1")
    soup = BeautifulSoup(response.text, "html.parser")
    
    print("Response status:", response.status_code)
    print("Page title:", soup.title.text if soup.title else "No title found")
    
    # Debug: Let's find the correct container
    print("\n=== Looking for property containers ===")
    
    # Try different possible selectors
    containers = [
        soup.find("ul", class_="styles_desktop_containerV85pq"),
        soup.find("ul", class_=lambda x: x and "container" in x.lower()),
        soup.find("div", class_=lambda x: x and "property" in x.lower()),
        soup.find_all("li", attrs={"data-testid": "list-item"}),
        soup.find_all("li", attrs={"data-id": True}),
        soup.find_all("article", class_=lambda x: x and "property-card" in x),
    ]
    
    for i, container in enumerate(containers):
        if container:
            print(f"Container {i} found: {type(container)} - {len(container) if hasattr(container, '__len__') else 1} items")
            if hasattr(container, 'find_all'):
                lands = container.find_all("li")
            elif isinstance(container, list):
                lands = container
            else:
                lands = [container]
            break
    else:
        print("No suitable container found. Let's check the page structure...")
        # Print first 2000 characters to see the structure
        print("\nPage content preview:")
        print(response.text[:2000])
        lands = []
    
    if lands:
        print(f"\nFound {len(lands)} property listings")
        
        for i, land in enumerate(lands):  # Process all properties
            try:
                print(f"\n--- Property {i+1} ---")
                
                # Property Type
                property_type = land.find("p", {"data-testid": "property-card-type"})
                property_type_text = property_type.text.strip() if property_type else "N/A"
                
                # Price
                price = land.find("p", {"data-testid": "property-card-price"})
                price_text = price.text.strip() if price else "N/A"
                
                # Title
                title = land.find("h2", class_=lambda x: x and "title" in x) or land.find("h2")
                title_text = title.text.strip() if title else "N/A"
                
                # Location
                location = land.find("p", class_=lambda x: x and "location" in x)
                location_text = location.text.strip() if location else "N/A"
                
                # Area/Size
                area = land.find("p", {"data-testid": "property-card-spec-area"})
                area_text = area.text.strip() if area else "N/A"
                
                # Property Link
                property_link = land.find("a", {"data-testid": "property-card-link"}) or land.find("a")
                link = property_link.get("href") if property_link else "N/A"
                full_link = f"https://www.propertyfinder.ae{link}" if link != "N/A" and not link.startswith("http") else link
                
                # Additional fields
                # Listing Status (Featured, Premium, etc.)
                listing_status = land.find("p", class_=lambda x: x and "listing-level" in x)
                status_text = listing_status.text.strip() if listing_status else "N/A"
                
                # New Tag
                new_tag = land.find("button", {"data-testid": "property-card-tag"})
                is_new = new_tag.text.strip() if new_tag else "N/A"
                
                # Listed time
                publish_info = land.find("p", class_=lambda x: x and "publish-info" in x)
                listed_time = publish_info.text.strip() if publish_info else "N/A"
                
                # Phone number from call link
                call_link = land.find("a", {"data-testid": "property-card-contact-action-CALL"})
                phone = call_link.get("href").replace("tel:", "") if call_link else "N/A"
                
                # Image count
                image_count = land.find("span", class_=lambda x: x and "image-count" in x)
                images = image_count.text.strip() if image_count else "N/A"
                
                # Bedrooms and Bathrooms if available
                specs = land.find_all("p", {"data-testid": lambda x: x and "property-card-spec" in x})
                bedrooms = bathrooms = "N/A"
                for spec in specs:
                    spec_text = spec.text.strip().lower()
                    if "bed" in spec_text:
                        bedrooms = spec.text.strip()
                    elif "bath" in spec_text:
                        bathrooms = spec.text.strip()
                
                # Property ID (from data-id attribute)
                property_id = land.get("data-id", "N/A")
                
                print(f"Property ID: {property_id}")
                print(f"Type: {property_type_text}")
                print(f"Title: {title_text}")
                print(f"Price: {price_text}")
                print(f"Location: {location_text}")
                print(f"Area: {area_text}")
                print(f"Bedrooms: {bedrooms}")
                print(f"Bathrooms: {bathrooms}")
                print(f"Status: {status_text}")
                print(f"New Listing: {is_new}")
                print(f"Listed: {listed_time}")
                print(f"Images: {images}")
                print(f"Phone: {phone}")
                print(f"Link: {full_link}")
                print("=" * 50)
                
            except Exception as e:
                print(f"Error parsing property {i+1}: {e}")
                print("Raw HTML snippet:", str(land)[:200] + "..." if len(str(land)) > 200 else str(land))
    else:
        print("No property listings found")
        
except Exception as e:
    print(f"Error: {e}")
    print("This might be due to:")
    print("1. Website blocking automated requests")
    print("2. Changed website structure")
    print("3. Network connectivity issues")
    print("4. Need for headers/user-agent")