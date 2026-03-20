import logging
from openclaw.scout.runner import ScoutRunner
from openclaw.scout.providers.youtube_provider import YouTubeProvider

logging.basicConfig(
    filename='openclaw/schedule_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def read_queries(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def run_scheduler():
    queries = read_queries('openclaw/scout_queries.txt')
    runner = ScoutRunner(provider=YouTubeProvider())
    for query in queries:
        try:
            logging.info(f"Starting query: {query}")
            results = runner.run(query)
            logging.info(f"Completed query: {query} with {len(results)} results")
        except Exception as e:
            logging.error(f"Error on query '{query}': {e}")

if __name__ == '__main__':
    run_scheduler()
