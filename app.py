from flask import Flask, request, render_template, jsonify
import datetime
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# Function to get reviews from a page using Selenium
def get_reviews_from_page(driver, source):
    """Extract reviews from a Selenium WebDriver object."""
    reviews = []
    if source == "G2":
        review_containers = driver.find_elements(By.CSS_SELECTOR, '.c-review')
        for container in review_containers:
            try:
                title = container.find_element(By.CSS_SELECTOR, '[itemprop="name"]').text.strip()
                review = container.find_element(By.CSS_SELECTOR, '[itemprop="reviewBody"]').text.strip()
                date_str = container.find_element(By.CSS_SELECTOR, '.c-review__date').text.strip()
                date = datetime.datetime.strptime(date_str, '%B %d, %Y')
                reviews.append({'title': title, 'review': review, 'date': date})
            except Exception as e:
                print(f"Error parsing G2 review: {e}")
                continue
    elif source == "Capterra":
        review_containers = driver.find_elements(By.CSS_SELECTOR, '.review-wrapper')
        for container in review_containers:
            try:
                title = container.find_element(By.CSS_SELECTOR, '.review-title').text.strip()
                review = container.find_element(By.CSS_SELECTOR, '.review-comments').text.strip()
                date_str = container.find_element(By.CSS_SELECTOR, '.review-date').text.strip()
                date = datetime.datetime.strptime(date_str, '%b %d, %Y')
                reviews.append({'title': title, 'review': review, 'date': date})
            except Exception as e:
                print(f"Error parsing Capterra review: {e}")
                continue
    return reviews

# Function to scrape reviews based on company name, start date, end date, and source
def scrape_reviews(company_name, start_date, end_date, source):
    """Scrapes product reviews from G2 or Capterra for a given company and time period."""
    reviews = []

    base_url = {
        "G2": f"https://www.g2.com/products/{company_name}/reviews",
        "Capterra": f"https://www.capterra.com/p/{company_name}/reviews/"
    }

    url = base_url.get(source)
    if not url:
        print(f"Invalid source: {source}. Choose either G2 or Capterra.")
        return []

    options = Options()
    # Uncomment the line below to run in headless mode if needed
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')

    driver = webdriver.Edge(options=options)
    driver.implicitly_wait(10)  # Waits for 10 seconds for elements to load

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.review-wrapper' if source == "Capterra" else '.c-review'))
        )

        while True:
            page_reviews = get_reviews_from_page(driver, source)
            for review in page_reviews:
                if start_date <= review['date'] <= end_date:
                    reviews.append(review)

            # Click next button
            try:
                if source == "G2":
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, '.c-pagination__next-page'))
                    )
                else:  # Capterra
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, '.page-link[rel="next"]'))
                    )
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)  # Pause to avoid overwhelming the server
            except Exception as e:
                print(f"No more pages or error navigating: {e}")
                break

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

    return reviews

# Define a Flask route to scrape reviews
@app.route('/scrape_reviews', methods=['GET', 'POST'])
def scrape_reviews_route():
    if request.method == 'POST':
        company_name = request.form['company_name'].strip().lower()
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']
        source = request.form['source'].strip()

        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

        if source not in ["G2", "Capterra"]:
            return jsonify({'error': "Invalid source. Please choose either 'G2' or 'Capterra'."}), 400

        # Call the scraping function
        reviews = scrape_reviews(company_name, start_date, end_date, source)

        if reviews:
            # Return the reviews in JSON format
            return jsonify(reviews), 200
        else:
            return jsonify({'message': f'No reviews found for {company_name} between {start_date_str} and {end_date_str}.'}), 404

    return render_template('scrape_reviews.html')

# Define the index route
@app.route('/')
def index():
    return render_template('index.html')  # Render index.html for the home page

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
