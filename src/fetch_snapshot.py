import json
import requests #HTTP Requests 
import gzip
from datetime import datetime, timezone #timezone-timestamps
from pathlib import Path #clean, cross-platform file paths 
#Configuration:
BASE_URL="https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"
FEEDS={
    #dictionnary: feed name-> its URL 
    "station_information":f"{BASE_URL}/station_information.json",
    "station_status":f"{BASE_URL}/station_status.json"
}
PROJECT_ROOT=Path(__file__).resolve().parent.parent
RAW_DIR=PROJECT_ROOT/"data"/"raw" #now always points to velib-pipeline/data/raw, wherever we run from 
TIMEOUT_SECONDS=10 #API doesnt answer within 10seconds
#This function downloads the data from a url and return it as a python dictionnary  
def fetch_feed(url:str)->dict:
    response=requests.get(url,timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()
#this function saves the downloaded json data in a clear folder structure  
def save_raw(payload:dict,feed_name:str,fetched_at:datetime)->Path:
    folder=RAW_DIR/feed_name/fetched_at.strftime("%Y-%m-%d") #data/raw/station_status/2026-10-25
    folder.mkdir(parents=True, exist_ok=True) 
    file_path=folder/fetched_at.strftime("T%H%M%SZ.json.gz")
    with gzip.open(file_path,"wt",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False)
    return file_path

def main()->None:
    fetched_at=datetime.now(timezone.utc)
    print(f"Snapchot started at {fetched_at:%Y-%m-%d %H:%M:%S} UTC")
    for feed_name,url in FEEDS.items():
        payload=fetch_feed(url)
        file_path=save_raw(payload,feed_name,fetched_at)
        n_stations=len(payload["data"]["stations"])
        feed_ts=payload.get("lastUpdatedOther")
        feed_time=datetime.fromtimestamp(feed_ts,tz=timezone.utc)#unix seconds-> readable utc time 
        print(f"{feed_name}:{n_stations} stations, feed updated at {feed_time:%H:%M:%S} UTC -> {file_path}")

if __name__=="__main__":
    main()

