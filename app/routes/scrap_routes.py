from flask import Blueprint, jsonify, request
from app.scraper.upwork_scraper import UpworkScraper

scraper_bp = Blueprint('scraper', __name__)

@scraper_bp.route('/upwork-jobs', methods=['GET'])
def scrape_upwork():
    keyword = request.args.get('q', 'flask')
    print(keyword)

    scraper = UpworkScraper()
    jobs = scraper.scrape_jobs(keyword)
    scraper.close()

    return jsonify(jobs)
