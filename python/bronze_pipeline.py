"""
Bronze Layer ETL Pipeline for CoinGecko Market Data.

This script extracts raw cryptocurrency market data from the CoinGecko API 
and loads it into a local 'Bronze' storage layer. It implements robust 
data engineering patterns including exponential backoff retries, pagination 
handling, idempotent execution, and atomic file writes.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
import requests
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Locate the .env file in the current script's directory and load the secrets into the environment
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


# ==========================================
# CONFIGURATION MANAGEMENT
# ==========================================
class PipelineConfig:
    """Centralized configuration for the pipeline."""
    def __init__(self):
        # Retrieve the required API key and implement a "fail-fast" pattern if it's missing
        self.api_key = os.getenv("COINGECKO_API_KEY")
        if not self.api_key:
            raise ValueError("CRITICAL: COINGECKO_API_KEY environment variable is not set.")
        
        # Define base API parameters
        self.base_url = "https://api.coingecko.com/api/v3"
        self.dataset_name = "markets"
        
        # Set boundaries for data extraction to prevent infinite loops or API quota exhaustion
        self.max_pages = int(os.getenv("CG_MAX_PAGES", "5"))
        self.per_page = 250
        
        # Define target directories for data storage and logging, using safe defaults
        self.base_dir = Path(os.getenv("BRONZE_DATA_DIR", "data"))
        self.log_dir = Path(os.getenv("LOG_DIR", "logs/bronze_data"))

# ==========================================
# API CLIENT (Extraction)
# ==========================================
class CoinGeckoClient:
    """Handles API interactions with robust retry logic."""
    def __init__(self, config: PipelineConfig):
        self.config = config
        # Set up authentication and expected response types
        self.headers = {
            "x-cg-demo-api-key": self.config.api_key,
            "accept": "application/json"
        }
        # Use a requests Session to reuse underlying TCP connections for better performance
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # Retry up to 5 times. Wait 2 seconds, then 4, 8, 16...
    # Only retry on specific transient exceptions, not on hard errors like 401 Unauthorized.
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout))
    )
    def fetch_page(self, endpoint: str, params: dict) -> list:
        """Fetches a single page from the API with built-in retry and timeout safety."""
        url = f"{self.config.base_url}{endpoint}"
        response = self.session.get(url, params=params, timeout=10)
        
        # Handle rate limits specifically
        # If the API complains about too many requests (429), pause execution to let the quota reset
        if response.status_code == 429:
            logging.warning("Rate limit hit (HTTP 429). Forcing a 60-second backoff...")
            import time
            time.sleep(60)
            response.raise_for_status() # Trigger a retry if configured, or fail

        # Raise an exception for any other HTTP errors (e.g., 404, 500)
        response.raise_for_status()
        return response.json()

    def fetch_all_pages(self, endpoint: str, base_params: dict) -> list:
        """Iterates through API pages until the max limit is reached or data is exhausted."""
        all_data = []
        for page in range(1, self.config.max_pages + 1):
            # Inject the current page number into the query parameters
            params = base_params.copy()
            params["page"] = page
            
            logging.info(f"Fetching page {page}/{self.config.max_pages}...")
            try:
                page_data = self.fetch_page(endpoint, params)
                # Break the loop early if a page returns empty (end of dataset)
                if not page_data:
                    break # Reached the end of the data
                
                # Append the newly fetched records to our master list
                all_data.extend(page_data)
            except requests.exceptions.HTTPError as e:
                # Catch non-transient HTTP errors to fail gracefully and preserve already-fetched data
                logging.error(f"HTTP Error failed permanently: {e}")
                break
        return all_data

# ==========================================
# STORAGE BACKEND (Loading)
# ==========================================
class BronzeStorage:
    """Manages idempotent file writes and partition structuring."""
    def __init__(self, config: PipelineConfig):
        self.base_dir = config.base_dir
        self.dataset_name = config.dataset_name

    def _get_partition_paths(self) -> tuple[Path, Path]:
        """Returns the directory and target file paths based on current time."""
        # Implement Hive-style partitioning (e.g., date=2023-10-27/14.json)
        # This makes querying the datalake highly efficient later on
        now = datetime.now()
        date_partition = now.strftime("%Y-%m-%d")
        hour_partition = now.strftime("%H")
        
        dir_path = self.base_dir / self.dataset_name / f"date={date_partition}"
        file_path = dir_path / f"{hour_partition}.json"
        return dir_path, file_path

    def is_already_processed(self) -> bool:
        """Checks if the data for the current hour already exists."""
        # This enables idempotency: running the script multiple times in the same hour
        # won't duplicate data or waste API calls.
        _, file_path = self._get_partition_paths()
        return file_path.exists()

    def write_data(self, data: list) -> str:
        """Writes JSON data and a _SUCCESS metadata file (atomic write pattern)."""
        dir_path, file_path = self._get_partition_paths()
        # Ensure the destination directories exist before attempting to write
        dir_path.mkdir(parents=True, exist_ok=True)

        # Write data to a temporary file first (prevents corrupted partial files if script crashes)
        temp_file = file_path.with_suffix(".tmp")
        
        try:
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename: Swap temp file to actual file
            # This ensures downstream consumers only ever see fully written files
            temp_file.rename(file_path)
            
            # Write metadata/success file for downstream systems (Silver layer) to watch
            # This acts as a reliable trigger for subsequent pipeline steps
            success_file = dir_path / f"_SUCCESS_{file_path.stem}"
            success_file.touch()
            
            return str(file_path)
        except Exception as e:
            # Rollback mechanism: destroy the temporary file if the process fails midway
            if temp_file.exists():
                temp_file.unlink() # Clean up partial file on failure
            raise e

# ==========================================
# PIPELINE ORCHESTRATOR
# ==========================================
def setup_logging(log_dir: Path):
    """Configures centralized logging to both the console and a daily log file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"bronze_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
    )

def main():
    """Main execution function that orchestrates the Extract and Load steps."""
    # Initialize configurations and logging
    config = PipelineConfig()
    setup_logging(config.log_dir)
    logger = logging.getLogger("BronzeETL")
    logger.info("--- Starting Production Bronze Pipeline ---")

    # Instantiate the dependencies
    storage = BronzeStorage(config)
    client = CoinGeckoClient(config)

    # 1. Pre-flight Check
    # Verify if we actually need to run right now (Idempotency check)
    if storage.is_already_processed():
        logger.info("Data for this partition already exists. Exiting pipeline safely.")
        return

    # 2. Extract
    # Define the payload parameters for the API request
    parameters = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": config.per_page, 
    }
    
    logger.info("Extracting data from source...")
    raw_data = client.fetch_all_pages("/coins/markets", parameters)
    
    # Abort if the API returned nothing, preventing empty files from being written
    if not raw_data:
        logger.warning("No data extracted. Aborting load phase.")
        return

    # 3. Load
    # Commit the extracted data to the storage backend
    logger.info(f"Loading {len(raw_data)} records to Bronze storage...")
    try:
        saved_path = storage.write_data(raw_data)
        logger.info(f"Pipeline completed successfully. Data written to: {saved_path}")
    except Exception as e:
        logger.error(f"Failed to write data to Bronze layer: {e}")

# Standard Python idiom to ensure main() runs only when the script is executed directly
if __name__ == "__main__":
    main()